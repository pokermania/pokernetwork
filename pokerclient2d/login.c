/* *
 * Copyright (C) 2004, 2005 Mekensleep
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
 *  Henry Prêcheur <henry at precheur dot org>
 *
 */

#include <stdio.h>
#include <string.h>
#include <glib/gprintf.h>
#include <gtk/gtk.h>
#include <glade/glade.h>
#include "gui.h"
#include "interface_io.h"

static GtkWidget*	g_login_window;
static GtkWidget*	g_login_entry;
static GtkWidget*	g_password_entry;
static GtkWidget*	g_remember_password;

static void	on_password_entry_activate(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("login ok");
  g_printf("login: %s\npass: %s\n",
	   gtk_entry_get_text(GTK_ENTRY(g_login_entry)),
	   gtk_entry_get_text(GTK_ENTRY(g_password_entry)));
  set_string("login");
  set_string("ok");
  set_string(gtk_entry_get_text(GTK_ENTRY(g_login_entry)));
  set_string(gtk_entry_get_text(GTK_ENTRY(g_password_entry)));
  set_int(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(g_remember_password)));
  flush_io_channel();
  gtk_widget_hide_all(g_login_window);
}

static void	on_login_cancel_button_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  set_string("login");
  set_string("cancel");
  set_string("");
  set_string("");
  set_int(0);
  flush_io_channel();
  gtk_widget_hide_all(g_login_window);
}

static void	on_create_account_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  set_string("login");
  set_string("create");
  set_string(gtk_entry_get_text(GTK_ENTRY(g_login_entry)));
  set_string(gtk_entry_get_text(GTK_ENTRY(g_password_entry)));
  set_int(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(g_remember_password)));
  flush_io_channel();
  gtk_widget_hide_all(g_login_window);
}

static void	on_login_entry_activate(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  gtk_widget_grab_focus(g_password_entry);
}

int	handle_login(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  char* tag = get_string();

  if (init)
    {
      g_login_window = glade_xml_get_widget(g_glade_xml, "login_window");
      g_assert(g_login_window);
      set_nil_draw_focus(g_login_window);
      if(screen) gtk_layout_put(screen, g_login_window, 0, 0);
      g_login_entry = glade_xml_get_widget(g_glade_xml, "login_entry");
      g_assert(g_login_entry);
      g_password_entry = glade_xml_get_widget(g_glade_xml,
                                              "password_entry");
      g_assert(g_password_entry);
      g_remember_password = glade_xml_get_widget(g_glade_xml,
                                                 "remember_password");
      g_assert(g_remember_password);
      GUI_BRANCH(g_glade_xml, on_password_entry_activate);
      GUI_BRANCH(g_glade_xml, on_login_entry_activate);
      GUI_BRANCH(g_glade_xml, on_login_cancel_button_clicked);
      GUI_BRANCH(g_glade_xml, on_create_account_clicked);
      GUI_BRANCH(g_glade_xml, gtk_widget_grab_focus);
      gtk_widget_hide_all(g_login_window);
    }

  if(!strncmp(tag, "hide", 4)) {
    gtk_widget_hide_all(g_login_window);
  } else {
    char* default_name = tag;
    char* default_password = get_string();
    int	remember_password = get_int();

    gtk_entry_set_text(GTK_ENTRY(g_login_entry), default_name);
    gtk_entry_set_text(GTK_ENTRY(g_password_entry), default_password);
    if (strcmp(default_name, "") != 0)
      gtk_widget_grab_focus(g_password_entry);
    if (remember_password)
      gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(g_remember_password), TRUE);
    g_free(default_password);

    gui_center(g_login_window, screen);
  }

  g_free(tag);

  return TRUE;
}
