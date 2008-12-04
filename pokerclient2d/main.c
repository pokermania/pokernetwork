/* *
 * Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
 *                                24 rue vieille du temple, 75004 Paris
 *
 * This software's license gives you freedom; you can copy, convey,
 * propagate, redistribute and/or modify this program under the terms of
 * the GNU Affero General Public License (AGPL) as published by the Free
 * Software Foundation (FSF), either version 3 of the License, or (at your
 * option) any later version of the AGPL published by the FSF.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
 * General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program in a file in the toplevel directory called
 * "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *  Henry Prêcheur <henry@precheur.org>
 *  Loic Dachary <loic@gnu.org>
 *
 */

#include <glade/glade.h>
#include "util.h"
#include "gui.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gtk/gtk.h>
#include <getopt.h>
#include <unistd.h>
#include "interface_io.h"
#include "dispatcher.h"

void create_smiley_array(const char *path, const char *filename);
void destroy_smiley_array(void);

/*
 * Command line parsing
 */
int   g_want_verbose = 0;
int   g_port_number = 19379;
char* g_display = 0;
char* g_hostname = 0;
char* g_gtk_rc_file = 0;
char* g_data_dir = 0;
char* g_smiley_path = 0;

static const char short_options[] = "p:d:D:g:v:r:s:";
enum option_e
  {
    opt_port = 'p',
    opt_display = 'd',
    opt_datadir = 'D',
    opt_glade = 'g',
    opt_verbose = 'v',
    opt_gtkrc = 'r',
    opt_smiley = 's'
  };

static struct option  long_options[] =
  {
    { "port",         required_argument,      0,      opt_port },
    { "display",      required_argument,      0,      opt_display },
    { "datadir",      required_argument,      0,      opt_datadir },
    { "glade",                required_argument,      0,      opt_glade },
    { "verbose",      required_argument,      0,      opt_verbose },
    { "gtkrc",                required_argument,      0,      opt_gtkrc },
    { "smiley",               required_argument,      0,      opt_smiley },
    { 0,              0,                      0,      0 }
  };

static int
parse_command_line(int argc, char* argv[])
{
  int c;
  int option_index = 0;

  while ((c = getopt_long (argc, argv, short_options, long_options,
                         &option_index)) != -1)
    {
      switch (c)
      {
      case opt_port:
        g_port_number = atoi(optarg);
        break;
      case opt_verbose:
        g_want_verbose = atoi(optarg);
        break;
      case opt_display:
        g_display = g_strdup(optarg);
        break;
      case opt_gtkrc:
        g_gtk_rc_file = g_strdup(optarg);
        break;
      case opt_datadir:
        g_data_dir = g_strdup(optarg);
        break;
      case opt_glade:
        gui_set_glade_file(optarg);
        break;
      case opt_smiley:
        g_smiley_path = g_strdup(optarg);
        break;
      default:
        abort();
      }
    }
  if (argc - optind > 1)
    {
      fprintf(stderr, "usage: %s [options] [hostname]\n", argv[0]);
      return -1;
    }
  else
    {
      g_hostname = g_strdup(argv[optind]);
      return 0;
    }
}

gboolean	handle_network(GIOChannel *source,
                             GIOCondition condition,
                             gpointer data)
{
  (void) source;
  (void) condition;
  (void) data;
  if (condition == G_IO_HUP)
    {
      gtk_main_quit();
      return FALSE;
    }
  else if (condition == G_IO_ERR)
    {
      gtk_main_quit();
      return FALSE;
    }
  g_message("handle_network");
  if (dispatcher(0) == FALSE)
    {
      gtk_main_quit();
      return FALSE;
    }
  return TRUE;
}

int main(int   argc,
	 char *argv[])
{
  if(setpgrp() < 0)
    perror("setpgrp()");

  if (parse_command_line(argc, argv) != 0)
    return 1;

#ifdef WIN32
  // if under windows, we need to define the locale directory
  bindtextdomain("poker2d", "./../locale");
#endif
  
  bind_textdomain_codeset("poker2d","UTF-8");    
  textdomain("poker2d");

  if (g_display)
  {
      char	tmp[64];
      snprintf(tmp, sizeof (tmp), "DISPLAY=%s", g_display);
      putenv(tmp);
  }
  
  if (g_gtk_rc_file)
  {
      char* file_name = strrchr(g_gtk_rc_file, '/')+1;

      int path_len = strlen(g_gtk_rc_file);
      int name_len = strlen(file_name);
      int newname_len = strlen(gettext(file_name));
      
      char* new_gtk_rc = malloc(sizeof(char)*(path_len-name_len+newname_len));
      memset(new_gtk_rc, 0, path_len-name_len+newname_len);
      memcpy(new_gtk_rc, g_gtk_rc_file, path_len-name_len);
      strcat(new_gtk_rc, gettext(file_name));
      
      char* tmp[2] = { new_gtk_rc, 0};
      gtk_rc_set_default_files(tmp);
      
      g_message("%s\n", new_gtk_rc);
      g_message(gettext("CANCEL"));
      
      g_free(g_gtk_rc_file);
      g_free(new_gtk_rc);
  }
  gtk_init (&argc, &argv);  

  set_verbose(g_want_verbose);

  if (!init_interface_io(g_hostname ? g_hostname : "127.0.0.1"))
    return 1;

  if (g_smiley_path)
    create_smiley_array(g_smiley_path, "smileys.xml");
  else
    create_smiley_array(".", "smileys.xml");
  gtk_main ();
  destroy_smiley_array();
  if (g_smiley_path) g_free(g_smiley_path);
  if (g_data_dir) g_free(g_data_dir);
  if (g_display) g_free(g_display);
  gui_set_glade_file(NULL);

  exit(0);
}
