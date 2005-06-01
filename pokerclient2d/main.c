/* *
 * Copyright (C) 2004 Mekensleep
 *
 *	Mekensleep
 *	24 rue vieille du temple
 *	75004 Paris
 *       licensing@mekensleep.com
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * Authors:
 *  Henry Prêcheur <henry@precheur.org>
 *  Loic Dachary <loic@gnu.org>
 *
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif /* HAVE_CONFIG_H */

#include <glade/glade.h>
#include "util.h"
#include "gui.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gtk/gtk.h>
#include <argp.h>
#include <unistd.h>
#include "interface_io.h"
#include "dispatcher.h"

void create_smiley_array(const char *path, const char *filename);
void destroy_smiley_array(void);

/*
 * Command line parsing
 */
int	g_want_verbose;
int	g_port_number;
char*	g_display;
char*	g_hostname;
char*	g_gtk_rc_file;
char*	g_data_dir;
char*	g_smiley_path;

static struct argp_option options[] =
{
  { "port",	'p',	"PORT-NUMBER",	0,
    "Specify port number of the server",	0 },
  { "display",	'd',	"DISPLAY",	0,
    "Display to connect to",	0 },
  { "datadir",	'D',	"DATADIR",	0,
    "Directory containing data",	0 },
  { "glade",	'g',	"GLADE",	0,
    "Glade file",	0 },
  { "verbose",	'v',	"VERBOSE-LEVEL",	0,
    "Print more information",	0 },
  { "gtkrc",	'r',	"GTK-RC-FILE",	0,
    "Specify gtk+2 recourse file",	0 },
  { "smiley",	's',	"SMILEY-PATH",	0,
    "Specify smiley's image and xml path",	0 },
  { NULL, 0, NULL, 0, NULL, 0 }
};

static void show_version (FILE *stream, struct argp_state *state)
{
  (void) state;
  fputs("poker3d-interface\n", stream);
  fprintf(stream, "Copyright (C) %s %s\n", "2004", "Mekensleep");
  fputs("\
This program is free software; you may redistribute it under the terms of\n\
the GNU General Public License.  This program has absolutely no warranty.\n",
	stream);
}

/* Parse a single option.  */
static error_t
parse_opt (int key, char *arg, struct argp_state *state)
{
  switch (key)
    {
    case ARGP_KEY_INIT:
      g_want_verbose = 0;
      g_port_number = 19379;
      g_hostname = 0;
      g_display = 0;
      g_gtk_rc_file = 0;
      g_smiley_path = 0;
      break;

    case 'p':			/* --port */
      g_port_number = atoi(arg);
      break;
    case 'v':			/* --verbose */
      g_want_verbose = atoi(arg);
      break;
    case 'd':			/* --display */
      g_display = g_strdup(arg);
      break;
    case 'r':
      g_gtk_rc_file = g_strdup(arg);
      break;
    case 'D':
      g_data_dir = g_strdup(arg);
      break;
    case 'g':
      gui_set_glade_file(arg);
      break;
    case 's':			/* -s smiley */
      g_smiley_path = g_strdup(arg);
      break;
    case ARGP_KEY_ARG:		/* [FILE]... */
      /* TODO: Do something with ARG, or remove this case and make
         main give argp_parse a non-NULL fifth argument.  */
      if (g_hostname)
	argp_failure (state, 1, errno,
		      "More than one hostname specified");
      else
	g_hostname = g_strdup(arg);
      break;

    default:
      return ARGP_ERR_UNKNOWN;
    }
  return 0;
}

/* The argp functions examine these global variables.  */
const char *argp_program_bug_address = "<henry@mekensleep.org>";
void (*argp_program_version_hook) (FILE *, struct argp_state *) = show_version;

static struct argp argp =
{
  options, parse_opt, "[HOSTNAME]",
  "Poker3D lobby",
  NULL, NULL, NULL
};

gboolean	handle_network(GIOChannel *source,
                         GIOCondition condition,
                         gpointer data)
{
  (void) source;
  (void) condition;
  (void) data;
  g_message("handle_network");
  dispatcher(0);
  return TRUE;
}

int main(int   argc,
	 char *argv[])
{
  if(setpgrp() < 0)
    perror("setpgrp()");

  if (argp_parse(&argp, argc, argv, 0, NULL, NULL) != 0)
    return 1;

  if (g_display)
    {
      char	tmp[64];
      snprintf(tmp, sizeof (tmp), "DISPLAY=%s", g_display);
      putenv(tmp);
    }

  if (g_gtk_rc_file)
    {
      char*	tmp[2] = { g_gtk_rc_file, 0 };
      gtk_rc_set_default_files(tmp);
      g_free(g_gtk_rc_file);
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
  if (g_smiley_path)
    g_free(g_smiley_path);
  return 0;
}
