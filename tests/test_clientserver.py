#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C)       2008 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2006       Mekensleep
#                          24 rue vieille du temple 75004 Paris
#                          <licensing@mekensleep.com>
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
#  Bradley M. Kuhn <bkuhn@ebb.org>
#

import sys
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from log_history import log_history

from zope.interface import implements

from twisted.trial import unittest, runner, reporter
from twisted.internet import protocol, reactor, defer
from twisted.application import service
from pokernetwork.pokerservice import IPokerFactory

from pokernetwork.protocol import protocol_handshake

#
# Must be done before importing pokerclient or pokerclient
# will have to be patched too.
#

import twisted.internet.base

twisted.internet.base.DelayedCall.debug = False

import pokernetwork.server
import pokernetwork.client

from pokerpackets.packets import *

from pokerpackets import binarypack

from mock_transport import PairedDeferredTransport

class FakeService(service.Service):
    def __init__(self):
        self._keepalive_delay = 0.1

class FakeAvatar:
    def __init__(self):
        pass

    def setProtocol(self, protocol):
        self.protocol = protocol

    def handlePacket(self, packet):
        if packet.type == PACKET_ERROR:
            raise Exception("EXCEPTION TEST")
        return []

class  FakeUser:
    def __init__(self):
        self.name = "Mr.Fakey"
        self.serial = -1

class FakeFactory(protocol.ServerFactory):
    implements(IPokerFactory)
    
    def __init__(self, testObject = None):
        self.tester = testObject
        self.service = FakeService()
        self.verbose = 7
        self.destroyedAvatars = []

    def createAvatar(self):
        return FakeAvatar()

    def destroyAvatar(self, avatar):
        self.destroyedAvatars.append(avatar)
    
    def buildProtocol(self, addr):
        class Transport:
            def __init__(self):
                self.loseConnectionCount = 0

            def loseConnection(self):
                self.loseConnectionCount += 1

            def setTcpKeepAlive(self, val):
                pass
        self.instance = pokernetwork.server.PokerServerProtocol()

        # Asserts that assure PokerServerProtocol.__init__() acts as
        # expected
        self.tester.assertEquals(self.instance._keepalive_timer, None)
        self.tester.assertEquals(self.instance._keepalive_delay, 10)
        self.tester.assertEquals(self.instance.avatar, None)
        self.tester.assertEquals(self.instance._out_buffer, [])

        # Set up variables and mock ups for tests 
        self.instance.transport = Transport()
        self.instance.verbose = 7
        self.instance.exception = None
        self.instance.factory = self
        self.instance.user = FakeUser()
        return self.instance

class ClientServerTestBase(unittest.TestCase):
    def setUpConnection(self, serial):
        server_protocol = self.server_protocol[serial] = self.server_factory.buildProtocol(('127.0.0.1',0))
        client_protocol = self.client_protocol[serial] = self.client_factory[serial].buildProtocol(('127.0.0.1',0))
        server_transport = PairedDeferredTransport(protocol=server_protocol, foreignProtocol=client_protocol)
        client_transport = PairedDeferredTransport(protocol=client_protocol, foreignProtocol=server_protocol)
        server_protocol.makeConnection(server_transport)
        client_protocol.makeConnection(client_transport)
    
    def setUpServer(self):
        self.server_factory = FakeFactory(self)

    def setUpClient(self, index):
        self.client_factory[index] = pokernetwork.client.UGAMEClientFactory()
        self.client_factory[index].verbose = 7
        def setUpProtocol(client):
            client._poll_frequency = 0.1
            return client
        d = self.client_factory[index].established_deferred
        d.addCallback(setUpProtocol)
        return d

    def setUp(self):
        self.setUpServer()
        self.client_factory = [None, None]
        self.client_protocol = [None, None]
        self.server_protocol = [None, None]
        self.setUpClient(0)
        self.setUpConnection(0)

    def cleanSessions(self, arg):
        #
        # twisted Session code has leftovers : disable the hanging delayed call warnings
        # of trial by nuking all what's left.
        #
        pending = reactor.getDelayedCalls()
        if pending:
            for p in pending:
                if p.active():
#                    print "still pending:" + str(p)
                    p.cancel()
        return arg
    # -----------------------------------------------------------------------        
    def tearDown(self):
        return self.cleanSessions(None)

class ClientServer(ClientServerTestBase):
    # -----------------------------------------------------------------------        
    def quit(self, args):
        client = args[0]
        client.sendPacket(PacketQuit())
        client.transport.loseConnection()
        def serverPingTimeout(val):
            self.assertTrue(log_history.search("sendPacket: PacketQuit(7)"))
        client.connection_lost_deferred.addCallback(serverPingTimeout)
        return client.connection_lost_deferred
    # -----------------------------------------------------------------------        
    def ping(self, client):
        log_history.reset()
        client.sendPacket(PacketPing())
        self.assertEquals(log_history.get_all(), ["sendPacket: PacketPing(5)"])
        return (client,)
    # -----------------------------------------------------------------------        
    def setPrefix(self, client):
        client._prefix = "ATesterPrefix: "
        return client
    # -----------------------------------------------------------------------        
    def test01_ping(self):
        d = self.client_factory[0].established_deferred
        d.addCallback(self.ping)
        d.addCallback(self.quit)
        return d

    def exception(self, client):
        client.sendPacket(PacketError())
        d = client.connection_lost_deferred
        def validate(result, count):
            server_protocol = self.server_factory.instance
            if server_protocol.exception:
                self.assertEquals("EXCEPTION TEST", str(server_protocol.exception[1]))
            else:
                if count == 0: self.fail("exception was not received")
                else: reactor.callLater(1, lambda: validate(result, count -1))

        d.addCallback(lambda result: validate(result, 5))
        return d
        
    def test02_exception(self):
        d = self.client_factory[0].established_deferred
        d.addCallback(self.exception)
        return d

    # -----------------------------------------------------------------------
    def killThenPing(self, client):
        def sendLostConnectionPacket(val):
            client.sendPacket(PacketPing())
            # self.assertTrue(log_history.search("bufferized"))
            self.assertEqual(len(client._out_buffer), 1)
            self.assertEqual(client._out_buffer[0].type, PACKET_PING)
        d = client.connection_lost_deferred
        d.addCallback(sendLostConnectionPacket)
        client.transport.loseConnection()
        return d

    def test03_killThenPing(self):
        "Designed to cover client.py when it tests for established"
        d = self.client_factory[0].established_deferred
        d.addCallback(self.killThenPing)
        return d

    # -----------------------------------------------------------------------
    def deadServerTransport(self, client):
        server = self.server_factory.instance
        saveMyTransport = server.transport
        server.transport = None

        server.sendPackets([PacketPing()])
        self.assertEquals(len(server._out_buffer), 1)
        self.assertEquals(server._out_buffer[0].type, PACKET_PING)
        # self.assertTrue(log_history.search("bufferized"))
        # self.assertTrue(log_history.search("no usuable transport"))
        server.transport = saveMyTransport

    def test04_deadServerTransport(self):
        """Covers the case where there is no transport available and the
        packets must be buffered by the server."""
        d = self.client_factory[0].established_deferred
        d.addCallback(self.deadServerTransport)
        return d
    # -----------------------------------------------------------------------
    def clientConnectionLost(self, client):
        class ReasonMockUp:
            def __str__(self):
                return "you mock me"
            def check(self, foo):
                return False
        log_history.reset()
        client.transport.loseConnection()
        client.connectionLost(ReasonMockUp())
        self.assertEquals(client._keepalive_timer, None)
        self.assertEquals(self.client_factory[0].protocol_instance,  None)
        return True

    def test05_clientConnectionLost(self):
        """Covers the case where the client connection is lost"""
        d = self.client_factory[0].established_deferred
        d.addCallback(self.clientConnectionLost)
        return d
    # -----------------------------------------------------------------------
    def dummyClientError(self, client):
        log_history.reset()
        client.log.error("stupid dummy error test since client never calls")
        self.assertEquals(log_history.get_all(), ["stupid dummy error test since client never calls"])
        return (client,)
    # -----------------------------------------------------------------------
    def test06_dummyClientError(self):
        """At the time of writing, client.error() is not used internally
        to client, so this is a call to test its use"""
        d = self.client_factory[0].established_deferred
        d.addCallback(self.dummyClientError)
        d.addCallback(lambda (client,): client.transport.loseConnection())
        return d
    # -----------------------------------------------------------------------
    def test07_bufferizedClientPackets(self):
        d = self.client_factory[0].established_deferred
        def bufferPackets(client):
            def checkOutput(client):
                assert client._out_buffer == [PacketAck()]
                return (client,)

            client._out_buffer = [ PacketAck() ]
            log_history.reset()
            ccd = client.connection_lost_deferred
            ccd.addCallback(checkOutput)
            client.transport.loseConnection()
            return ccd

        d.addCallback(bufferPackets)
        return d

#    def test09_badClientProtocol(self):
#        pass
#-------------------------------------------------------------------------------
class ClientServerBadClientProtocol(ClientServerTestBase):
    def setUpServer(self):
        class BadVersionFakeFactory(FakeFactory):
            def buildProtocol(self, addr):
                proto = FakeFactory.buildProtocol(self, addr)
                def badSendVersion():
                    proto.transport.write('CGI 000.000\n')
                proto._sendVersion = badSendVersion
                return proto

        self.server_factory = BadVersionFakeFactory(self)
    # -----------------------------------------------------------------------
    def test01_badClientProtocol(self):
        d = self.client_factory[0].established_deferred
        def findError(myFailure):
            msg = myFailure.getErrorMessage()

            assert "%s, 'CGI 000.000\\n')" % (repr(protocol_handshake),) in msg
            assert "(<pokernetwork.client.UGAMEClientProtocol instance at" in msg
        d.addErrback(findError)
        return d
#-------------------------------------------------------------------------------
class ClientServerQueuedServerPackets(ClientServerTestBase):
    def setUpServer(self):
        class BufferedFakeFactory(FakeFactory):
            def buildProtocol(self, addr):
                proto = FakeFactory.buildProtocol(self, addr)
                proto._out_buffer.append(PacketAck())
                return proto

        self.server_factory = BufferedFakeFactory(self)
    # -----------------------------------------------------------------------
    def getServerPacket(self, client):
        # self.failUnless(log_history.search('protocol established'))
        log_history.reset()
        def findBufferedAckPacket(client):
            self.failUnless(log_history.search("PacketAck(4)"))

        d = client.connection_lost_deferred
        d.addCallback(findBufferedAckPacket)
        client.transport.loseConnection()
        return d
    # -----------------------------------------------------------------------
    def test01_getServerPacket(self):
        d = self.client_factory[0].established_deferred
        d.addCallback(self.getServerPacket)
        return d

# DummyClientTests are to cover code on the server that doesn't need a
# client running to test it.

class DummyClientTests(unittest.TestCase):

    def test05_getSerial(self):
        class  MockUser:
            def __init__(userSelf):
                userSelf.serial = 5
        client = pokernetwork.client.UGAMEClientProtocol()
        client.user = MockUser()
        self.assertEquals(client.getSerial(), 5)
    # -----------------------------------------------------------------------
    def test06_getName(self):
        class  MockUser:
            def __init__(userSelf):
                userSelf.name = "joe"
        client = pokernetwork.client.UGAMEClientProtocol()
        client.user = MockUser()
        self.assertEquals(client.getName(), "joe")
    # -----------------------------------------------------------------------
    def test07_getURL(self):
        class  MockUser:
            def __init__(userSelf):
                userSelf.url = "http://example.org"
        client = pokernetwork.client.UGAMEClientProtocol()
        client.user = MockUser()
        self.assertEquals(client.getUrl(), "http://example.org")
    # -----------------------------------------------------------------------
    def test08_getOutfit(self):
        class  MockUser:
            def __init__(userSelf):
                userSelf.outfit = "naked"
        client = pokernetwork.client.UGAMEClientProtocol()
        client.user = MockUser()
        self.assertEquals(client.getOutfit(), "naked")
    # -----------------------------------------------------------------------
    def test09_isLogged(self):
        class  MockUser:
            def isLogged(userself): return True
        client = pokernetwork.client.UGAMEClientProtocol()
        client.user = MockUser()
        self.assertEquals(client.isLogged(), True)
    # -----------------------------------------------------------------------
    def test10_factoryError(self):
        log_history.reset()
        clientFactory = pokernetwork.client.UGAMEClientFactory()
        clientFactory.log.error("test10")
        self.assertEquals(log_history.get_all(), [ "test10"])
# -----------------------------------------------------------------------------------------------------

def GetTestSuite():
    loader = runner.TestLoader()
    # loader.methodPrefix = "_test"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(ClientServer))
    suite.addTest(loader.loadClass(ClientServerBadClientProtocol))
    suite.addTest(loader.loadClass(ClientServerQueuedServerPackets))
    suite.addTest(loader.loadClass(ClientServerDeferredServerPackets))
    suite.addTest(loader.loadClass(DummyServerTests))
    suite.addTest(loader.loadClass(DummyClientTests))
    return suite

def Run():
    return runner.TrialRunner(
        reporter.TextReporter,
        tracebackFormat='default',
    ).run(GetTestSuite())

# -----------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
