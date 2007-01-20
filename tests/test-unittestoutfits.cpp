/*
*
* Copyright (C) 2006 Mekensleep
*
*	Mekensleep
*	24 rue vieille du temple
*	75004 Paris
* licensing@mekensleep.com
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
* Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
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
