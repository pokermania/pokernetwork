# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
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
from pokerengine.pokergame import PokerGameClient
from pokernetwork import log as network_log
log = network_log.getChild('pokergameclient')

class PokerNetworkGameClient(PokerGameClient):
    SERIAL_IN_POSITION = 0
    POSITION_OBSOLETE = 1

    def __init__(self, url, dirs):
        PokerGameClient.__init__(self, url, dirs)
        self.log = log.getChild(self.__class__.__name__)
        self.level_skin = ""
        self.currency_serial = 0
        self.history_index = 0
        self.position_info = [ 0, 0 ]

    def reset(self):
        PokerGameClient.reset(self)
        self.resetStaticPlayerList()

    def cancelState(self):
        self.resetStaticPlayerList()
        return PokerGameClient.cancelState(self)

    def endState(self):
        self.resetStaticPlayerList()
        return PokerGameClient.endState(self)

    def resetStaticPlayerList(self):
        self.static_player_list = None

    def setStaticPlayerList(self, player_list):
        self.static_player_list = player_list[:]

    def getStaticPlayerList(self):
        return self.static_player_list
      
    def buildPlayerList(self, with_wait_for):
        self.player_list = self.getStaticPlayerList()
        self.log.debug("buildPlayerList %s", self.player_list)
        return True
