/*
*
* Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
*                    24 rue vieille du temple, 75004 Paris
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
}

TEST( Gui_loadWidget )
{
  gtk_init(NULL, NULL);

  static GladeXML* test_gladeXml = 0;
  char* glade_file = getenv("GLADE_FILE");
  gui_set_glade_file(glade_file);
  test_gladeXml = gui_load_widget("login_window");
  CHECK( 0 != test_gladeXml);
}

