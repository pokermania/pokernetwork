/* *
 * Copyright (C) 2005, 2006 Mekensleep
 *
 *	Mekensleep
 *	24 rue vieille du temple
 *	75004 Paris
 *  licensing@mekensleep.com
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
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
 */

#include <string.h>
#include <stdio.h>
#include <stdlib.h>

char	string_buffer[4096];
char*	string = string_buffer;

void	flush_io_channel(void)
{
}

void set_string(const char* str)
{
  string += sprintf(string, "%s", str) + 1;
}

void	set_int(int i)
{
  string += sprintf(string, "%d", i) + 1;
}

char*	get_string(void)
{
  char* result = malloc(strlen(string));
  return result;
}

int	get_int(void)
{
  return 1;
}
