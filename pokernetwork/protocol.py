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
#
# 
import sys
from time import time

from twisted.internet import reactor, protocol

from pokernetwork.packets import Packet, PacketFactory, PacketNames
from pokernetwork import protocol_number
from pokernetwork.version import Version

protocol_version = Version(protocol_number)

PROTOCOL_MAJOR = "%03d" % protocol_version.major()
PROTOCOL_MINOR = "%d%02d" % ( protocol_version.medium(), protocol_version.minor() )

class Queue:
    def __init__(self):
        self.delay = 0
        self.packets = []
        
class UGAMEProtocol(protocol.Protocol):
    """UGAMEProtocol"""

    def __init__(self):
        self._packet = []
        self._packet_len = 0
        self._timer = None
        self._packet2id = lambda x: 0
        self._packet2front = lambda x: False
        self._handler = self._handleConnection
        self._queues = {}
        self._lagmax = 0
        self._prefix = ""
        self._blocked = False
        self.established = 0
        self._poll = True
        self._ping_delay = 5

    def setPingDelay(self, ping_delay):
        self._ping_delay = ping_delay

    def getPingDelay(self):
        return self._ping_delay
    
    def getOrCreateQueue(self, id):
        if not self._queues.has_key(id):
            self._queues[id] = Queue()
        return self._queues[id]
            
    def connectionMade(self):
        "connectionMade"
        self._sendVersion()

    def connectionLost(self, reason):
        self.established = 0
        
    def _sendVersion(self):
        self.transport.write('CGI %s.%s\n' % ( PROTOCOL_MAJOR, PROTOCOL_MINOR ) )

    def _handleConnection(self):
        pass

    def ignoreIncomingData(self):
        if self._timer and self._timer.active():
            self._timer.cancel()
        
    def _handleVersion(self):
        buffer = ''.join(self._packet)
        if '\n' in buffer:
            if buffer[:3] == 'CGI':
                major, minor = buffer[4:11].split('.')
                if (major, minor) != ( PROTOCOL_MAJOR, PROTOCOL_MINOR ):
                    self.protocolInvalid(major + "." + minor, PROTOCOL_MAJOR + "." + PROTOCOL_MINOR)
                    self.transport.loseConnection()
                    return
            buffer = buffer[12:]
            self.established = 1
            self._packet[:] = [buffer]
            self._packet_len = len(buffer)
            self._expected_len = Packet.format_size
            if self.factory.verbose > 1:
                print "protocol established"
            self.protocolEstablished()
            if self._packet_len > 0:
                self.dataReceived("")
            self._processQueues()
        else:
            self._packet[:] = [buffer]
            self._packet_len = len(buffer)

    def protocolEstablished(self):
        pass

    def protocolInvalid(self, server, client):
        pass
    
    def hold(self, delay, id = None):
        if delay > 0:
            delay = time() + delay
        if id == None:
            for (id, queue) in self._queues.iteritems():
                queue.delay = delay
        else:
            self.getOrCreateQueue(id).delay = delay

    def block(self):
        self._blocked = True

    def unblock(self):
        self._blocked = False
        
    def discardPackets(self, id):
        if self._queues.has_key(id):
            self._queues[id] = Queue()
            del self._queues[id]

    def canHandlePacket(self, packet):
        return True
    
    def _processQueues(self):
        if not self._blocked:
            now = time()
            to_delete = []
            #
            # Shallow copy the queues list so that 
            # self.discardPacket can remove an entry
            # without conpromizing the for loop on queues
            #
            queues = self._queues.copy()
            #
            # Process exactly one packet in each queue
            #
            for (id, queue) in queues.iteritems():
                if len(queue.packets) <= 0:
                    if queue.delay <= now:
                        to_delete.append(id)
                    continue
                #
                # If lagging behind too much, ignore the imposed delay
                #
                lag = now - queue.packets[0].time__
                if queue.delay > now and lag > self._lagmax:
                    print " => queue %d delay canceled because lag too high" % id
                    queue.delay = 0
                #
                # If time has come, process one packet
                #
                if queue.delay <= now:
                    if queue.packets[0].nodelay__:
                        ( can_handle, delay ) = ( True, 0 )
                    else:
                        ( can_handle, delay ) = self.canHandlePacket(queue.packets[0])
                    if can_handle:
                        packet = queue.packets.pop(0)
                        del packet.time__
                        del packet.nodelay__
                        self._handler(packet)
                    elif delay > now:
                        queue.delay = delay
                else:
                    if self.factory.verbose > 5:
                        print "wait %s seconds before handling the next packet in queue %s" % ( str(queue.delay - now), str(id) )
            #
            # Remove empty queues for which there is no delay
            #
            for id in to_delete:
                del self._queues[id]

        #
        # Reconsider the situation every 1/100 seconds
        #
        if not self._timer or not self._timer.active():
            if self._poll or len(self._queues) > 0:
                self._timer = reactor.callLater(0.01, self._processQueues)            

    def pushPacket(self, packet):
        id = self._packet2id(packet)
        if id != None:
            packet.time__ = time()
            front = self._packet2front(packet)
            if front and self._queues.has_key(id):
                packet.nodelay__ = True
                self._queues[id].packets.insert(0, packet)
            else:
                packet.nodelay__ = False
                self.getOrCreateQueue(id).packets.append(packet)
        
    def handleData(self):
        if self._packet_len >= self._expected_len:
            type = Packet()
            buffer = ''.join(self._packet)
            while len(buffer) >= self._expected_len:
                type.unpack(buffer)
                if type.length <= len(buffer):

                    if PacketFactory.has_key(type.type):
                        packet = PacketFactory[type.type]()
                        buffer = packet.unpack(buffer)
                        if self.factory.verbose > 4:
                            print "%s(%d bytes) => %s" % ( self._prefix, type.length, packet )
                        if self._poll:
                            self.pushPacket(packet)
                        else:
                            self._handler(packet)
                    else:
                        print "%s: unknown message received (id %d, length %d)\n" % ( self._prefix, type.type, type.length )
                        if self.factory.verbose > 4:
                            print "known types are %s " % PacketNames
                        buffer = buffer[type.length:]
                    self._expected_len = Packet.format_size
                else:
                    self._expected_len = type.length
            self._packet[:] = [buffer]
            self._packet_len = len(buffer)
        
    def dataReceived(self, data):
        self._packet.append(data)
        self._packet_len += len(data)

        if self.established:
            self.handleData()
        else:
            self._handleVersion()
