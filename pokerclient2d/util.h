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

#ifndef _UTIL_H
#define _UTIL_H

#include <gtk/gtk.h>

void entry_numeric_constraint(GtkEditable *editable,
			      gchar *new_text,
			      gint new_text_length,
			      gint *position,
			      gpointer user_data);

void set_verbose(int verbose);

#endif /* _UTIL_H */
