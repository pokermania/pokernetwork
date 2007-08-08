#
# Copyright (C) 2007 Loic Dachary <loic@dachary.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
#
munindir = ${datadir}/munin/plugins
dist_munin_SCRIPTS = \
	poker_traffic_ \
	poker_players_ \
	poker_hands_

TESTS = \
	${srcdir}/test_poker_traffic_ \
	${srcdir}/test_poker_players_ \
	${srcdir}/test_poker_hands_

EXTRA_DIST = \
	${TESTS} \
	test_config.dat \
	test_wget1
