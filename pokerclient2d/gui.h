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

#ifndef	_GUI_H_
#define	_GUI_H_

#include <glade/glade-build.h>
#include <gtk/gtk.h>

typedef struct position_t
{
  int	x, y;
  GtkLayout* screen;
} position_t;

void gui_set_glade_file(char* glade_file);
GladeXML*	gui_load_widget(const char* widget_name);
GtkWidget*	gui_get_widget(GladeXML* self, const char* widget_name);

void	gui_center(GtkWidget* window, GtkLayout* screen);
void	gui_bottom_left(GtkWidget* window, GtkLayout* screen);
void	gui_top_right(GtkWidget* window, GtkLayout* screen);
void	gui_bottom_right(GtkWidget* window, GtkLayout* screen);
void	gui_place(GtkWidget* window, position_t* position, GtkLayout* screen);
int   gui_width(GtkLayout* screen);
int   gui_height(GtkLayout* screen);

GtkWidget*  gui_create_image(GladeXML* xml, GType widget_type, GladeWidgetInfo* info);

#define GUI_BRANCH(xml, p)	glade_xml_signal_connect(xml, #p, (void*)p);

void set_nil_draw_focus(GtkWidget* widget);

#endif /* _GUI_H_ */
