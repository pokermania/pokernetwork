/* *
 * Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
 *                                24 rue vieille du temple, 75004 Paris
 *
 * This software's license gives you freedom; you can copy, convey,
 * propogate, redistribute and/or modify this program under the terms of
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
 *  Loic Dachary <loic@dachary.org>
 *
 */

#include <gtk/gtk.h>
#include <glade/glade.h>
#include <string.h>
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

static GtkWidget*	g_muck_window;
static gboolean		g_muck_window_shown = 0;
static GtkLayout*	g_screen = 0;

void	on_muck_show_button_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("show");
  set_string("muck");
  set_string("show");
  flush_io_channel();
  if (g_screen)
    gtk_widget_hide_all(g_muck_window);
}

void	on_muck_hide_button_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("hide");
  set_string("muck");
  set_string("hide");
  flush_io_channel();
  if (g_screen)
    gtk_widget_hide_all(g_muck_window);
}

void	on_muck_always_button_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("always");
  set_string("muck");
  set_string("always");
  flush_io_channel();
  if (g_screen)
    gtk_widget_hide_all(g_muck_window);
}

int	handle_muck(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  char*	tag = get_string();

  if (init)
    {
      g_screen = screen;
      g_muck_window = glade_xml_get_widget(g_glade_xml,
					   "muck_window");
      g_assert(g_muck_window);
      set_nil_draw_focus(g_muck_window);
      if(screen) gtk_layout_put(screen, g_muck_window, 0, 0);
      GUI_BRANCH(g_glade_xml, on_muck_show_button_clicked);
      GUI_BRANCH(g_glade_xml, on_muck_hide_button_clicked);
      GUI_BRANCH(g_glade_xml, on_muck_always_button_clicked);
    }

  
  if(!strcmp(tag, "show"))
    {
      if (screen != NULL || !g_muck_window_shown)
        {
          gui_center(g_muck_window, screen);
          g_muck_window_shown = 1;
        }
    }
  else if(!strcmp(tag, "hide"))
    {
      if (screen != NULL) 
        gtk_widget_hide_all(g_muck_window); 
    }

  return TRUE;
}
