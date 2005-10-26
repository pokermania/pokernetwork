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
 *  Loic Dachary <loic@gnu.org>
 *
 */

#include <gtk/gtk.h>
#include <glade/glade.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <locale.h>
#include "gui.h"
#include "interface_io.h"
#include "util.h"
#include "dispatcher.h"

static GtkWidget*	g_buy_in_window;
static GtkWidget*	g_max_radio;
static GtkWidget*	g_max_label;
static float		max_amount = 0.f;
static float		min_amount = 0.f;
static GtkWidget*	g_custom_radio;
static GtkWidget*	g_legend;
static GtkWidget*	g_custom_amount;

gboolean
on_custom_amount_focus_out_event       (GtkWidget       *widget,
                                        GdkEventFocus   *event,
                                        gpointer         user_data)
{
  (void) event;
  (void) user_data;
  const gchar* input = gtk_entry_get_text(GTK_ENTRY(widget));
  float amount = atof(input);

  char tmp[32];
  if(amount < min_amount || amount > max_amount) {
    snprintf(tmp, 32, "%.02f", min_amount);
    gtk_entry_set_text(GTK_ENTRY(widget), tmp);
  }
    
  return FALSE;
}

void (*on_custom_amount_insert_text)(GtkEditable *editable,
				     gchar *new_text,
				     gint new_text_length,
				     gint *position,
				     gpointer user_data) = entry_numeric_constraint;

void	on_ok_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;
  (void) widget;
  set_string("buy_in");
  char tmp[32];
  if(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(g_max_radio))) {
    snprintf(tmp, 32, "%.02f", max_amount);  
    set_string(tmp);
  } else {
    set_string(gtk_entry_get_text(GTK_ENTRY(g_custom_amount)));
  }

  flush_io_channel();
}

int	handle_buy_in(GladeXML*	g_glade_xml, GtkLayout* screen, int init)
{
  char*	tag = get_string();
  
  if (init)
    {
  setlocale(LC_NUMERIC, "C");
      g_buy_in_window = glade_xml_get_widget(g_glade_xml,
					     "buy_in_window");
      g_assert(g_buy_in_window);
      set_nil_draw_focus(g_buy_in_window);
      if(screen) gtk_layout_put(screen, g_buy_in_window, 0, 0);
      g_max_radio = glade_xml_get_widget(g_glade_xml,
					 "max_radio");
      g_assert(g_max_radio);
      g_max_label = glade_xml_get_widget(g_glade_xml,
					 "max_label");
      g_assert(g_max_label);
      g_custom_radio = glade_xml_get_widget(g_glade_xml,
					    "custom_radio");
      g_assert(g_custom_radio);
      g_custom_amount = glade_xml_get_widget(g_glade_xml,
					     "custom_amount");
      g_assert(g_custom_amount);
      g_legend = glade_xml_get_widget(g_glade_xml,
					     "legend");
      g_assert(g_legend);
      GUI_BRANCH(g_glade_xml, on_ok_clicked);
      GUI_BRANCH(g_glade_xml, on_custom_amount_focus_out_event);
      GUI_BRANCH(g_glade_xml, on_custom_amount_insert_text);
      gui_center(g_buy_in_window, screen);
      gtk_widget_hide_all(g_buy_in_window);
    }

  if(!strcmp(tag, "show"))
    {
      gtk_widget_show_all(g_buy_in_window);
    }
  else if(!strcmp(tag, "hide"))
    {
      gtk_widget_hide_all(g_buy_in_window); 
    }
  else if(!strcmp(tag, "params"))
    {
      char*	minimum_amount = get_string();
      char*	maximum_amount = get_string();
      char*	legend = get_string();
      char*	maximum_label = get_string();

      max_amount = atof(maximum_amount);
      min_amount = atof(minimum_amount);
      
      gtk_label_set_text(GTK_LABEL(g_max_label), maximum_amount);
      gtk_label_set_text(GTK_LABEL(g_legend), legend);
      gtk_entry_set_text(GTK_ENTRY(g_custom_amount), minimum_amount);
      gtk_button_set_label(GTK_BUTTON(g_max_radio), maximum_label);
      g_free(legend);
      g_free(minimum_amount);
      g_free(maximum_amount);
      g_free(maximum_label);
    }
  
  g_free(tag);

  return TRUE;
}
