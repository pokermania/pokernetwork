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
 *  Henry Prêcheur <henry at precheur dot org>
 *  Loic Dachary <loic@gnu.org>
 *
 */

#include <gtk/gtk.h>
#include <glade/glade.h>
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

static GtkWidget*	g_message_window;
static GtkWidget*	g_credits_label;

static void	on_okbutton1_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  gtk_widget_hide_all(g_message_window);
  set_string("credits");
  flush_io_channel();
}

int	handle_credits(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  char*	message = get_string();

  if (init)
    {
      g_message_window = glade_xml_get_widget(g_glade_xml,
					      "credits_window");
      g_assert(g_message_window);
      set_nil_draw_focus(g_message_window);
      if(screen) gtk_layout_put(screen, g_message_window, 0, 0);
      g_credits_label = glade_xml_get_widget(g_glade_xml,
					     "credits_label");
      g_assert(g_credits_label);
      GUI_BRANCH(g_glade_xml, on_okbutton1_clicked);
    }

  gtk_label_set_markup(GTK_LABEL(g_credits_label), message);
  g_free(message);

  gui_center(g_message_window, screen);

  return TRUE;
}

