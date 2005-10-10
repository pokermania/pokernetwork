#
# Copyright (C) 2004, 2005 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
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
# Authors:
#  Loic Dachary <loic@gnu.org>
#  Henry Precheur <henry@precheur.org>
#
# 
from twisted.internet import reactor, protocol

from pokernetwork.protocol import UGAMEProtocol

class PokerServerProtocol(UGAMEProtocol):
    """UGAMEServerProtocol"""

    def __init__(self):
        UGAMEProtocol.__init__(self)
        self._poll = False
        self.avatar = None

    def _handleConnection(self, packet):
        for packet in self.avatar.handlePacket(packet):
            self.sendPacket(packet)

    def sendPacket(self, packet):
        self.transport.write(packet.pack())

    def protocolEstablished(self):
        self.transport.setTcpKeepAlive(True)
        self.avatar = self.factory.createAvatar()
        self.avatar.setProtocol(self)

    def connectionLost(self, reason):
        if self.avatar:
            self.factory.destroyAvatar(self.avatar)
        del self.avatar
        UGAMEProtocol.connectionLost(self, reason)

