#!/usr/bin/python2.4
# -*- mode: python -*-
#
# Copyright (C) 2006 Mekensleep
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
#  J.Jeannin <griim.work@gmail.com>
#

import sys, os
sys.path.insert(0, "..")

from pokernetwork import protocol
from pokernetwork import protocol_number
from pokernetwork.version import Version

from time import time

protocol_version = Version(protocol_number)

import unittest

#-----------------

class FakeFactory:
    """Factory for testing purpose"""
    def __init__(self, verbose):
        self.verbose = verbose

class FakeTransport:
    """Transport for testing purpose"""
    def __init__(self):
        self._loseConnection = False

    def write(self, data = ''):
        return True

    def loseConnection(self):
        self._loseConnection = True
        
class FakeTimer:
    """Timer for testing purpose"""
    def __init__(self):
        self._active = True

    def active(self):
        return self._active

    def cancel(self):
        self._active = False

class FakePacket:
    """Packet for testing purpose"""
    def __init__(self, time):
        self.time__ = time
        self.nodelay__ = None
        self.arg = time

#-----------------

class QueueTestCase(unittest.TestCase):
    """Test case for class Queue"""

    def testQueueInit(self):
        """Testing class Queue init"""
        
        queue = protocol.Queue()
        assert queue.delay == 0 , "invalid delay (0 expected)"
        assert len(queue.packets) == 0 , "list packets not empty"

class UGAMEProtocolTestCase(unittest.TestCase):
    """Test case for class UGAMEProtocol"""

    def setUp(self):
        self.u = protocol.UGAMEProtocol()
        self.u.transport = FakeTransport()
        self.u.factory = FakeFactory(6)

    def testUGAMEProtocolInit(self):
        """Testing class UGAMEProtocol init"""
        
        assert len(self.u._packet) == 0       , "list _packet not empty"
        assert self.u._packet_len  == 0       , "invalid _packet_len  (0 expected)"
        assert self.u._timer == None          , "invalid _timer (None expected)"
        assert self.u._packet2id(1) == 0      , "function _packet2id invalid"
        assert self.u._packet2front(2) == False , "function _packet2front invalid"
        assert len(self.u._queues) == 0       , "dictionnary _queues not empty"
        assert self.u._lagmax == 0            , "invalid _lagmax (0 expected)"
        assert self.u._lag == 0               , "invalid _lag (0 expected)"
        assert self.u._prefix == ""           , "invalid _prefix"
        assert self.u._blocked == False       , "invalid _blocked (False expected)"
        assert self.u.established == 0        , "invalid ugp.established (0 expected)"
        assert self.u._protocol_ok == False   , "invalid _protocol_ok (False expected)"
        assert self.u._poll == True                      , "invalid _poll (True expected)"
        assert self.u._poll_frequency == 0.01    , "invalid _poll_frequency (0.01 expected)"
        assert self.u._ping_delay == 5        , "invalid _ping_delay"

    def testSetPingDelay(self):
        """Testing setPingDelay"""        

        self.u.setPingDelay(10)
        assert self.u._ping_delay == 10       , "_ping_delay is not set correctly"

    def testGetPingDelay(self):
        """Testing getPingDelay"""        

        self.u.setPingDelay(8)
        assert self.u.getPingDelay() == 8     , "return value is not the one expected"

    def testGetLag(self):
        """Testing getLag"""

        assert self.u.getLag() == 0             , "return value is not the one expected"

    def testGetOrCreateQueue(self):
        """Testing getOrCreateQueue"""
        
        assert self.u._queues.has_key(0) == False , "queues already containing Key '0'"
        q1 = self.u.getOrCreateQueue(0)
        assert self.u._queues.has_key(0) == True  , "getOrCreateQueue does not have created queues"
        q2 = self.u.getOrCreateQueue(0)

        assert q1 == q2                           , "getOrCreateQueue overwrite queues"

    # assert ?
    def testConnectionMade(self):
        """Testing connectionMade"""
    
        self.u.connectionMade()
 
    def testConnectionLost(self):
        """Testing ConnectionLost"""

        self.u.established = 1
        self.u.connectionLost("testing")
            
        assert self.u.established == 0             , "connectionLost error"
    
    # assert ?
    def testSendVersion(self):
        """Testing sendVersion"""
        
        self.u._sendVersion()
            
    # assert ?
    def testHandleConnection(self):
        """"Testing _handleConnection"""        

        self.u._handleConnection("...")

    def testIgnoreIncomingData(self):
        """Testing ignoreIncomingData"""
        
        self.u.ignoreIncomingData()           
        self.u._timer = FakeTimer()
        self.u.ignoreIncomingData()
        assert self.u._timer._active == False

    def testHandleVersion(self):
        """Testing handleVersion"""

        assert self.u._protocol_ok == False        , "_protocol_ok : False expected"
        self.u._handleVersion()
        assert self.u._protocol_ok == False        ,"_protocol_ok change unexpected"
        
        self.u._packet = list('\n')
        self.u._handleVersion()
        assert self.u.transport._loseConnection == True , "loseConnection not called"

        self.u.transport = FakeTransport()      # transport re-init
        self.u._packet = list('CGI a.b\n')
        self.u._handleVersion()
        assert self.u.transport._loseConnection == True , "loseConnection not called"

        self.u.transport = FakeTransport()      # transport re-init
        vers = Version(protocol_number)
        PROTOCOL_MAJOR = "%03d" % vers.major()
        PROTOCOL_MINOR = "%d%02d" % ( vers.medium(), vers.minor() )
        self.u._packet = list( 'CGI %s.%s\n' % (PROTOCOL_MAJOR, PROTOCOL_MINOR ))
        self.u._handleVersion()
        assert self.u._protocol_ok == True ,  "_protocol_ok value unexpected"

    def testProtocolEstablished(self):
        pass

    def testProtocolInvalid(self):
        pass
    
    def testHold(self):
        """Testing hold"""

        self.u.hold(-2,0)
        assert self.u._queues.has_key(0) == True  , "queue has not been created"
        assert self.u._queues[0].delay == -2  , "delay wrongly set"

        self.u.hold(-4)
        assert self.u._queues[0]. delay == -4 , "delay wrongly  set"

        self.u.hold(1)
        assert self.u._queues[0].delay > 0 , "delay wrongly set"

    def testBlock(self):
        """Testing block"""

        self.u._blocked = False
        self.u.block()
        assert self.u._blocked == True   ,   "block don't block..."

    def testUnblock(self):
        """Testing unblock"""

        self.u._blocked = True
        self.u.unblock()
        assert self.u._blocked == False  ,   "unblock don't unblock..."
 
    def testDiscardPackets(self):
        """Testing discardPackets"""
        
        self.u._queues[0] = protocol.Queue()
        self.u.discardPackets(0)
        assert not hasattr(self.u , '_queues[0]')  ,  "queue not deleted"
 
    def testCanHandlePacket(self):
        """Testing canHandlePackets"""

        assert self.u.canHandlePacket('') == (True,0)
    
    # assert ?
    def testProcessQueues(self):
        """Testing _proccessQueues"""
         
        self.u.canHandlePacket = lambda x : (False, time()+10)
        self.u.getOrCreateQueue(0)

        self.u._lagmax = 10

        self.u.getOrCreateQueue(1)
        self.u._queues[1].delay = time()+10
        self.u._queues[1].packets.insert( 0, FakePacket(0) )
        self.u._queues[1].packets[0].nodelay__ = True

        self.u.getOrCreateQueue(2)
        self.u._queues[2].delay = time()
        self.u._queues[2].packets.insert( 0, FakePacket(time()) )

        self.u.getOrCreateQueue(3)
        self.u._queues[3].delay = time()+1
        self.u._queues[3].packets.insert( 0, FakePacket(time()+10) )

        self.u._processQueues()

    # assert ?
    def testTriggerTimer(self):
        """Testing triggerTimer"""

        self.u.getOrCreateQueue(0)
        self.u.triggerTimer()

    def testPushPacket(self):
        """Testing pushPacket"""
       
        self.u._packet2front = lambda x:  x <= 0

        self.u.pushPacket( FakePacket(1) );        
        self.u.pushPacket( FakePacket(0) );        
        
        assert len(self.u._queues[0].packets) == 2  , "packets not in list"
        assert self.u._queues[0].packets[0].arg <  self.u._queues[0].packets[1].arg  , "packet not set in front of the queue"

    def testHandleData(self):
        """Testing handleData"""

        self.u._expected_len = 3
        self.u._packet.append("\x00\x00\x03")
        self.u._packet_len = len("\x00\x00\x03")
        self.u.handleData() 

        self.u._poll = False
        self.u._packet.append("\x00\x00\x03")
        self.u._packet_len = len("\x00\x00\x03")
        self.u.handleData()

        self.u._packet.append("\xff\x00\x03")
        self.u._packet_len = len("\xff\x00\x03")
        self.u.handleData()

        # trying with wrong packet
        self.u._packet.append("\xff\x00\x00")
        self.u._packet_len = len("\xff\x00\x00")
        self.u.handleData()
     
    # assert ?
    def testDataReceived(self):
        """Testing dataReceived"""

        self.u.dataReceived("packet_1")

        self.u.established == True
        self.u.dataReceived("packet_2")

# running test
if __name__ == '__main__':
    unittest.main()
