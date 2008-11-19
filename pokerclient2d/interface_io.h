/*
 *
 * Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
 *                                24 rue vieille du temple, 75004 Paris
 *
 * This software's license gives you freedom; you can copy, convey,
 * propogate, redistribute and/or modify this program under the terms of
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
 * Henry Precheur	<henry at precheur dot org>
 *
 */

#ifndef	_INTERFACE_IO_H_
#define	_INTERFACE_IO_H_

char*	get_string(void);
int	get_int(void);

void	set_string(const char* str);
void	set_int(int i);
void	flush_io_channel(void);

int	init_interface_io(const char* adress);

#endif /* _INTERFACE_IO_H_ */
