/* *
 * Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
 *                                24 rue vieille du temple, 75004 Paris
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
