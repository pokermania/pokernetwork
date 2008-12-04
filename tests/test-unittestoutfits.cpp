/*
*
* Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
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
  int handle_outfit(GladeXML* g_glade_outfit_sex_xml, GladeXML* g_glade_outfit_ok_xml, GladeXML* g_glade_outfit_slots_male_xml, GladeXML* g_glade_outfit_slots_female_xml, GladeXML* g_glade_outfit_params_xml, GladeXML* g_glade_outfit_random_xml, GtkLayout* screen, int init);
  void set_string(const char* str);
  void flush_io_channel(void);
  char* g_data_dir = 0;
}

TEST( Outfit_handleOutfit )
{

  gtk_init(NULL, NULL);

  char* glade_file = getenv("GLADE_FILE");
  gui_set_glade_file(glade_file);

  GtkLayout* screen = 0;

  static GladeXML* g_glade_outfit_sex_xml = gui_load_widget("outfit_sex_window");
  static GladeXML* g_glade_outfit_ok_xml = gui_load_widget("outfit_ok_window");
  static GladeXML* g_glade_outfit_slots_male_xml = gui_load_widget("outfit_slots_male_window");
  static GladeXML* g_glade_outfit_params_xml = gui_load_widget("outfit_params_window");
  static GladeXML* g_glade_outfit_random_xml = gui_load_widget("outfit_random_window");
  static GladeXML* g_glade_outfit_slots_female_xml = gui_load_widget("outfit_slots_female_window");

  set_string("test");
  flush_io_channel();

  int return_handle = handle_outfit(g_glade_outfit_sex_xml, g_glade_outfit_ok_xml, g_glade_outfit_slots_male_xml, g_glade_outfit_slots_female_xml, g_glade_outfit_params_xml, g_glade_outfit_random_xml, screen, 1);
  CHECK(return_handle);
}
