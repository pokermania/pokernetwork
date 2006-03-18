/* *
 * Copyright (C) 2004, 2005, 2006 Mekensleep
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

static gboolean		g_sit_actions_disable = FALSE;

static GtkWidget*	g_blind_window;
static GtkWidget*	g_blind_message;
static GtkWidget*	g_blind_window_shown;

static void	on_blind_no_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("no");
  set_string("blind");
  set_string("post");
  set_string("no");
  flush_io_channel();
}

static void	on_blind_yes_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("yes");
  set_string("blind");
  set_string("post");
  set_string("yes");
  flush_io_channel();
}

static void	on_wait_blind_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("yes");
  set_string("blind");
  set_string("post");
  set_string("wait");
  flush_io_channel();
}

static void	on_auto_post_toggled(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;

  if(g_sit_actions_disable) {
    g_message("g_sit_actions_disable");
    return;
  }

  set_string("sit_actions");
  set_string("auto");
  if(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(widget)))
    {
      g_message("auto post blind");
      set_string("yes");
    }
  else
    {
      g_message("no auto post blind");
      set_string("no");
    }
  
  flush_io_channel();
}


int	handle_blind(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  char*	tag = get_string();
  
  if (init)
    {
      g_blind_window = glade_xml_get_widget(g_glade_xml,
                                            "blind_window");
      g_assert(g_blind_window);
      set_nil_draw_focus(g_blind_window);
      if(screen) gtk_layout_put(screen, g_blind_window, 0, 0);
      g_blind_message = glade_xml_get_widget(g_glade_xml,
                                             "post_blind_message");
      g_assert(g_blind_message);
      GUI_BRANCH(g_glade_xml, on_blind_no_clicked);
      GUI_BRANCH(g_glade_xml, on_blind_yes_clicked);
      GUI_BRANCH(g_glade_xml, on_wait_blind_clicked);
      GUI_BRANCH(g_glade_xml, on_auto_post_toggled);

      gui_center(g_blind_window, screen);
    }

  if(!strcmp(tag, "show"))
    {
      if (screen != NULL || !g_blind_window_shown) 
        {
          gtk_widget_show_all(g_blind_window);
          g_blind_window_shown = 1;
        }
    }
  else if(!strcmp(tag, "hide"))
    {
      GtkWidget* auto_post = glade_xml_get_widget(g_glade_xml, "auto_post");
      g_sit_actions_disable = TRUE;
      gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(auto_post), FALSE);
      g_sit_actions_disable = FALSE;

      if (screen != NULL) 
        gtk_widget_hide_all(g_blind_window); 
    }
  else if(!strcmp(tag, "blind message"))
    {
      char*	message = get_string();
      char*	wait_blind = get_string();

      gtk_label_set_text(GTK_LABEL(g_blind_message), message);
      GtkWidget* post_blind_widget = glade_xml_get_widget(g_glade_xml,
                                                          "post_blind");
      GtkWidget* wait_blind_widget = glade_xml_get_widget(g_glade_xml,
                                                          "wait_blind");
      g_assert(post_blind_widget);
      g_assert(wait_blind_widget);
      if(strlen(message) > 0)
        {
          gtk_widget_set_sensitive(post_blind_widget, TRUE);
        }
      else
        {
          gtk_widget_set_sensitive(post_blind_widget, FALSE);
        }

      if(!strcmp(wait_blind, "yes"))
        {
          gtk_widget_set_sensitive(wait_blind_widget, TRUE);
        }
      else
        {
          gtk_widget_set_sensitive(wait_blind_widget, FALSE);
        }
	
      g_free(message);
      g_free(wait_blind);
    }
  
  g_free(tag);

  return TRUE;
}
