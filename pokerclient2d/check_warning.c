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
 *  Henry Prêcheur <henry@precheur.org>
 *
 */

#include <gtk/gtk.h>
#include <glade/glade.h>
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

static GtkWidget*	g_check_warning_window;
static gboolean		g_check_warning_window_shown = 0;
static GtkLayout*	g_screen = 0;

void	on_check_warning_fold_button_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("fold");
  set_string("check_warning");
  set_string("fold");
  flush_io_channel();
  if (g_screen)
    gtk_widget_hide_all(g_check_warning_window);
}

void	on_check_warning_check_button_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("check");
  set_string("check_warning");
  set_string("check");
  flush_io_channel();
  if (g_screen)
    gtk_widget_hide_all(g_check_warning_window);
}

void	on_check_warning_cancel_button_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  g_message("cancel");
  set_string("check_warning");
  set_string("cancel");
  flush_io_channel();
  if (g_screen)
    gtk_widget_hide_all(g_check_warning_window);
}

int	handle_check_warning(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  if (init)
    {
      g_screen = screen;
      g_check_warning_window = glade_xml_get_widget(g_glade_xml,
						    "check_warning_window");
      g_assert(g_check_warning_window);
      set_nil_draw_focus(g_check_warning_window);
      if(screen) gtk_layout_put(screen, g_check_warning_window, 0, 0);
      GUI_BRANCH(g_glade_xml, on_check_warning_fold_button_clicked);
      GUI_BRANCH(g_glade_xml, on_check_warning_check_button_clicked);
      GUI_BRANCH(g_glade_xml, on_check_warning_cancel_button_clicked);
    }

  
  if (screen != NULL || !g_check_warning_window_shown)
    {
      gui_center(g_check_warning_window, screen);
      g_check_warning_window_shown = 1;
    }

  return TRUE;
}
