#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C)       2008 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2006       Mekensleep <licensing@mekensleep.com>
#                          24 rue vieille du temple 75004 Paris
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
#  J.Jeannin <griim.work@gmail.com>
#  Bradley M. Kuhn <bkuhn@ebb.org>

import sys, os
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from log_history import log_history

from pokernetwork import protocol
from pokernetwork import protocol_number
from pokernetwork.version import Version

from twisted.trial import unittest, runner, reporter
from twisted.internet import reactor, defer

from time import time

protocol_version = Version(protocol_number)

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
    def __init__(self, time, id = None):
        self.time__ = time
        self.nodelay__ = None
        self.arg = time
        self.id = id

#-----------------

class QueueTestCase(unittest.TestCase):
    """Test case for class Queue"""

    def testQueueInit(self):
        """Testing class Queue init"""
        
        queue = protocol.Queue()
        self.assertTrue(queue.delay == 0 , "invalid delay (0 expected)")
        self.assertTrue(len(queue.packets) == 0 , "list packets not empty")

class UGAMEProtocolTestCase(unittest.TestCase):
    """Test case for class UGAMEProtocol"""

    def setUp(self):
        self.u = protocol.UGAMEProtocol()
        self.u.transport = FakeTransport()
        self.u.factory = FakeFactory(int(os.environ.get('VERBOSE_T', 6)))

    def fakeProcessQueuesDeferred(self, count = 1):
        global calledProcessQueuesCount
        calledProcessQueuesCount = 0
        self.soughtCount= count
        def mockProcessQueues():
            global calledProcessQueuesCount
            calledProcessQueuesCount += 1

        self.u._processQueues = mockProcessQueues

        def doneOk(mySelf):
            global calledProcessQueuesCount
            self.assertEquals(calledProcessQueuesCount, mySelf.soughtCount)
        d = defer.Deferred()
        d.addCallback(doneOk)
        # Note, if test fails, you'll get a reactor error.
        reactor.callLater(1, lambda: d.callback(self))

        return d


    def testUGAMEProtocolInit(self):
        """Testing class UGAMEProtocol init"""
        
        self.assertTrue(len(self.u._packet) == 0 , "list _packet not empty")
        self.assertTrue(self.u._packet_len  == 0 , "invalid _packet_len (0 expected)")
        self.assertTrue(self.u._timer == None , "invalid _timer (None expected)")
        self.assertTrue(self.u._packet2id(1) == 0 , "function _packet2id invalid")
        self.assertTrue(self.u._packet2front(2) == False , "function _packet2front invalid")
        self.assertTrue(len(self.u._queues) == 0 , "dictionnary _queues not empty")
        self.assertTrue(self.u._lagmax == 0 , "invalid _lagmax (0 expected)")
        self.assertTrue(self.u._lag == 0 , "invalid _lag (0 expected)")
        self.assertTrue(self.u._prefix == "" , "invalid _prefix")
        self.assertTrue(self.u._blocked == False , "invalid _blocked (False expected)")
        self.assertTrue(self.u.established == 0 , "invalid ugp.established (0 expected)")
        self.assertTrue(self.u._protocol_ok == False , "invalid _protocol_ok (False expected)")
        self.assertTrue(self.u._poll == True , "invalid _poll (True expected)")
        self.assertTrue(self.u._poll_frequency == 0.01 , "invalid _poll_frequency (0.01 expected)")
        self.assertTrue(self.u._ping_delay == 5 , "invalid _ping_delay")

    def testSetPingDelay(self):
        """Testing setPingDelay""" 

        self.u.setPingDelay(10)
        self.assertTrue(self.u._ping_delay == 10 , "_ping_delay is not set correctly")

    def testGetPingDelay(self):
        """Testing getPingDelay""" 

        self.u.setPingDelay(8)
        self.assertTrue(self.u.getPingDelay() == 8 , "return value is not the one expected")

    def testGetLag(self):
        """Testing getLag"""
        self.assertTrue(self.u.getLag() == 0 , "return value is not the one expected")

    def testGetOrCreateQueue(self):
        """Testing getOrCreateQueue"""
        
        self.assertTrue(self.u._queues.has_key(0) == False , "queues already containing Key '0'")
        q1 = self.u.getOrCreateQueue(0)
        self.assertTrue(self.u._queues.has_key(0) == True , "getOrCreateQueue does not have created queues")
        q2 = self.u.getOrCreateQueue(0)
        self.assertTrue(q1 == q2 , "getOrCreateQueue overwrite queues")

    def testConnectionMade(self):
        """Testing connectionMade"""
        global writeCallCount
        writeCallCount = 0

        def mockTestSendVersion(data):
            global writeCallCount
            self.assertEquals(data, 'CGI %s.%s\n' % (protocol.PROTOCOL_MAJOR, protocol.PROTOCOL_MINOR))
            writeCallCount += 1
        self.u.transport.write = mockTestSendVersion

        self.u.connectionMade()
        self.assertEquals(writeCallCount, 1)
 
    def testConnectionLost(self):
        """Testing ConnectionLost"""
        log_history.reset()
        self.u.established = 1
        self.u.connectionLost("testing")
            
        self.assertEquals(self.u.established,0)

    def testConnectionLostWithProtocolOk(self):
        """Testing ConnectionLostWithProtocolOk"""
        log_history.reset()
        self.u.established = 1
        self.u._protocol_ok = True
        self.u.connectionLost("another")
            
        self.assertEquals(self.u.established,0)
    
    def testHandleConnection(self):
        """Testing _handleConnection""" 
        log_history.reset()
        # there is just a pass here in the implementation, there is really
        # nothing to be done to truly test it.
        self.assertEquals(self.u._handleConnection("..."), None)
        self.assertEquals(log_history.get_all(), [])

    def testIgnoreIncomingData(self):
        """Testing ignoreIncomingData"""
        
        self.u.ignoreIncomingData() 
        self.u._timer = FakeTimer()
        self.u.ignoreIncomingData()
        self.assertTrue(self.u._timer._active == False)

    def testHandleVersion(self):
        """Testing handleVersion"""
        self.assertTrue(self.u._protocol_ok == False , "_protocol_ok : False expected")
        # Messages should be empty, protocol is not established
        log_history.reset()
        self.u._handleVersion()
        self.assertEquals(log_history.get_all(), [])
        
        self.assertTrue(self.u._protocol_ok == False ,"_protocol_ok change unexpected")
        
        self.u._packet = list('\n')
        # Messages should be empty, protocol is not established
        log_history.reset()
        self.u._handleVersion()
        self.assertEquals(log_history.get_all(), [])
        self.assertTrue(self.u.transport._loseConnection == True , "loseConnection not called")
        self.u.transport = FakeTransport() # transport re-init
        self.u._packet = list('CGI a.b\n')
        # Messages should be empty, protocol is not established
        log_history.reset()
        self.u._handleVersion()
        self.assertEquals(log_history.get_all(), [])
        self.assertTrue(self.u.transport._loseConnection == True , "loseConnection not called")
        self.u.transport = FakeTransport() # transport re-init
        vers = Version(protocol_number)
        PROTOCOL_MAJOR = "%03d" % vers.major()
        PROTOCOL_MINOR = "%d%02d" % ( vers.medium(), vers.minor() )
        self.u._packet = list( 'CGI %s.%s \n' % (PROTOCOL_MAJOR, PROTOCOL_MINOR ))
        log_history.reset()
        self.u._handleVersion()
        self.assertEquals(log_history.get_all(), ["protocol established"])
        self.assertTrue(self.u._protocol_ok == True , "_protocol_ok value unexpected")

    def testProtocolEstablished(self):
        pass

    def testProtocolInvalid(self):
        pass
    
    def testHold(self):
        """Testing hold"""

        self.u.hold(-2,0)
        self.assertTrue(self.u._queues.has_key(0) == True , "queue has not been created")
        self.assertTrue(self.u._queues[0].delay == -2 , "delay wrongly set")

        self.u.hold(-4)
        self.assertTrue(self.u._queues[0]. delay == -4 , "delay wrongly set")

        self.u.hold(1)
        self.assertTrue(self.u._queues[0].delay > 0 , "delay wrongly set")

    def testBlock(self):
        """Testing block"""

        self.u._blocked = False
        self.u.block()
        self.assertTrue(self.u._blocked == True , "block don't block...")

    def testUnblock(self):
        """Testing unblock"""

        self.u._blocked = True
        self.u.unblock()
        self.assertTrue(self.u._blocked == False , "unblock don't unblock...")
 
    def testDiscardPackets(self):
        """Testing discardPackets"""
        
        self.u._queues[0] = protocol.Queue()
        self.u.discardPackets(0)
        self.assertTrue(not hasattr(self.u , '_queues[0]') , "queue not deleted")
 
    def testCanHandlePacket(self):
        """Testing canHandlePackets"""

        self.assertTrue(self.u.canHandlePacket('') == (True,0))
    
    def testProcessQueues(self):
        """Testing _proccessQueues"""
        global triggerTimerCallCount
        triggerTimerCallCount = 0
        def mockTriggerTimer():
            global triggerTimerCallCount
            triggerTimerCallCount += 1
            
        self.u.triggerTimer = mockTriggerTimer
        self.u.canHandlePacket = lambda x : (False, time()+10)
        self.failIf(self.u._queues.has_key(0))
        self.u.getOrCreateQueue(0)
        self.failUnless(self.u._queues.has_key(0))

        self.u._lagmax = 10

        self.failIf(self.u._queues.has_key(1))
        self.u.getOrCreateQueue(1)
        self.failUnless(self.u._queues.has_key(1))
        self.u._queues[1].delay = time()+10
        oneArg = 0
        self.u._queues[1].packets.insert( 0, FakePacket(oneArg, "one") )
        self.u._queues[1].packets[0].nodelay__ = True

        self.failIf(self.u._queues.has_key(2))
        self.u.getOrCreateQueue(2)
        self.failUnless(self.u._queues.has_key(2))
        self.u._queues[2].delay = time()
        twoArg = time()
        self.u._queues[2].packets.insert( 0, FakePacket(twoArg, "two") )

        self.failIf(self.u._queues.has_key(3))
        self.u.getOrCreateQueue(3)
        self.failUnless(self.u._queues.has_key(3))
        self.u._queues[3].delay = time()+1
        threeArg = time() +10
        self.u._queues[3].packets.insert( 0, FakePacket(threeArg, "three") )

        # Ok, Test blocked first -- nothing happens
        log_history.reset()
        self.u._blocked = True
        self.u._processQueues()
        k = self.u._queues.keys()
        self.assertEquals(triggerTimerCallCount, 1)

        k.sort()
        self.assertEquals(k, [ 0, 1, 2, 3 ])
        self.assertEquals(log_history.get_all(), [])
        self.assertEquals(self.u._lag, 0)

        # Unblocked test, function fully runs
        triggerTimerCallCount = 0
        self.u._blocked = False

        global callCount
        callCount = 0
        def mockHandler(packet):
            global callCount
            callCount += 1
            self.assertEquals(packet.arg, oneArg)
            self.assertEquals(packet.id, 'one')
                
        self.u._handler = mockHandler

        startTime = time()
        self.u._processQueues()
        endTime = time()

        self.assertEquals(callCount, 1)
        self.failUnless(self.u._lag >= startTime)
        self.failUnless(self.u._lag <= endTime)

        k = self.u._queues.keys()
        k.sort()
        self.assertEquals(k, [ 1, 2, 3 ])

        self.assertEquals(len(self.u._queues[1].packets), 0)
        self.assertEquals(len(self.u._queues[2].packets), 1)
        self.assertEquals(len(self.u._queues[3].packets), 1)
        self.assertEquals(triggerTimerCallCount, 1)

        self.assertEquals(len(log_history.get_all()), 2)
        self.assertEquals(log_history.get_all()[0], ' => queue 1 delay canceled because lag too high')
        self.assertEquals(log_history.get_all()[1].find('seconds before handling the next packet in queue 3') > 0, True)

    def triggerTimer_expectNoCallLater(self, doneOk):
        def mockProcessQueue(): self.fail()
        self.u._processQueues = mockProcessQueue
        self._poll_frequency = 0.1
        self.u.triggerTimer()

        d = defer.Deferred()
        d.addCallback(doneOk)
        reactor.callLater(1, lambda: d.callback(self))
        return d

    def testTriggerTimer_alreadyHaveActiveTimer(self):
        """Testing triggerTimer when it already has an active timer
        """
        self.assertEquals(self.u._timer, None)
        class MockTimer:
            def __init__(self): self.myID = "MOCK"
            def active(self): return True

        self.u._timer = MockTimer()

        def doneOk(mySelf):
            mySelf.assertEquals(mySelf.u._timer.myID, "MOCK")

        # Note that _poll is removed because it should never actually be
        # read and if it is, we know something has gone wrong with test.
        del self.u.__dict__['_poll']

        return self.triggerTimer_expectNoCallLater(doneOk)

    def testTriggerTimer_inactiveTimerNoPoll(self):
        """Testing triggerTimer when timer exists, is inactive, but not polling
        """
        self.assertEquals(self.u._timer, None)
        class MockTimer:
            def __init__(self): self.myID = "MOCK2"
            def active(self): return False

        self.u._timer = MockTimer()

        def doneOk(mySelf):
            mySelf.assertEquals(mySelf.u._timer.myID, "MOCK2")

        self.u._poll = False

        return self.triggerTimer_expectNoCallLater(doneOk)

    def testTriggerTimer_noTimerPollingEmptyQueues(self):
        """Testing triggerTimer without timer, polling on, empty queue
        """
        self.assertEquals(self.u._timer, None)

        def doneOk(mySelf):
            mySelf.assertEquals(mySelf.u._timer, None)

        self.u._poll = True

        return self.triggerTimer_expectNoCallLater(doneOk)

    def testTriggerTimer_reactorIsCalled(self):
        """Testing triggerTimer when reactor is called
        """
        self.assertEquals(self.u._timer, None)
        self.u._poll = True
        self.u.getOrCreateQueue(0)

        global processQueueCalled
        processQueueCalled = 0
        def mockProcessQueue():
            global processQueueCalled
            processQueueCalled += 1
            
        self.u._processQueues = mockProcessQueue

        def doneOk(mySelf):
            global processQueueCalled
            self.assertEquals(processQueueCalled, 1)

        d = defer.Deferred()
        d.addCallback(doneOk)
        # Note, if test fails, you'll get a reactor error.
        reactor.callLater(1, lambda: d.callback(self))

        self.u.triggerTimer()

        return d

    def testPushPacket(self):
        """Testing pushPacket"""
        global triggerTimerCallCount
        triggerTimerCallCount = 0
        def mockTriggerTimer():
            global triggerTimerCallCount
            triggerTimerCallCount += 1
            
        self.u.triggerTimer = mockTriggerTimer
       
        self.u._packet2front = lambda x: x <= 0
        self.u.pushPacket(FakePacket(1)) 
        self.u.pushPacket(FakePacket(0)) 
        
        self.assertTrue(len(self.u._queues[0].packets) == 2 , "packets not in list")
        self.assertTrue(self.u._queues[0].packets[0].arg < self.u._queues[0].packets[1].arg , "packet not set in front of the queue")
        self.assertEquals(triggerTimerCallCount, 2)

    def testHandleData(self):
        """Testing handleData"""
        fakeProcessQueuesDeferred = self.fakeProcessQueuesDeferred()

        self.u._expected_len = 3
        self.u._packet.append("\x00\x00\x03")
        self.u._packet_len = len("\x00\x00\x03")
        log_history.reset()
        self.u.handleData() 
        self.assertEquals(log_history.get_all(), ['(3 bytes) => type = NONE(0)'])

        self.u._poll = False
        self.u._packet.append("\x00\x00\x03")
        self.u._packet_len = len("\x00\x00\x03")
        log_history.reset()
        self.u.handleData()
        self.assertEquals(log_history.get_all(), ['(3 bytes) => type = NONE(0)'])

        self.u._packet.append("\xff\x00\x03")
        self.u._packet_len = len("\xff\x00\x03")
        log_history.reset()
        self.u.handleData()
        self.assertEquals(log_history.get_all(), [': unknown message received (id 255, length 3)\n'])
        # trying with wrong packet
        self.u._packet.append("\xff\x00\x00")
        self.u._packet_len = len("\xff\x00\x00")
        log_history.reset()
        self.u.handleData()
        # FIXME (maybe): I am not completely sure it's correct that we
        # should get absolutely no output when we send the "wrong packet".
        # I've asked Loic to take a look.
        self.assertEquals(log_history.get_all(), [])
        return fakeProcessQueuesDeferred
        
    def testDataReceived(self):
        """Testing dataReceived"""
        global handledVersion
        global handledData
        handledData = handledVersion = 0

        def mockHandleVersion():
            global handledVersion
            handledVersion += 1

        def mockHandleData():
            global handledData
            handledData += 1

        self.u._handleVersion = mockHandleVersion
        self.u.handleData = mockHandleData

        self.assertEquals(self.u._packet, [])
        self.assertEquals(self.u._packet_len, 0)

        self.u.dataReceived("packet_1")

        self.assertEquals(self.u._packet, ['packet_1'])
        self.assertEquals(self.u._packet_len, 8)
        self.failIf(handledData > 0)
        self.failUnless(handledVersion == 1)
        self.assertEquals(self.u.established, 0)

        handledVersion = 0
        self.u.established = 1
        self.u.dataReceived("packet_2_long")
        self.assertEquals(self.u._packet, ['packet_1', 'packet_2_long'])
        self.assertEquals(self.u._packet_len, 21)
        self.failIf(handledVersion > 0)
        self.failUnless(handledData == 1)
        
    def testCoverDataWrite(self):
        """Testing data write"""
        log_history.reset()
        tot = protocol.UGAMEProtocol._stats_write

        global calledWrite
        calledWrite = 0
        myData = "testing data"
        def mockTransportWrite(data):
            global calledWrite
            self.assertEquals(data, myData)
            calledWrite += 1
        self.u.transport.write = mockTransportWrite

        self.u.dataWrite(myData)

        self.assertEquals(tot + len(myData), protocol.UGAMEProtocol._stats_write)

        self.assertEquals(calledWrite, 1)
        self.assertEquals(log_history.get_all(), [])

#------------------------------------------------------------------------

def GetTestSuite():
    loader = runner.TestLoader()
    # Comment in line below this when you wish to run just one test by
    # itself (changing prefix as needed).
#    loader.methodPrefix = "testProcess"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(QueueTestCase))
    suite.addTest(loader.loadClass(UGAMEProtocolTestCase))
    return suite

def Run():
    return runner.TrialRunner(
        reporter.TextReporter,
        tracebackFormat='default',
    ).run(GetTestSuite())
# ----------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
