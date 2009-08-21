#
# Copyright (C) 2007, 2009 Loic Dachary <loic@dachary.org>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#

MAINTAINERCLEANFILES = Makefile.in

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
