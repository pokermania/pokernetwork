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
#
# 
from twisted.internet import reactor, protocol, error
from struct import pack, unpack

from pokernetwork.packets import *
from pokernetwork.protocol import UGAMEProtocol
from pokernetwork.user import User

class UGAMEClientProtocol(UGAMEProtocol):
    """"""
    def __init__(self):
        self._ping_timer = None
        self.user = User()
        self.bufferized_packets = []
        UGAMEProtocol.__init__(self)
        self._ping_delay = 5

    def getSerial(self):
        return self.user.serial

    def getName(self):
        return self.user.name

    def getUrl(self):
        return self.user.url

    def getOutfit(self):
        return self.user.outfit

    def isLogged(self):
        return self.user.isLogged()
    
    def sendPacket(self, packet):
        if self.established != 0:
            self.ping()
            if self.factory.verbose > 2:
                print "%ssendPacket %s " % ( self._prefix, packet )
            self.transport.write(packet.pack())
        else:
            self.bufferized_packets.append(packet)

    def ping(self):
        if not hasattr(self, "_ping_timer") or not self._ping_timer:
            return

        if self._ping_timer.active():
            self._ping_timer.reset(self._ping_delay)
        else:
            if self.factory.verbose > 6:
                print "%ssend ping" % self._prefix
            self.transport.write(PacketPing().pack())
            self._ping_timer = reactor.callLater(self._ping_delay, self.ping)
        
    def protocolEstablished(self):
        self._ping_timer = reactor.callLater(self._ping_delay, self.ping)
        for packet in self.bufferized_packets:
            self.sendPacket(packet)
        self.bufferized_packets = []
            
    def connectionLost(self, reason):
        if hasattr(self, "_ping_timer") and self._ping_timer and self._ping_timer.active():
            self._ping_timer.cancel()
        self._ping_timer = None
        self.factory.protocol_instance = None
        UGAMEProtocol.connectionLost(self, reason)
        if not reason.check(error.ConnectionDone) and self.factory.verbose > 3:
            print "UGAMEClient.connectionLost %s" % reason

class UGAMEClientFactory(protocol.ClientFactory):

    def __init__(self, *args, **kwargs):
        self.protocol = UGAMEClientProtocol
        self.protocol_instance = None
        self.verbose = 0

    def buildProtocol(self, addr):
        instance = self.protocol()
        instance.factory = self
        self.protocol_instance = instance
        return instance

    def clientConnectionLost(self, connector, reason):
        pass
