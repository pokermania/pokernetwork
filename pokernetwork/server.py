#
# Copyright (C) 2006, 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
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
# Authors:
#  Loic Dachary <loic@dachary.org>
#  Henry Precheur <henry@precheur.org> (2004)
#
#
from twisted.internet import reactor, protocol, defer

from pokernetwork import log as network_log
log = network_log.get_child('server')

from pokernetwork.protocol import UGAMEProtocol
from pokerpackets.packets import PacketError
from pokernetwork.util.trace import format_exc

from reflogging import deprecated

class PokerServerProtocol(UGAMEProtocol):
    """UGAMEServerProtocol"""

    log = log.get_child('PokerServerProtocol')

    def __init__(self):
        self.avatar = None
        UGAMEProtocol.__init__(self)
        self._keepalive_delay = 10

    def packetReceived(self, packet):
        try:
            if self.avatar:
                self.sendPackets(self.avatar.handlePacket(packet))
        except:
            self.log.error(format_exc())
            self.transport.loseConnection()

    def protocolEstablished(self):
        self.transport.setTcpKeepAlive(True)
        self._keepalive_delay = self.factory.service._keepalive_delay
        self.avatar = self.factory.createAvatar()
        self.avatar.setProtocol(self)

    def connectionLost(self, reason):
        if self.avatar:
            self.factory.destroyAvatar(self.avatar)
        self.avatar = None
        UGAMEProtocol.connectionLost(self, reason)
