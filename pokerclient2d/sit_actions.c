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
 *  Loic Dachary <loic@gnu.org>
 *
 */

#include <gtk/gtk.h>
#include <glade/glade.h>
#include <string.h>
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

static GtkWidget*	g_sit_actions_window;
static gboolean		g_sit_actions_disable = FALSE;

void	on_auto_post_blinds_toggled(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;

  if(g_sit_actions_disable)
    return;

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

void	on_sit_out_next_hand_toggled(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;

  if(g_sit_actions_disable)
    return;

  set_string("sit_actions");
  set_string("sit_out");
  if(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(widget)))
    {
      g_message("sit out next hand");
      set_string("yes");
    }
  else
    {
      g_message("do not sit out next hand");
      set_string("no");
    }
  
  flush_io_channel();
}

int	handle_sit_actions(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  char*	tag = get_string();
  
  if (init)
    {
      g_sit_actions_window = glade_xml_get_widget(g_glade_xml,
                                                  "sit_actions_window");
      g_assert(g_sit_actions_window);
      set_nil_draw_focus(g_sit_actions_window);
      if(screen) gtk_layout_put(screen, g_sit_actions_window, 0, 0);
      GUI_BRANCH(g_glade_xml, on_auto_post_blinds_toggled);
      GUI_BRANCH(g_glade_xml, on_sit_out_next_hand_toggled);
    }

  g_sit_actions_disable = TRUE;
  if(!strcmp(tag, "show"))
    {
      gui_bottom_left(g_sit_actions_window, screen);
    }
  else if(!strcmp(tag, "hide"))
    {
      GtkWidget* sit_out_next_hand = glade_xml_get_widget(g_glade_xml,
                                                          "sit_out_next_hand");
      gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(sit_out_next_hand), FALSE);

      gtk_widget_hide_all(g_sit_actions_window); 
    }
  else if(!strcmp(tag, "auto"))
    {
      char*	state = get_string();
      gboolean bool_state = !strcmp(state, "yes");
      gboolean show = strcmp(state, "None");
      GtkWidget* auto_blind = glade_xml_get_widget(g_glade_xml,
                                                   "auto_post_blinds");
      if(show) {
        gtk_widget_show(auto_blind);
        gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(auto_blind), bool_state);
      } else {
        gtk_widget_hide(auto_blind);
      }

      g_free(state);
    }
  else if(!strcmp(tag, "sit_out"))
    {
      char*	state = get_string();
      char*	message = get_string();
      gboolean bool_state = !strcmp(state, "yes");
      GtkWidget* sit_out_next_hand = glade_xml_get_widget(g_glade_xml,
                                                          "sit_out_next_hand");
      gtk_button_set_label(GTK_BUTTON(sit_out_next_hand), message);
      gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(sit_out_next_hand), bool_state);

      g_free(state);
      g_free(message);
    }
  g_sit_actions_disable = FALSE;
  
  g_free(tag);

  return TRUE;
}
