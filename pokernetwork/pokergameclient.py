# -*- py-indent-offset: 4; coding: iso-8859-1; mode: python -*-
#
# Copyright (C) 2007, 2008 Loic Dachary <loic@dachary.org>
#
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
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
from pokerengine.pokergame import PokerGameClient

class PokerNetworkGameClient(PokerGameClient):
    SERIAL_IN_POSITION = 0
    POSITION_OBSOLETE = 1

    def __init__(self, url, dirs):
        PokerGameClient.__init__(self, url, dirs)
        self.level_skin = ""
        self.currency_serial = 0
        self.history_index = 0
        self.position_info = [ 0, 0 ]
