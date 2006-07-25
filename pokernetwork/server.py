#
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
from twisted.internet import reactor, protocol, defer

from pokernetwork.protocol import UGAMEProtocol

class PokerServerProtocol(UGAMEProtocol):
    """UGAMEServerProtocol"""

    def __init__(self):
        UGAMEProtocol.__init__(self)
        self._poll = False
        self.avatar = None
        self._ping_delay = 10
        self._ping_timer = None

    def _handleConnection(self, packet):
        self.ping()
        self.sendPackets(self.avatar.handlePacket(packet))

    def sendPackets(self, packets):
        self.unblock()
        if not hasattr(self, 'transport') or not self.transport:
            #
            # Just trash packets sent when the connection is down
            #
            if self.factory.verbose:
                print "server: packets " + str(packets) + " thrown away because the protocol has no usuable transport"
            return
        while len(packets) > 0:
            packet = packets.pop(0)
            if isinstance(packet, defer.Deferred):
                packet.addCallback(self.unshiftPacket, packets)
                #
                # No packet may be received while sending the answer to
                # a previous packet.
                #
                self.block()
                break
            else:
                self.sendPacket(packet)

    def unshiftPacket(self, packet, packets):
        packets.insert(0, packet)
        self.sendPackets(packets)

    def sendPacket(self, packet):
        self.transport.write(packet.pack())

    def protocolEstablished(self):
        self.transport.setTcpKeepAlive(True)
        self._ping_delay = self.factory.service._ping_delay
        self.avatar = self.factory.createAvatar()
        self.avatar.setProtocol(self)
        self._ping_timer = reactor.callLater(self._ping_delay, self.ping)

    def connectionLost(self, reason):
        if hasattr(self, "_ping_timer") and self._ping_timer and self._ping_timer.active():
            self._ping_timer.cancel()
        self._ping_timer = None
        if self.avatar:
            self.factory.destroyAvatar(self.avatar)
        del self.avatar
        UGAMEProtocol.connectionLost(self, reason)

    def protocolInvalid(self, client, server):
        if self.factory.verbose:
                print "client with protocol %s rejected (need %s)" % ( client, server )

    def ping(self):
        if not hasattr(self, "_ping_timer") or not self._ping_timer:
            return

        if self._ping_timer.active():
            if self.factory.verbose > 6 and hasattr(self, "user") and self.user:
                print "ping: renew %s/%s" % ( self.user.name, self.user.serial )
            self._ping_timer.reset(self._ping_delay)
        else:
            self._ping_timer = None
            if self.factory.verbose and hasattr(self, "user") and self.user:
                print "ping: timeout %s/%s" % ( self.user.name, self.user.serial )
            self.transport.loseConnection()
