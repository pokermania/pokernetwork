/* *
 * Copyright (C) 2005, 2006 Mekensleep
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
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
 *
 * Authors:
 *  Loic Dachary <loic@gnu.org>
 *
 */

#include <gtk/gtk.h>
#include <glade/glade.h>
#include <string.h>
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

static GtkWidget*	g_menu_window;
static int s_disable_callbacks = FALSE;

#define on_item_activate(WHAT) \
void on_##WHAT##_activate(GtkWidget* widget, gpointer data) \
{ \
  (void) data; \
  (void) widget; \
  if(s_disable_callbacks) return; \
  set_string("menu"); \
  set_string(#WHAT); \
  set_string("1"); \
  flush_io_channel(); \
}

on_item_activate(cashier)
on_item_activate(outfits)
on_item_activate(hand_history)
on_item_activate(edit_account)
on_item_activate(quit)
on_item_activate(tables_list)
on_item_activate(tournaments)
on_item_activate(login)

#define on_check_activate(WHAT) \
void	on_##WHAT##_activate(GtkWidget *widget, gpointer user_data) \
{ \
  (void) user_data; \
  if(s_disable_callbacks) return; \
  set_string("menu"); \
  set_string(#WHAT); \
  if(gtk_check_menu_item_get_active(GTK_CHECK_MENU_ITEM(widget))) { \
    set_string("yes"); \
  } else { \
    set_string("no"); \
  } \
  flush_io_channel(); \
}

on_check_activate(graphics)
on_check_activate(sound)
on_check_activate(fullscreen)
on_check_activate(auto_post)
on_check_activate(remember_me)
on_check_activate(muck)

#define on_radio_activate(GROUP, WHAT) \
void on_##WHAT##_activate(GtkWidget* widget, gpointer data) \
{ \
  (void) data; \
  if(s_disable_callbacks) return; \
  if(gtk_check_menu_item_get_active(GTK_CHECK_MENU_ITEM(widget))) { \
    set_string("menu"); \
    set_string(#GROUP); \
    set_string(#WHAT); \
    flush_io_channel(); \
  } \
}

on_radio_activate(resolution, resolution_auto)
on_radio_activate(resolution, 1024x768)
on_radio_activate(resolution, 1280x800)
on_radio_activate(resolution, 1280x1024)
on_radio_activate(resolution, 1366x1024)
on_radio_activate(resolution, 1400x1050)
on_radio_activate(resolution, 1600x1200)
on_radio_activate(resolution, 1680x1050)
on_radio_activate(resolution, 1920x1200)

int	handle_menu(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  char*	tag = get_string();

  if (init) {
    g_menu_window = glade_xml_get_widget(g_glade_xml,
                                         "menu_window");
    g_assert(g_menu_window);
    set_nil_draw_focus(g_menu_window);
    if(screen) gtk_layout_put(screen, g_menu_window, 0, 0);

#define branch(WHAT) GUI_BRANCH(g_glade_xml, on_##WHAT##_activate)
    branch(cashier);
    branch(outfits);
    branch(hand_history);
    branch(edit_account);
    branch(quit);
    branch(tables_list);
    branch(tournaments);
    branch(login);
    branch(graphics);
    branch(sound);
    branch(fullscreen);
    branch(auto_post);
    branch(remember_me);
    branch(muck);
    branch(resolution_auto);
    branch(1024x768);
    branch(1280x800);
    branch(1280x1024);
    branch(1366x1024);
    branch(1400x1050);
    branch(1600x1200);
    branch(1680x1050);
    branch(1920x1200);

    static position_t	menu_position;
    menu_position.x = 0;
    menu_position.y = 0;

    gui_place(g_menu_window, &menu_position, screen);
    gtk_widget_hide_all(g_menu_window);
  }

  if(!strcmp(tag, "show")) {

    /*
     * calculate windows position
     */
    //    gtk_widget_set_size_request(g_menu_window, screen_width, -1 ); // -1 because we don't want to change height of menubar
    gtk_widget_show_all(g_menu_window);
  } else if(!strcmp(tag, "hide")) {
    gtk_widget_hide_all(g_menu_window);
  } else if(!strcmp(tag, "set")) {
    char* what = get_string();
    char* value = get_string();

    s_disable_callbacks = TRUE;
#define set_check(WHAT) \
    else if(!strcmp(what, #WHAT)) { \
      GtkCheckMenuItem* widget = GTK_CHECK_MENU_ITEM(glade_xml_get_widget(g_glade_xml, #WHAT)); \
      g_assert(widget); \
      gtk_check_menu_item_set_active(widget, !strcmp(value, "yes") || !strcmp(value, "on")); \
    } 
    
    if(0) {
    }
    set_check(graphics)
      set_check(sound)
      set_check(fullscreen)
      set_check(auto_post)
      set_check(remember_me)
      set_check(muck)
    else if(!strcmp(what, "resolution")) {
      GtkCheckMenuItem* widget = GTK_CHECK_MENU_ITEM(glade_xml_get_widget(g_glade_xml, value));
      gtk_check_menu_item_set_active(widget, TRUE);
    }

    s_disable_callbacks = FALSE;
    g_free(what);
    g_free(value);
  }

  g_free(tag);

  return TRUE;
}

