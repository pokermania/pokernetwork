/*
*
* Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
*                    24 rue vieille du temple, 75004 Paris
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
*  Jerome Jeannin <griim.work@gmail.com>
*
*/

#include "UnitTest++.h"
#include <iostream>

#include <gtk/gtk.h>
#include <glade/glade-build.h>

extern "C"
{
  void gui_set_glade_file(char* glade_file);  
  GladeXML* gui_load_widget(char* const);
  int handle_hand_history(GladeXML* g_glade_xml, GtkLayout* screen, int init);
  void set_string(const char* str);
  void flush_io_channel(void);
}

TEST( Lobby_handlehandhistory )
{
  gtk_init(NULL, NULL);
  char* glade_file = getenv("GLADE_FILE");
  gui_set_glade_file(glade_file);

  static GladeXML*  g_glade_xml = 0;

  GtkLayout* screen = 0;
  g_glade_xml = gui_load_widget("hand_history_window");

  set_string("test");
  flush_io_channel();

  handle_hand_history(g_glade_xml, screen, 1);
  CHECK(0 != g_glade_xml);
}
