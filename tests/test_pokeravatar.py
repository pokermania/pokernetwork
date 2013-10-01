#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 - 2010 Loic Dachary    <loic@dachary.org>
# Copyright (C) 2008, 2009 Bradley M. Kuhn  <bkuhn@ebb.org>
# Copyright (C) 2008       Johan Euphrosine <proppy@aminche.com>
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

import sys, os
from os import path
from pokerengine.pokertournament import TOURNAMENT_STATE_RUNNING, TOURNAMENT_STATE_REGISTERING, TOURNAMENT_STATE_CANCELED

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from config import config
from log_history import log_history
import sqlmanager

import locale
import libxml2
from types import *
import socket
from twisted.trial import unittest, runner, reporter
import twisted.internet.base
from twisted.internet import reactor, defer, error, base
from twisted.python import failure, runtime
from twisted.python.runtime import seconds

from pokerengine import pokertournament
#
# Must be done before importing pokerclient or pokerclient
# will have to be patched too.
#
from tests import testclock
from mock_transport import PairedDeferredTransport
import pprint

twisted.internet.base.DelayedCall.debug = False

from pokernetwork import pokerservice
from pokernetwork import pokernetworkconfig
from pokernetwork import pokerclient
from pokernetwork import currencyclient
currencyclient.CurrencyClient = currencyclient.FakeCurrencyClient
from pokerpackets.packets import *
from pokerpackets.networkpackets import *
from pokerpackets.clientpackets import *
from pokernetwork.pokertable import PokerAvatarCollection
from pokernetwork.pokerrestclient import PokerRestClient

try:
    from nose.plugins.attrib import attr
except ImportError, e:
    def attr(fn): return fn

class ConstantDeckShuffler:
    def shuffle(self, what):
        what[:] = [
            40, 13, 32, 9, 19, 31, 15, 14, 50, 34, 20, 6, 43, 44, 28, 29, 48, 3, 21, 45,
            23, 37, 35, 11, 5, 22, 24, 30, 27, 39, 46, 33, 0, 8, 1, 42, 36, 16, 49, 2,
            10, 26, 4, 18, 7, 41, 47, 17
        ]

from pokerengine import pokergame
pokergame.shuffler = ConstantDeckShuffler()

class ConstantPlayerShuffler:
    def shuffle(self, what):
        what.sort()

pokertournament.shuffler = ConstantPlayerShuffler()
PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = -1

class PokerAvatarLocaleTestCase(unittest.TestCase):
    def test01_gettext_underscore_not_defined(self):
        from pokernetwork import pokeravatar
        service = PokerAvatarNoClientServerTestCase.MockService()
        avatar = pokeravatar.PokerAvatar(service)
        avatar.localeFunc = lambda x: x
        avatar.queuePackets()
        avatar.sendPacket(Packet())

settings_xml_server = """\
<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" simultaneous="4" chat="yes" auto_create_account="yes" >
    <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

    <language value="en_US.UTF-8"/>
    <language value="de_DE.UTF-8"/>

    <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />
    <table name="Table2" variant="holdem" betting_structure="1-2_20-200_limit" seats="10" player_timeout="60" currency_serial="1" />
    <table name="Table3" variant="holdem" betting_structure="test18pokerclient" seats="10"
        player_timeout="600" muck_timeout="600" currency_serial="1" forced_dealer_seat="0" />
    <table name="Table4" variant="holdem" betting_structure="10-20_100-2000000_ante-limit" seats="10" player_timeout="60" currency_serial="1" />
    <listen tcp="19480" />

    <resthost serial="1" host="127.0.0.1" port="19481" path="/POKER_REST" name="test" />

    <refill serial="1" amount="100" />
    <cashier acquire_timeout="5" pokerlock_queue_timeout="30" user_create="yes"/>
    <database
        host="%(dbhost)s" name="%(dbname)s"
        user="%(dbuser)s" password="%(dbuser_password)s"
        root_user="%(dbroot)s" root_password="%(dbroot_password)s"
        schema="%(tests_path)s/../database/schema.sql"
        command="%(mysql_command)s" />
    <tourney_select_info>tests.testtourney_select_info</tourney_select_info>
    <path>%(engine_path)s/conf %(tests_path)s/conf</path>
    <users temporary="BOT.*"/>
</server>
""" % {
    'dbhost': config.test.mysql.host,
    'dbname': config.test.mysql.database,
    'dbuser': config.test.mysql.user.name,
    'dbuser_password': config.test.mysql.user.password,
    'dbroot': config.test.mysql.root_user.name,
    'dbroot_password': config.test.mysql.root_user.password,
    'tests_path': TESTS_PATH,
    'engine_path': config.test.engine_path,
    'mysql_command': config.test.mysql.command
}

settings_xml_client = """\
<?xml version="1.0" encoding="UTF-8"?>
<settings display2d="yes" display3d="no" ping="15000" verbose="6" delays="true" tcptimeout="2000" upgrades="no">
   <delays blind_ante_position="0" position="0" begin_round="0" end_round="0" end_round_last="0" showdown="0" lag="60"/> 
  <screen fullscreen="no" width="1024" height="768"/>
  <name>user1</name>
  <passwd>password1</passwd>
  <remember>yes</remember>
  <muck>yes</muck>
  <auto_post>no</auto_post>
  <chat max_chars="40" line_length="20"/>
  <sound>yes</sound>
  <tournaments currency_serial="1" type="sit_n_go" sort="name"/>
  <lobby currency_serial="1" type="holdem" sort="name"/>
  <shadow>yes</shadow>
  <vprogram>yes</vprogram>
  
  <path>%(engine_path)s/conf %(tests_path)s/conf</path>
  <data path="data" sounds="data/sounds"/>
  <handlist start="0" count="10"/>
</settings>
""" % {
    'tests_path': TESTS_PATH,
    'engine_path': config.test.engine_path,
    'mysql_command': config.test.mysql.command
}

##############################################################################
class PokerAvatarTestCaseBaseClass(unittest.TestCase):
    timeout = 500

    def setupDb(self):
        sqlmanager.setup_db(

            TESTS_PATH + "/../database/schema.sql", (
                ("INSERT INTO tableconfigs (name, variant, betting_structure, seats, currency_serial) VALUES (%s, 'holdem', %s, 10, 1)", (
                    ('Table1','100-200_2000-20000_no-limit'),
                    ('Table2','1-2_20-200_limit'),
                )),
                ("INSERT INTO tableconfigs (name, variant, betting_structure, seats, currency_serial, player_timeout, muck_timeout) VALUES (%s, 'holdem', %s, 10, 1, %s, %s)", (
                    ('Table3','test18pokerclient', 600, 600), #player timeout 600, muck timeout 600
                )),
                ("INSERT INTO tableconfigs (name, variant, betting_structure, seats, currency_serial) VALUES (%s, 'holdem', %s, 10, 1)", (
                    ('Table4', '10-20_100-2000000_ante-limit'),
                )),
                ("INSERT INTO tables (resthost_serial, tableconfig_serial) VALUES (%s, %s)", (
                    (1, 1),
                    (1, 2),
                    (1, 3),
                    (1, 4),
                )),
                ('INSERT INTO tourneys_schedule (resthost_serial, name, description_short, description_long, players_quota, variant, ' \
                'betting_structure, seats_per_game, currency_serial, buy_in, rake, sit_n_go, start_time, ' \
                'register_time, respawn, respawn_interval) ' \
                'VALUES (1, "sitngo2", "Sit and Go 2 players, Holdem", "Sit and Go 2 players", "2", "holdem", "level-15-30-no-limit", ' \
                '"2", 1, "3000", "0", "y", "0", "0", "y", "60");',None),
                ('INSERT INTO tourneys_schedule (resthost_serial, name, description_short, description_long, players_quota, variant, ' \
                'betting_structure, seats_per_game, currency_serial, buy_in, rake, sit_n_go, breaks_interval, ' \
                'rebuy_delay, add_on, add_on_delay, start_time, register_time, respawn, respawn_interval, players_min) ' \
                'VALUES (1, "regular1", "Holdem No Limit Freeroll", "Holdem No Limit Freeroll", "1000", "holdem", "level-001", "10", ' \
                '1, "0", "0", "n", "60", "30", "1", "60", unix_timestamp(now() + INTERVAL 2 MINUTE), unix_timestamp(now() - ' \
                'INTERVAL 1 HOUR), "n", "60", 3);', None),
            ),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host,
            port=config.test.mysql.port,
            database=config.test.mysql.database
        )

    def setUpConnection(self, serial):
        server_protocol = self.server_protocol[serial] = self.server_factory.buildProtocol(('127.0.0.1',0))
        client_protocol = self.client_protocol[serial] = self.client_factory[serial].buildProtocol(('127.0.0.1',0))
        server_transport = PairedDeferredTransport(protocol=server_protocol, foreignProtocol=client_protocol)
        client_transport = PairedDeferredTransport(protocol=client_protocol, foreignProtocol=server_protocol)
        server_protocol.makeConnection(server_transport)
        client_protocol.makeConnection(client_transport)
    
    def setUpServer(self, serverSettings=settings_xml_server):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(serverSettings)
        #
        # Setup server
        #
        self.service = pokerservice.PokerService(settings)
        self.service.startService()
        for i in (1,2,3,4):
            self.service.spawnTable(i, **self.service.loadTableConfig(i))
        self.service.updateTourneysSchedule()
        self.server_factory = pokerservice.IPokerFactory(self.service)
    # ------------------------------------------------------
    def setUpClient(self, index):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml_client)
        self.client_factory.append(pokerclient.PokerClientFactory(settings = settings))
        self.client_protocol.append(None)
        self.server_protocol.append(None)
        self.assertEquals(
            len(self.client_factory), index + 1,
            "clients must be created in daisy-chain with createClients() or createClient()"
        )
        def setUpProtocol(client):
            client._poll_frequency = 0.1
            return client
        d = self.client_factory[index].established_deferred
        d.addCallback(setUpProtocol)
        return d
    # ------------------------------------------------------
    def setUp(self):
        testclock._seconds_reset()        

        self.avatarLocales = {}
        self.avatarLocales[0] = "default"
        self.avatarLocales[1] = "default"

        self.setupDb()
        self.setUpServer()
        self.client_factory = []
        self.client_protocol = []
        self.server_protocol = []
        
    # -------------------------------------------------------------------------
    def createClient(self):
        client_index = len(self.client_factory)
        self.setUpClient(client_index)
        self.setUpConnection(client_index)
        return client_index
    
    # -------------------------------------------------------------------------
    def createClients(self, numClients):
        if numClients <= 0:
            return

        dl = []
        for i in range(numClients):
            dl.append(self.setUpClient(i))
            self.setUpConnection(i)
    # -------------------------------------------------------------------------
    def cleanSessions(self, arg):
        #
        # twisted Session code has leftovers : disable the hanging delayed call warnings
        # of trial by nuking all what's left.
        #
        pending = reactor.getDelayedCalls()
        if pending:
            for p in pending:
                if p.active():
                    # print "still pending:" + str(p)
                    p.cancel()
        return arg
    # -------------------------------------------------------------------------
    def tearDown(self):
        d = self.service.stopService()
        d.addCallback(self.cleanSessions)
        return d
    # -------------------------------------------------------------------------
    def quit(self, args):
        client = args[0]
        client.sendPacket(PacketQuit())
        if hasattr(client, "transport"):
            client.transport.loseConnection()
            return client.connection_lost_deferred
        else:
            raise UserWarning, "quit does not have transport %d" % client.getSerial()
    # -------------------------------------------------------------------------
    def setupCallbackChain(self, client):
        return (client, None)
    # ------------------------------------------------------------------------
    def autoBlindAnte(self, (client, packet), id, gameId ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerAutoBlindAnte(
            serial= client.getSerial(),
            game_id = gameId
        ))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_AUTO_BLIND_ANTE:
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.game_id, gameId)
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # -------------------------------------------------------------------------
    def sendExplain(self, client):
        client.sendPacket(PacketPokerExplain(value = PacketPokerExplain.ALL))
        return client.packetDeferred(True, PACKET_ACK)
    # -------------------------------------------------------------------------
    def sendRolePlay(self, (client, packet)):
        client.sendPacket(PacketPokerSetRole(serial = client.getSerial(), roles = PacketPokerSetRole.PLAY))
        return client.packetDeferred(True, PACKET_POKER_ROLES)
    # -------------------------------------------------------------------------
    def login(self, (client, packet), index):
        client.sendPacket(PacketLogin(name = 'user%d' % index, password = 'password1'))
        return client.packetDeferred(True, PACKET_POKER_PLAYER_INFO)
    # -------------------------------------------------------------------------
    def joinTable(self, (client, packet), id, gameId, name, struct, statsExpected = [],
                  variant = 'holdem', max_players = 10, reason = PacketPokerTable.REASON_TABLE_JOIN):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTableJoin(serial = client.getSerial(), game_id = gameId))
        total = 2 + len(statsExpected)
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_ARRIVE:
                game = table.game
                player = game.getPlayer(avatar.getSerial())
                if player:
                    self.assertEquals(player.buy_in_payed, packet.buy_in_payed)
            if packet.type == PACKET_POKER_TABLE:
                found += 1
                self.assertEquals(packet.betting_structure, struct)
                self.assertEquals(packet.variant, variant)
                self.assertEquals(packet.reason, reason)
                for (kk, vv) in avatar.tables.items():
                    self.assertEquals(vv.game.id, table.game.id)
                    self.assertEquals(vv.game.name, name)
                    self.assertEquals(vv.game.max_players, max_players)
                    self.assertEquals(vv.game.variant, variant)
                    self.assertEquals(vv.game.betting_structure, struct)
            elif packet.type == PACKET_POKER_BUY_IN_LIMITS:
                found += 1
                for key in [ 'best', 'game_id', 'min', 'max' ]:
                    self.assert_(hasattr(packet, key))
            elif packet.type == PACKET_POKER_PLAYER_STATS:
                for ss in statsExpected:
                    if ss['serial'] == packet.serial:
                        found += 1
                        self.assertEquals(packet.rank, ss['rank'])
                        self.assertEquals(packet.percentile, ss['percentile'])
        self.assertEquals(found, total)
        return (client, packet)
    # -------------------------------------------------------------------------
    def seatTable(self, (client, packet), id, gameId, rank = None, percentile = None, seatNumber = None):
        if seatNumber == None: seatNumber = id + 1

        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSeat(
            serial = client.getSerial(),
            seat = seatNumber,
            game_id = gameId
        ))
        found = 0
        packets = avatar.resetPacketsQueue()
        for packet in packets:
            if packet.type == PACKET_POKER_SEATS:
                found += 1
                self.assertEquals(packet.game_id, table.game.id)
                if seatNumber == -1:
                    self.failUnless(client.getSerial() in packet.seats)
                else:
                    self.assertEquals(packet.seats[seatNumber], client.getSerial())
            elif packet.type == PACKET_POKER_PLAYER_ARRIVE:
                found += 1 
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.name, "user%d" % id)
                self.assertEquals(packet.serial, client.getSerial())
                if seatNumber == -1:
                    self.failUnless(packet.seat >= 0)
                else:
                    self.assertEquals(packet.seat, seatNumber)
            elif packet.type == PACKET_POKER_PLAYER_STATS:
                found += 1 
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.rank, rank)
                self.assertEquals(packet.percentile, percentile)
            elif packet.type == PACKET_POKER_PLAYER_CHIPS:
                found += 1
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.bet, 0)
                self.assertEquals(packet.money, 0)
        expected = 3
        if percentile:
            expected += 1
        self.assertEquals(found, expected, "avatarID %d was unable to SEAT in game(%d) : %s" % (id, gameId, str(packets)))
        return (client, packet)
    # -------------------------------------------------------------------------
    def buyInTable(self, (client, packet), id, gameId, myAmount):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        seatNumber = id + 1
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerBuyIn(serial = client.getSerial(), amount = myAmount, game_id = gameId))
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_CHIPS:
                found += 1
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.bet, 0)
                self.assertEquals(packet.money, myAmount)
        self.assertEquals(found, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def sitTable(self, (client, packet), id, gameId):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        seatNumber = id + 1
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSit(serial = client.getSerial(), game_id = gameId))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_SIT:
                found = True
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.serial, client.getSerial())
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def readyToPlay(self, (client, packet), id, gameId ):
        avatars = self.service.avatar_collection.get(client.getSerial())
        self.failUnless(len(avatars) ==  1, "Only one avatar should have this serial")
        avatar = avatars[0]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerReadyToPlay(serial = client.getSerial(), game_id = gameId))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ACK:
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def sitOut(self, (client, packet), id, gameId ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSitOut(serial= client.getSerial(), game_id = gameId))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_SIT_OUT:
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.game_id, gameId)
                found = True
            elif packet.type == PACKET_POKER_CHAT:
                print packet
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def dealTable(self, (client, packet), gameId):
        table = self.service.getTable(gameId)
        table.beginTurn()
        table.update()
        return (client, packet)
    # ------------------------------------------------------------------------
    def beginHandSetup(self, (client, packet), gameId, autoDeal = False):
        dealerAssigned = 1
        blindAmount = 1
        blindExpected = 'small'
        table = self.service.getTable(gameId)
        avatar0 = self.service.avatars[0]
        avatar1 = self.service.avatars[1]
        avatar0.queuePackets()
        avatar1.queuePackets()
        # Handle the packets that initially arrive.  I learned what to
        # expect from "What to expect while a hand is being played?" in
        # pokerpackets.py
        packetList = []
        packetList.extend(avatar0.resetPacketsQueue())
        packetList.extend(avatar1.resetPacketsQueue())
        playersExpect = [ avatar0.getSerial(), avatar1.getSerial() ]
        playersExpect.sort()
        found = 0
        for packet in packetList:
            if packet.type == PACKET_POKER_IN_GAME:
                found += 1
                self.assertEquals(packet.serial, 0)
                self.assertEquals(packet.game_id, gameId)
                packet.players.sort()
                self.assertEquals(packet.players, playersExpect)
            elif packet.type == PACKET_POKER_DEALER:
                found += 1
                self.assertEquals(packet.dealer, dealerAssigned)
                self.assertEquals(packet.previous_dealer, -1)
                self.assertEquals(packet.game_id, gameId)
            elif packet.type == PACKET_POKER_START:
                found += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.level, 0)
                self.assertEquals(packet.hand_serial, 1)
                self.assertEquals(packet.serial, 0)
                self.assertEquals(packet.hands_count, 0)
                self.assertEquals(packet.time, 0)
            elif packet.type == PACKET_POKER_POSITION:
                found += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(True, packet.serial == avatar0.getSerial() or packet.serial == avatar1.getSerial())
            elif packet.type == PACKET_POKER_CHIPS_POT_RESET:
                found += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.serial, 0)
            elif packet.type == PACKET_POKER_BLIND_REQUEST:
                found += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.dead, 0)
                self.assertEquals(packet.serial, avatar1.getSerial())
                self.assertEquals(packet.amount, blindAmount)
                self.assertEquals(packet.state, blindExpected)
            elif packet.type == PACKET_POKER_SELF_IN_POSITION:
                self.assertEquals(packet.serial, avatar1.getSerial())
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.position, -1)
            elif packet.type == PACKET_POKER_BOARD_CARDS:
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(True, packet.serial == avatar0.getSerial() or packet.serial == avatar1.getSerial())
                self.assertEquals(packet.cards, [])
            # When I was writing this loop, I also saw a number of:
            # POKER_PLAYER_CHIPS and also the POKER_PLAYER_ARRIVE for
            # serial 5, but I thought it was safe to ignore them here.
        
        expected = 14 if autoDeal else 12
        self.assertEquals(found, expected, pprint.pformat(packetList))
        avatar0.queuePackets()
        avatar1.queuePackets()
        return (client, packet)
    # ------------------------------------------------------------------------
    def doBlindPost(self, (client, packet), id, gameId):
        # By now, we should have seen as noted above, a request for the
        # blinds for avatar1 for 1 small blind.  Here we send it.
        avatars = self.service.avatar_collection.get(client.getSerial())
        self.failUnless(len(avatars) ==  1, "Only one avatar should have this serial")
        avatar = avatars[0]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerBlind(serial= avatar.getSerial(), game_id = gameId, dead = 0, amount = 1))
        return (client, packet)
    # -------------------------------------------------------------------------
    def setMoneyForPlayer(self, (client, packet), id, currency_serial, setting, gameId):
        table = self.service.getTable(gameId)
        game = table.game
        amount = 0
        if setting == "under_min":
            amount = game.buyIn() - 1
        elif setting == "over_min_under_best":
            amount = game.buyIn() + 1
        elif setting == "min":
            amount = game.buyIn()
        elif setting == "best":
            amount = game.bestBuyIn()
        elif setting == "over_best":
            amount = game.bestBuyIn() +1
        else:
            self.fail("Unknown setting for setMoneyForPlayer: %s" % setting)

        cursor = self.service.db.cursor()
        sql =  "DELETE FROM user2money WHERE user_serial = " + str(client.getSerial())
        cursor.execute(sql)
        sql = "INSERT INTO user2money(amount, user_serial, currency_serial) VALUES(%s, %s, %s)" % (str(amount),  str(client.getSerial()), str(currency_serial))
        cursor.execute(sql)
        cursor.close()
        return (client, packet)    
##############################################################################
class PokerAvatarTestCase(PokerAvatarTestCaseBaseClass):
    # -------------------------------------------------------------------------
    def ping(self, client):
        client.sendPacket(PacketPing())
        return (client,)
    # -------------------------------------------------------------------------
    def explain(self, (client, packet)):
        avatar = self.service.avatars[0]
        self.assertNotEqual(None, avatar.explain)
        serial = 200
        packet_serial = PacketSerial(serial = serial)
        self.assertTrue(avatar.explain.explain(packet_serial))
        self.assertEqual(packet_serial, avatar.explain.forward_packets[0])
        self.assertEqual(serial, avatar.explain.getSerial())
        return (client,)
    # -------------------------------------------------------------------------
    def test02_explain(self):
        """ test02_explain """
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.explain)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def login_again(self, (client, packet)):
        avatar = self.service.avatars[0]
        self.assertNotEqual(None, avatar.explain)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketLogin(name = 'user0', password = 'password1'))
        answer = avatar._packets_queue[0]
        self.assertEqual(PACKET_ERROR, answer.type)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test03_login_again(self):
        """ test03_login """
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.login_again)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def test04_createTable(self):
        """Tests receipt of a table creation packet, followed by creation of a
           table once the avatar is logged in."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        def handleTable((client, packet)):
            avatar = self.service.avatars[0]
            table_packet = PacketPokerTable(
                id = 1, seats  = 5,
                name = "A Testing Cash Table", variant = "holdem",
                betting_structure = '1-2_20-200_limit', player_timeout =  6,
                currency_serial = 0
            )
            packets = avatar.handlePacket(table_packet)
            self.assertEquals(len(avatar.tables), 0)
            self.assertEquals(packets[0].type, PACKET_AUTH_REQUEST, 'cannot create table as user.REGULAR')
            avatar.user.privilege = avatar.user.ADMIN
            packets = avatar.handlePacket(table_packet)
            self.assertEquals(packets[0].type, PACKET_ACK, 'can create table as user.ADMIN')
            return (client, packet)
        d.addCallback(handleTable)
        return d
    # -------------------------------------------------------------------------
    def test05_testStrInterpolation(self):
        """Tests to make sure the string output of an avatar is accurate"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        def stringAvatar((client, packet)):
            self.assertEquals(str(self.service.avatars[0]),
                              "PokerAvatar serial = 4, name = user0")
            return (client, packet)
            
        d.addCallback(stringAvatar)
        return d
    # -------------------------------------------------------------------------
    def normalSetRoles(self, (client, packet), myRoles, rolesString):
        avatar = self.service.avatars[0]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSetRole(serial = client.getSerial(), roles = myRoles))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_ROLES:
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.roles, rolesString)
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # -------------------------------------------------------------------------
    def test06_setRoles(self):
        """Tests setting of roles"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.normalSetRoles, PacketPokerRoles.PLAY, "PLAY")
        d.addCallback(self.login, 0)
        d.addCallback(self.quit)
        return d
    # -------------------------------------------------------------------------
    def test06_5_setRolesIsAnErrorWhenDoneAfterLogin(self):
        """Tests setting of roles after a login has already occurred.  Results are
        undefined in this case."""
        # While I was writing full coverage tests here, Loic and I
        # discovered that bad behavior occurs if you set roles after
        # you've logged in.  It must be done before, as is done in the
        # above test.  Loic documented this in
        # pokernetwork/pokerpackets.py as of r3654 about this issue.  This
        # test here looks for the blow-up that we discovered in the
        # undefined behavhior.  Since we've determined the behavior to be
        # undefined, this test might need to be updated later to test for
        # the undefined behavior we see. ;) Perhaps testing for things
        # that aren't defined with this.
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        def setRoles((client, packet)):
            avatar = self.service.avatars[0]
            avatar.handlePacket(PacketPokerSetRole(serial = client.getSerial(), roles = PacketPokerRoles.PLAY))
            try:
                avatar.logout()
            except KeyError, ke:
                self.assertEquals(ke.args[0], client.getSerial())
            # Reset avatar role values back to blank so future errors of
            # this type do not occur.
            avatar.roles = ""
            return (client, packet)
        d.addCallback(setRoles)
        return d
    # -------------------------------------------------------------------------
    def errorSetRoles(self, (client, packet), myRoles, errorCode, errorMessage):
        avatar = self.service.avatars[0]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSetRole(serial = client.getSerial(), roles = myRoles))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ERROR:
                self.assertEquals(packet.other_type, PACKET_POKER_SET_ROLE)
                self.assertEquals(packet.code, errorCode)
                self.assertEquals(packet.message, errorMessage)
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # -------------------------------------------------------------------------
    def test06_7_setUnknownRole(self):
        """Tests setting of a role that is unknown."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        # This error message will need to be fixed if you add additional valid roles 
        d.addCallback(self.errorSetRoles, "YOU_HAVE_NEVER_HEARD_OF_THIS_ROLE",
                      PacketPokerSetRole.UNKNOWN_ROLE, "role YOU_HAVE_NEVER_HEARD_OF_THIS_ROLE is unknown (roles = ['PLAY', 'EDIT'])")
        d.addCallback(self.login, 0)
        d.addCallback(self.quit)
        return d
    # -------------------------------------------------------------------------
    def test06_8_setRoleAfterAnotherUserHas(self):
        """Tests setting of a role that is unknown."""
        def client1():
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.normalSetRoles, PacketPokerRoles.PLAY, "PLAY")
            d.addCallback(self.login, index)
            return d

        def client2():
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.errorSetRoles, PacketPokerRoles.PLAY,
                PacketPokerSetRole.NOT_AVAILABLE,
                "another client already has role %s" % PacketPokerRoles.PLAY
            )
            d.addCallback(self.login, index)
            return d

        dl = defer.DeferredList([client1(),client2()])
        def quitAll(client_info):
            for (_packet,client) in client_info:
                self.quit(client)

        dl.addCallback(quitAll)
        return dl
    # -------------------------------------------------------------------------
    def test08_joinTable(self):
        """Tests table joining."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def test08_1_joinTable_buy_in_payed(self):
        """Tests table joining with buy_in_payed."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def test08_joinTable_pending_packet(self):
        """Tests table joining, check that packets related to the table and still in the avatar queue are discarded."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        game_id = 2
        def joinTable((client, packet)):
            avatar = self.service.avatars[0]
            avatar.queuePackets()
            avatar.sendPacket(PacketPokerMessage(serial = 111, game_id = 222))
            avatar.sendPacket(PacketPokerPlayerLeave(seat = 1, serial = 111, game_id = game_id))
            avatar.sendPacket(PacketPokerMonitor())
            avatar.handlePacketLogic(PacketPokerTableJoin(serial = client.getSerial(), game_id = game_id))
            packets = avatar.resetPacketsQueue()
            self.assertEquals(PACKET_POKER_MESSAGE, packets[0].type)
            self.assertEquals(PACKET_POKER_MONITOR, packets[1].type)
            self.assertEquals(PACKET_POKER_TABLE, packets[2].type)
            self.assertEquals(7, len(packets))
            return (client, packet)
        d.addCallback(joinTable)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def test09_00_seatTable(self):
        """Tests table joining table and sitting down."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def createRankDBTable(self, (client, packet), gameId, rank, percentile):
        table = self.service.getTable(gameId)
        self.service.db.db.query('CREATE TABLE rank (user_serial INT, currency_serial INT, rank INT, percentile TINYINT)')
        self.service.db.db.query('INSERT INTO rank VALUES(%d, %d, %d, %d)' %
                                 (client.getSerial(), table.currency_serial, rank, percentile))
        self.service.setupLadder()
        return (client, packet)
    # ------------------------------------------------------------------------
    def test09_01_seatTableWithRankTable(self):
        """Tests joining table and sitting down, with a stats packet."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.createRankDBTable, 2, rank = 60, percentile = 80)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2, 60, 80)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def forceExplain(self, (client, packet), id):
        avatar = self.service.avatars[id]
        table = self.service.getTable(101)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerExplain(
                serial = client.getSerial(), value = PacketPokerExplain.ALL))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ERROR:
                found = True
                self.assertEquals(packet.other_type, PACKET_POKER_EXPLAIN)
                self.assertEquals(packet.code, 0)
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test10_explainFailsOnceAtTable(self):
        """Tests to be sure setting explain fails when you are already
        connected to to table."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.forceExplain, 0)
        d.addCallback(self.quit)
        return d

    # ------------------------------------------------------------------------
    def test10_explainTwiceIsOk(self):
        """Tests to be sure setting explain twice succeeds if already set."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        def explainAgain((client, packet), id):
            avatar = self.service.avatars[id]
            table = self.service.getTable(101)
            avatar.queuePackets()
            avatar.handlePacketLogic(PacketPokerExplain(
                    serial = client.getSerial(), value = PacketPokerExplain.ALL))
            found = False
            for packet in avatar.resetPacketsQueue():
                if packet.type == PACKET_ACK:
                    found = True
            self.assertEquals(found, True)
            return (client, packet)
        d.addCallback(explainAgain, 0)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def loginWithPasswordTooLong(self, (client, packet), index):
        client.sendPacket(PacketLogin(name = 'user%d' % index, password = 'passwordislongerthan15chars'))
        d = client.packetDeferred(True, PACKET_AUTH_REFUSED)
        def checkbadLoginReturn( (client, packet) ):
            self.assertEquals(packet.type, PACKET_AUTH_REFUSED)
            self.assertEquals(packet.message, "password must be at most 15 characters long")
            self.assertEquals(packet.code, 6)
            self.assertEquals(packet.other_type, PACKET_LOGIN)
            self.assertEquals(client.getSerial(), 0)
        d.addCallback(checkbadLoginReturn)
        return d
    # ------------------------------------------------------------------------
    def test11_loginWithPasswordTooLong(self):
        """Tests to be sure setting explain fails when you are already
        connected to to table."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.loginWithPasswordTooLong, 0)
        return d
    # ------------------------------------------------------------------------
    def test12_buyIntoGame(self):
        """Tests to be sure once sat down, the user can buy into the game"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def statsQuery(self, (client, packet), id):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerStatsQuery(serial = client.getSerial()))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_STATS:
                found = True
                self.assertEquals(packet.players, 3)
                # assert(packet.bytesin > 0)
                # assert(packet.bytesout > 0)
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test13_stats(self):
        """Test stats request"""
        self.createClients(3)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.statsQuery, 0)
        return d
    # ------------------------------------------------------------------------
    def startHandAndReceiveCards(self, (client, packet), gameId):
        table = self.service.getTable(gameId)

        lang2strings = { 
            'default' : [  
                "Dealer: user1 pays 1 blind\n",
                "Dealer: user0 pays 2 blind\n",
                "Dealer: pre-flop, 2 players\n" 
            ], 
             'en_US' : [ 
                "Dealer: user1 pays 1 blind\n",
                "Dealer: user0 pays 2 blind\n",
                "Dealer: pre-flop, 2 players\n" 
            ], 
             'de_DE' : [
                "Dealer: user1 zahlt 1 blind\n",
                "Dealer: user0 zahlt 2 blind\n",
                "Dealer: pre-flop, 2 Spieler\n"
            ] 
        }
        avatar = []
        avatar.append(self.service.avatars[0])
        avatar.append(self.service.avatars[1])

        packetList = []
        packetList.append(avatar[0].resetPacketsQueue())
        packetList.append(avatar[1].resetPacketsQueue())

        found = 0
        ignored = 0
        for avid in [0, 1]:
            otherid = avid -1
            if otherid < 0: otherid = 1
            mySerial = avatar[avid].getSerial()
            for packet in packetList[avid]:
                if packet.type == PACKET_POKER_BLIND:
                    found += 1
                    self.assertEquals(packet.game_id, gameId)
                    self.assertEquals(packet.dead, 0)
                    if packet.serial == avatar[1].getSerial():
                        self.assertEquals(packet.amount, 1)
                    elif packet.serial == avatar[0].getSerial():
                        self.assertEquals(packet.amount, 2)
                    else:
                        self.assertEquals("", "Unknown serial: %d" % packet.serial)
                elif packet.type == PACKET_POKER_CHIPS_PLAYER2BET:
                    found += 1
                    self.assertEquals(packet.game_id, gameId)
                    if (packet.serial == avatar[0].getSerial()):
                        self.assertEquals(packet.chips, [1, 2])
                    elif (packet.serial == avatar[1].getSerial()):
                        self.assertEquals(packet.chips, [1, 1])
                    else:
                        assert("unknown serial in player2bet packet: %d" % packet.serial)
                elif packet.type == PACKET_POKER_CHIPS:
                    found += 1
                    self.assertEquals(packet.serial, mySerial)
                    self.assertEquals(packet.game_id, gameId)
                    if (avid == 0):
                        self.assertEquals(packet.bet, 2)
                        self.assertEquals(packet.money, 8)
                    else:
                        self.assertEquals(packet.bet, 1)
                        self.assertEquals(packet.money, 9)
                elif packet.type == PACKET_POKER_CHAT:
                    found += 1
                    self.assertEquals(packet.game_id, gameId)
                    self.assertEquals(packet.serial, 0)
                    if (packet.message not in lang2strings[self.avatarLocales[avid]]):
                        self.fail(
                            "Unexpected and/or Wrong Language (expected %s) message: %s for avatar %d" % \
                            (self.avatarLocales[avid], packet.message, avid)
                        )
                elif packet.type == PACKET_POKER_STATE:
                    found += 1
                    self.assertEquals(packet.game_id, gameId)
                    self.assertEquals(packet.serial, 0)
                    self.assertEquals(packet.string, "pre-flop")
                elif packet.type == PACKET_POKER_BEGIN_ROUND:
                    found += 1
                    self.assertEquals(packet.game_id, gameId)
                    self.assertEquals(packet.serial, 0)

                elif packet.type == PACKET_POKER_PLAYER_CARDS:
                    found += 1
                    self.assertEquals(packet.game_id, gameId)
                    if (packet.serial == mySerial):
                        self.assertEquals(len(packet.cards), 2)
                        for c in packet.cards:
                            self.assertTrue(c <  255)
                            self.assertTrue(c >  0)
                    else:
                        self.assertEquals(packet.cards, [255, 255])
                elif packet.type == PACKET_POKER_BET_LIMIT:
                    found += 1
                    self.assertEquals(packet.game_id, gameId)
                    self.assertEquals(packet.serial, 0)
                    self.assertEquals(packet.step, 1)
                    if (avid == 0):
                        self.assertEquals(packet.min, 2)
                        self.assertEquals(packet.max, 2)
                        self.assertEquals(packet.allin, 18)
                        self.assertEquals(packet.pot, 3)
                        self.assertEquals(packet.call, 0)
                    else:
                        self.assertEquals(packet.min, 3)
                        self.assertEquals(packet.max, 3)
                        self.assertEquals(packet.allin, 19)
                        self.assertEquals(packet.pot, 5)
                        self.assertEquals(packet.call, 1)
                else:
                    ignored += 1
        self.assertEquals(found, 26)
        self.assertEquals(ignored, 16)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test15_handPlay(self):
        """Test playing an actual hand all the way through"""
        # The sequence of how to get yourself seated in a cash game was
        # taken from the instructions at the top of pokerpackets.py
        # labelled "How to sit at a cash game table ?"
        def client1(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.setLocale, "de_DE")
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.createRankDBTable, gameId, rank = 50, percentile = 30)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId, 50, 30)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        def client2(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(
                self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit',
                [{ 'rank' : 50, 'percentile' : 30, 'serial' : 4}]
            )
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            # Note: this avatar does not autopost, and doBlindPost handles it.
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        gameId = 2
        dl = defer.DeferredList([client1(gameId), client2(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.dealTable, gameId)
        dl.addCallback(self.beginHandSetup, gameId)
        dl.addCallback(self.doBlindPost, 1, gameId)
        dl.addCallback(self.startHandAndReceiveCards, gameId)
        return dl
    # -------------------------------------------------------------------------
    def sendExplainTooLate(self, (client, packet)):
        avatar = self.service.avatars[0]
        d = client.packetDeferred(True, PACKET_ERROR)
        def checkError( (client, packet) ):
            self.assertEquals(packet.type, PACKET_ERROR)
            self.assertEquals(packet.other_type, PACKET_POKER_EXPLAIN)
            self.assertEquals(packet.code, 0)
            self.assertEquals(packet.message, "no message")
        d.addCallback(checkError)
        # I believe that turning off packet queue here happens to get some
        # extra coverage in the pokeravatar.sendPacket() function.  Think
        # twice before using the queue in this test.
        avatar.noqueuePackets()
        client.sendPacket(PacketPokerExplain(value = PacketPokerExplain.ALL))
        return  d
    # ------------------------------------------------------------------------
    def forceDbToLocaleValue(self, (client, packet), avid = 0, setTo = '', expect = '', updateCount = 0):
        from pokernetwork.pokerauth import get_auth_instance
        auth = get_auth_instance(self.service.db, self.service.memcache, self.service.settings)

        avatar = self.service.avatars[avid]
        self.avatarLocales[avid] = expect

        cursor = self.service.db.cursor()
        cursor.execute(
            "INSERT INTO users (created, name, password, locale) VALUES (%s, %s, %s, %s)",
            (seconds(), 'user%d' % avid, 'password1', setTo)
        )
        self.assertEquals(cursor.rowcount, 1)
        cursor.close()
        return (client, packet)
    # ------------------------------------------------------------------------
    # RANDOM
    def test15a_handPlay_dbLocalesAndOverridesThereof(self):
        """Test playing an actual hand all the way through when locale changes"""
        def client1(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.forceDbToLocaleValue, avid = 0, setTo = 'de_DE', expect = "RESET_BY_SET_LOCALE")
            d.addCallback(self.setLocale, "de_DE")
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.createRankDBTable, gameId, rank = 50, percentile = 30)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId, 50, 30)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        def client2(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.forceDbToLocaleValue, avid = 1, setTo = 'de_DE', expect = "de_DE")
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(
                self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit', 
                [{ 'rank' : 50, 'percentile' : 30, 'serial' : 4}]
            )
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            # Note: this avatar does not autopost, and doBlindPost handles it.
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        gameId = 2
        dl = defer.DeferredList([client1(gameId), client2(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.dealTable, gameId)
        dl.addCallback(self.beginHandSetup, gameId)
        dl.addCallback(self.doBlindPost, 1, gameId)
        dl.addCallback(self.startHandAndReceiveCards, gameId)
        return dl

    # -------------------------------------------------------------------------
    def test16_explainTooLate(self):
        """This test covers the case where you attempt to turn on explain
        after being at a table."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.sitTable, 0, 2)
        d.addCallback(self.sendExplainTooLate)
        return d
    # -------------------------------------------------------------------------
    def pingThenExpectPrivilegeFailure(self, (client, packet), sendingPacket, id = 0):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPing())
        avatar.handlePacketLogic(sendingPacket)
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_AUTH_REQUEST:
                found = True
        self.assertEquals(found, True)
        return (client,)
    # -------------------------------------------------------------------------
    def tourneyRegisterUnpriv(self, (client, packet)):
        return self.pingThenExpectPrivilegeFailure((client, packet), 
            PacketPokerTourneyRegister(serial = client.getSerial(), tourney_serial = 3))
    # -------------------------------------------------------------------------
    def test17_0_tourneyRegisterUnpriv(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.tourneyRegisterUnpriv)
        return d
    # -------------------------------------------------------------------------
    def seatUnpriv(self, (client, packet)):
        return self.pingThenExpectPrivilegeFailure((client, packet), 
                   PacketPokerSeat(serial = client.getSerial(),
                                   seat = 0, game_id = 3))
    # -------------------------------------------------------------------------
    def test17_1_seatUnpriv(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.seatUnpriv)
        return d
    # -------------------------------------------------------------------------
    def userInfoUnpriv(self, (client, packet)):
        return self.pingThenExpectPrivilegeFailure((client, packet), 
             PacketPokerGetUserInfo(serial = client.getSerial()))
    # -------------------------------------------------------------------------
    def test17_2_userInfoUnpriv(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.userInfoUnpriv)
        return d
    # -------------------------------------------------------------------------
    def personalInfoUnpriv(self, (client, packet)):
        return self.pingThenExpectPrivilegeFailure((client, packet), 
             PacketPokerGetPersonalInfo(serial= client.getSerial()))
    # -------------------------------------------------------------------------
    def test17_3_personalInfoUnpriv(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.personalInfoUnpriv)
        return d
    # -------------------------------------------------------------------------
    def playerInfoUnpriv(self, (client, packet)):
        return self.pingThenExpectPrivilegeFailure((client, packet), 
            PacketPokerPlayerInfo(serial= client.getSerial(), name = "The Naked Guy",
                                  outfit = "Naked", url = "http://example.org"))
    # -------------------------------------------------------------------------
    def test17_4_tourneyTourneyRegisterUnpriv(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.playerInfoUnpriv)
        return d
    # -------------------------------------------------------------------------
    def requestsWithWrongSerial(self, (client, packet), avid, gameId):
        avatar = self.service.avatars[avid]
        avatar.queuePackets()
        someoneElseSerial = client.getSerial() + 1
        userByUser = " for user %d by user %d" % (someoneElseSerial, client.getSerial())
        forPlayerByPlayer = " for player %d by player %d" % (someoneElseSerial, client.getSerial())
        ofPlayerByPlayer = " of player %d by player %d" % (someoneElseSerial, client.getSerial())
        messageStart = ""
        badPacketAttempts = {
            'user_info': {
                'output': "%sattempt to get user info%s" % (messageStart, userByUser),
                'packet': PacketPokerGetUserInfo(serial = someoneElseSerial)
            },
            'get_personal': {
                'output': "%sattempt to get personal info%s" % (messageStart, userByUser),
                'packet': PacketPokerGetPersonalInfo(serial = someoneElseSerial),
                'err_type': PACKET_AUTH_REQUEST 
            },
            'player_info': {
                'output': "%sattempt to set player info%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerPlayerInfo(serial = someoneElseSerial,
                      name = "YOU_BEEN_CRACKED",
                      url = "http://example.com/myhack", 
                      outfit = "Naked"
                )
            },
            'set_personal': { 
                'output': "%sattempt to set player info%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerPersonalInfo(
                    serial = someoneElseSerial,
                    firstname = "YOU_HAVE",
                    lastname = "BEEN_CRACKED", 
                    birthday = "2001-01-01"
                ) 
            },
            'cash_in': { 
                'output': "%sattempt to cash in%s" % (messageStart, userByUser),
                'packet': PacketPokerCashIn(
                    serial = someoneElseSerial, 
                    name = "YOU_BEEN_CRACKED", value = 10000,
                    url = "http://example.com/myhack"
                ),
                'err_type': PACKET_POKER_ERROR,
                'other_type': PACKET_POKER_CASH_IN 
            },
            'cash_out': { 
                'output': "%sattempt to cash out%s" % (messageStart, userByUser),
                'packet': PacketPokerCashOut(
                     serial = someoneElseSerial, 
                     name = "YOU_BEEN_CRACKED", value = 10000,
                     url = "http://example.com/myhack"
                ),
                'err_type': PACKET_POKER_ERROR,
                'other_type': PACKET_POKER_CASH_OUT 
            },
            'tourney_reg': { 
                'output': "%sattempt to register in tournament %d%s" % (messageStart, gameId, forPlayerByPlayer),
                'packet': PacketPokerTourneyRegister(serial = someoneElseSerial, tourney_serial = gameId) 
            },
            'tourney_unreg': { 
                'output': "%sattempt to unregister from tournament %d%s" % (messageStart, gameId, forPlayerByPlayer),
                'packet': PacketPokerTourneyUnregister(serial = someoneElseSerial,tourney_serial = gameId) 
            },
            'hand_hist': {
                'output': "%sattempt to get history%s" % (messageStart, ofPlayerByPlayer),
                'packet': PacketPokerHandHistory(serial=someoneElseSerial, serial2name={someoneElseSerial:"YOU_BEEN_CRACKED"}, history='CRACKED')
            },
            'ready': {
                'output': "%sattempt to set ready to play%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerReadyToPlay(serial=someoneElseSerial, game_id=gameId) 
            },
            'proc': {
                'output': "%sattempt to set processing hand%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerProcessingHand(serial=someoneElseSerial, game_id=gameId)
            },
            'seat': {
                'output': "%sattempt to get seat%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerSeat(serial=someoneElseSerial, seat=255, game_id=gameId) 
            },
            'buyin': {
                'output': "%sattempt to bring money%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerBuyIn(serial=someoneElseSerial, amount=10, game_id=gameId)
            },
            'rebuy': {
                'output': "%sattempt to rebuy%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerRebuy(serial=someoneElseSerial, amount=10, game_id=gameId)
            },
            'chat': {
                'output': "%sattempt to chat%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerChat(serial=someoneElseSerial, game_id=gameId, message="I AM IN YOUR SERIALZ CHATING YOUR POKERZ")
            },
            'leave': {
                'output': "%sattempt to leave%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerPlayerLeave(serial= someoneElseSerial, game_id= gameId, seat=2) 
            },
            'sit': {
                'output': "%sattempt to sit back%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerSit(serial=someoneElseSerial, game_id=gameId)
            },
            'sitout': {
                'output': "%sattempt to sit out%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerSitOut(serial=someoneElseSerial, game_id=gameId)
            },
            'autoblind': {
                'output': "%sattempt to set auto blind/ante%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerAutoBlindAnte(serial=someoneElseSerial, game_id=gameId) },
            'noautoblind': {
                'output': "%sattempt to set auto blind/ante%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerNoautoBlindAnte(serial=someoneElseSerial, game_id=gameId)
            },
            'muckaccept': {
                'output': "%sattempt to accept muck%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerMuckAccept(serial=someoneElseSerial, game_id=gameId)
            },
            'muckdeny': {
                'output': "%sattempt to deny muck%s" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerMuckDeny(serial=someoneElseSerial, game_id=gameId)
            },
            'automuck': {
                'output': "%sattempt to set auto muck%s, or player is not in game" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerAutoMuck(serial=someoneElseSerial, game_id=gameId, info = 0x01) 
            },
            'blind': {
                'output': "%sattempt to pay the blind%s, or player is not not playing" % (messageStart, ofPlayerByPlayer),
                'packet': PacketPokerBlind(serial=someoneElseSerial, game_id=gameId, dead=0, amount=1)
            },
            'waitblind': {
                'output': "%sattempt to wait for big blind%s" % (messageStart, ofPlayerByPlayer),
                'packet': PacketPokerWaitBigBlind(serial = someoneElseSerial, game_id = gameId)
            },
            'ante': {
                'output': "%sattempt to pay the ante%s, or player is not not playing" % (messageStart, ofPlayerByPlayer ),
                'packet': PacketPokerAnte(serial = someoneElseSerial, game_id = gameId,amount = 10) 
            },
            'fold': {
                'output': "%sattempt to fold%s, or player is not not playing" % (messageStart, forPlayerByPlayer ),
                'packet': PacketPokerFold(serial = someoneElseSerial, game_id = gameId)
            },
            'call': {
                'output': "%sattempt to call%s, or player is not not playing" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerCall(serial = someoneElseSerial, game_id = gameId)
            },
            'raise': {
                'output': "%sattempt to raise%s, or player is not not playing" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerRaise(serial = someoneElseSerial, game_id = gameId, amount=1)
            },
            'start': { 
                'output': "%splayer %d %s" % (
                    messageStart, client.getSerial(),
                    "tried to start a new game but is not the owner of the table"
                ),
                'packet': PacketPokerStart(serial = someoneElseSerial,game_id = gameId),
            },
            'check': {
                'output': "%sattempt to check%s, or player is not not playing" % (messageStart, forPlayerByPlayer),
                'packet': PacketPokerCheck(serial = someoneElseSerial, game_id = gameId) 
            }
        }
        badAdminAttempts = {
            'tourney_create': { 
                'output': "attempt to create tourney%s"  % forPlayerByPlayer,
                'packet': PacketPokerCreateTourney(serial = someoneElseSerial),
                'err_type': PACKET_AUTH_REQUEST 
            },
        }
        # Next, we loop through all the serial-related bad pack list,
        # attempting to handle each one.  Setup stdout to go to a string
        # so that we can test if they generate the right printed output.
        # Also, catch any error packets for those we expect to receive.
        def assertBadAttempt(key,info):
            avatar.resetPacketsQueue()
            avatar.queuePackets()
            log_history.reset()
            avatar.handlePacketLogic(info['packet'])
            self.assertEqual(log_history.search(info['output']), True, info['output'])

            found = False
            for packet in avatar.resetPacketsQueue():
                found = True
                self.assertEquals(packet.type, info['err_type'])
                if 'other_type' in info:
                    self.assertEquals(info['other_type'], packet.other_type)
            self.assertEquals(found, 'err_type' in info)
        for (key, info) in badPacketAttempts.iteritems():
            assertBadAttempt(key,info)
        
        avatar.user.privilege = avatar.user.ADMIN
        for (key, info) in badAdminAttempts.iteritems():
            assertBadAttempt(key,info)
            
        return (client, packet)
    # -------------------------------------------------------------------------
    def test18_badAttempts(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.sitTable, 0, 2)
        d.addCallback(self.requestsWithWrongSerial, 0, 2)
        return d
    # -------------------------------------------------------------------------
    def badBuyIn(self, (client, packet), id, gameId, myAmount):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        seatNumber = id + 1
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerBuyIn(serial = client.getSerial(), amount = myAmount, game_id = gameId))
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_ERROR:
                found += 1
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.other_type, PACKET_POKER_BUY_IN)
        self.assertEquals(found, 1)
        return (client, packet)
    # -------------------------------------------------------------------------
    def test19_badBuyIn(self):
        """Test to cover the condition where the buyIn fails"""        
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 1, 'Table1', '100-200_2000-20000_no-limit')
        d.addCallback(self.setMoneyForPlayer, 0, 1, 'min', 1)
        d.addCallback(self.seatTable, 0, 1)
        d.addCallback(self.setMoneyForPlayer, 0, 1, 'under_min', 1)
        d.addCallback(self.badBuyIn, 0, 1, 1)
        return d
    
    def test19a_cannotSitWithoutEnoughMoney(self):
        """A player should not be able to get a seat if he cannot afford the buyin"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 1, 'Table1', '100-200_2000-20000_no-limit')
        d.addCallback(self.setMoneyForPlayer, 0, 1, 'under_min', 1)        
        d.addCallback(self.seatTable, 0, 1)
        d.addCallbacks(lambda *a,**kw: self.fail('should have failed'), lambda *a,**kw: True)
        return d    
    # ------------------------------------------------------------------------
    def noAutoBlindAnte(self, (client, packet), id, gameId ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerNoautoBlindAnte(serial= client.getSerial(), game_id = gameId))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_NOAUTO_BLIND_ANTE:
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.game_id, gameId)
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # -------------------------------------------------------------------------
    def test20_turningOffAutoBlind(self):
        """Test to cover a player turning off their autoBlindAnte Setting"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.noAutoBlindAnte, 0, 2)
        return d
    # -------------------------------------------------------------------------
    def test21_sitOut(self):
        """Test playing an actual hand all the way through"""
        # The sequence of how to get yourself seated in a cash game was
        # taken from the instructions at the top of pokerpackets.py
        # labelled "How to sit at a cash game table ?"
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.sitTable, 0, 2)
        d.addCallback(self.readyToPlay, 0, 2)
        d.addCallback(self.sitOut, 0, 2)
        return d
    # -------------------------------------------------------------------------
    def sitOutClosedGame(self, (client, packet), id, gameId ):
        table = self.service.getTable(gameId)
        table.game.close()

        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSitOut(serial = client.getSerial(), game_id = gameId))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_AUTO_FOLD:
                self.assertEquals(False, table.game.getPlayer(avatar.getSerial()).sit_out)
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.game_id, gameId)
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # -------------------------------------------------------------------------
    def joinTableAndCheckPokerSitAndAutoFoldAreSend(self, (client, packet), id, gameId, name, struct):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTableJoin(serial = client.getSerial(), game_id = gameId))
        founds = [packet.type for packet in avatar.resetPacketsQueue()
                  if packet.type == PACKET_POKER_SIT
                  or packet.type == PACKET_POKER_AUTO_FOLD]
        self.assertEquals(founds[0], PACKET_POKER_SIT)
        self.assertEquals(founds[1], PACKET_POKER_AUTO_FOLD)
        return (client, packet)
    # -------------------------------------------------------------------------    
    def test22_sitOutClosedGame(self):
        """Test playing an actual hand all the way through"""
        # The sequence of how to get yourself seated in a cash game was
        # taken from the instructions at the top of pokerpackets.py
        # labelled "How to sit at a cash game table ?"
        def client1(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.setLocale, "de_DE")
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.createRankDBTable, gameId, rank = 50, percentile = 30)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId, 50, 30)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            d.addCallback(self.sitOutClosedGame, index, gameId)
            return d
        def client2(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTableAndCheckPokerSitAndAutoFoldAreSend, index, gameId, 'Table2', '1-2_20-200_limit')
            return d
        gameId = 2
        return defer.DeferredList([client1(gameId),client2(gameId)])
    # ------------------------------------------------------------------------
    def doBlindPostAndHaveOtherGuyWaitForCardsAndQuit(self, (client, packet), id, gameId):
        # By now, we should have seen as noted above, a request for the
        # blinds for avatar1 for 100 small blind.  Here we send it.
        otherAvatar = self.service.avatars[0]
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerBlind(
            serial = avatar.getSerial(),
            game_id = gameId, 
            dead = 0,
            amount = 100
        ))
        otherAvatar.removePlayer(table, otherAvatar.getSerial())
        return (client, packet)
    # ------------------------------------------------------------------------
    def test23_quitPlayerInHand(self):
        """Test when a player quits in the middle of a hand."""
        # The sequence of how to get yourself seated in a cash game was
        # taken from the instructions at the top of pokerpackets.py
        # labelled "How to sit at a cash game table ?"
        def client(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        gameId = 2
        dl = defer.DeferredList([client(gameId),client(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.dealTable, gameId)
        dl.addCallback(self.beginHandSetup, gameId, True)
        dl.addCallback(self.doBlindPostAndHaveOtherGuyWaitForCardsAndQuit, 1, gameId)
        return dl

    # ------------------------------------------------------------------------
    def getPersonalInfo(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerGetPersonalInfo(serial= client.getSerial()))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PERSONAL_INFO:
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.name, "user%d" % id)
                self.assertEquals(packet.password, "")
                self.assertEquals(packet.rating, 1000)
                self.assertEquals(packet.affiliate, 0)
                self.assertEquals(packet.addr_street, "")
                self.assertEquals(packet.firstname, "Joe")
                self.assertEquals(packet.lastname, "Schmoe")
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def setPersonalInfo(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerPersonalInfo(serial= client.getSerial(),
                                                         firstname = "Joe",
                                                         lastname = "Schmoe"))
        return (client, packet)
    # ------------------------------------------------------------------------
    def test24_personalInfo(self):
        """Test lookup of personal information."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.setPersonalInfo, 0)
        d.addCallback(self.getPersonalInfo, 0)
        return d
    # ------------------------------------------------------------------------
    def listHands(self, (client, packet), id, mySerial):
        avatar = self.service.avatars[id]
        if mySerial == -1: mySerial = client.getSerial()
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerHandSelect(serial= mySerial, count = 5, start = 0))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_HAND_LIST:
                self.assertEquals(packet.count, 5)
                self.assertEquals(packet.hands, [])
                self.assertEquals(packet.total, 0)
                found = True
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerHandSelect(serial= None, count = 5, start = 0))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_HAND_LIST:
                self.assertEquals(packet.count, 5)
                self.assertEquals(packet.hands, [])
                self.assertEquals(packet.total, 0)
                found = True
        self.assertEquals(found, True)

        from _mysql_exceptions import OperationalError
        try:
            avatar.handlePacketLogic(PacketPokerHandSelect(serial= mySerial, count = 5, start = 0,
                                                           string = "Testing"))
        except OperationalError, oe:
            self.assertEquals(oe[0],1054)
            self.assertEquals(oe[1], "Unknown column 'Testing' in 'where clause'")

        return (client, packet)
    # ------------------------------------------------------------------------
    def test25_listHands(self):
        """Test for hand listing."""
        # It might be better to improve this test so that a few hands have
        # actually been played and therfore an actual hand list is available.
        self.createClients(3)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.listHands, 1, -1)
        return d
    # ------------------------------------------------------------------------
    def listTables(self, (client, packet), id):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTableSelect(string = ""))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_TABLE_LIST:
                self.assertEquals(packet.players, 0)
                self.assertEquals(packet.tables, 4)
                count = 0
                for p in packet.packets:
                    count += 1
                    self.assertEquals(p.reason, PacketPokerTable.REASON_TABLE_LIST)
                    self.assertEquals(p.average_pot,  0)
                    self.assertEquals(p.hands_per_hour, 0)
                    self.assertEquals(p.percent_flop, 0)
                    self.assertEquals(p.players, 0)
                    self.assertEquals(p.observers, 0)
                    self.assertEquals(p.waiting, 0)
                    self.assertEquals(p.skin,  "default")
                    self.assertEquals(p.variant, "holdem")
                    if (p.id == 1):
                        self.assertEquals(p.name, "Table1")
                        self.assertEquals(p.betting_structure, "100-200_2000-20000_no-limit")
                        self.assertEquals(p.seats, 10)
                        self.assertEquals(p.player_timeout, 60)
                        self.assertEquals(p.currency_serial, 1)
                    elif (p.id == 2):
                        self.assertEquals(p.name, "Table2")
                        self.assertEquals(p.betting_structure, "1-2_20-200_limit")
                        self.assertEquals(p.player_timeout, 60)
                        self.assertEquals(p.muck_timeout, 5)
                        self.assertEquals(p.currency_serial, 1)
                    elif (p.id == 3):
                        self.assertEquals(p.name, "Table3")
                        self.assertEquals(p.betting_structure, "test18pokerclient")
                        self.assertEquals(p.player_timeout, 600)
                        self.assertEquals(p.muck_timeout, 600)
                        self.assertEquals(p.seats, 10)
                        self.assertEquals(p.currency_serial, 1)
                self.assertEquals(count, packet.tables)
                found = True
        self.assertEquals(found, True)

        return (client, packet)
    # ------------------------------------------------------------------------
    def test26_listTables(self):
        """Test for table listing."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.listTables, 0)
        return d
    # ------------------------------------------------------------------------
    def getPlayerInfoError(self, (client, packet), id):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerGetPlayerInfo())
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ERROR:
                self.assertEquals(packet.code, PacketPokerGetPlayerInfo.NOT_LOGGED)
                self.assertEquals(packet.message, "Not logged in")
                self.assertEquals(packet.other_type, PACKET_POKER_GET_PLAYER_INFO)
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test27_playerInfoNotLoggedIn(self):
        """Test for getting player info before login has occurred."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.getPlayerInfoError, 0)
        return d
    # ------------------------------------------------------------------------
    def setPokerPlayerInfo(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerPlayerInfo(serial= client.getSerial(),
                                                       name = "The Naked Guy",
                                                       outfit = "Naked",
                                                       url = "http://example.org"))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_INFO:
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.name, "The Naked Guy")
                self.assertEquals(packet.outfit, "Naked")
                self.assertEquals(packet.url, "http://example.org")
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test28_setPokerPlayerInfo(self):
        """Test for setting poker player info."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.setPokerPlayerInfo, 0)
        return d
    # ------------------------------------------------------------------------
    def errorSetPokerPlayerInfo(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        def forceFalse(player_info):
            return False
        originalFunction = avatar.service.setPlayerInfo
        avatar.service.setPlayerInfo = forceFalse

        avatar.handlePacketLogic(PacketPokerPlayerInfo(serial= client.getSerial(),
                                                       name = "The Naked Guy",
                                                       outfit = "Naked",
                                                       url = "http://example.org"))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ERROR:
                self.assertEquals(packet.other_type, PACKET_POKER_PLAYER_INFO)
                self.assertEquals(packet.code, PACKET_POKER_PLAYER_INFO)
                self.assertEquals(packet.message, "Failed to save set player information")
                found = True
        self.assertEquals(found, True)
        avatar.service.setPlayerInfo = originalFunction
        return (client, packet)
    # ------------------------------------------------------------------------
    def test29_errorSetPokerPlayerInfo(self):
        """Test for errors when setting poker player info."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.errorSetPokerPlayerInfo, 0)
        return d
    # ------------------------------------------------------------------------
    calledCashIn = False
    def cashIn(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        PokerAvatarTestCase.calledCashIn = False
        def fakeCashIn(packet):
            PokerAvatarTestCase.calledCashIn = True
        self.originalFunction = avatar.service.cashIn
        avatar.service.cashIn = fakeCashIn
        avatar.handlePacketLogic(PacketPokerCashIn(serial= client.getSerial(),
                                                   currency = "http://fake",
                                                   bserial = 0, value = 10))
        return (client, packet)
    # ------------------------------------------------------------------------
    def checkCashIn(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        self.assertEquals(PokerAvatarTestCase.calledCashIn, True)
        avatar.service.cashIn = self.originalFunction
    # ------------------------------------------------------------------------
    def test32_cashIn(self):
        """Test for doing a cash in operation."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.cashIn, 0)
        d.addCallback(self.checkCashIn, 0)
        return d
    # ------------------------------------------------------------------------
    def cashQuery(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerCashQuery(application_data =
                                                      "THIS_WILL_NOT_BE_FOUND_AS_VALID_AT_ALL"))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ERROR:
                self.assertEquals(packet.other_type, PACKET_POKER_CASH_QUERY)
                self.assertEquals(packet.code, PacketPokerCashQuery.DOES_NOT_EXIST)
                self.assertEquals(packet.message, "No record with application_data = 'THIS_WILL_NOT_BE_FOUND_AS_VALID_AT_ALL'")
                found = True
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test33_cashQuery(self):
        """Test for a cash query operation; it's designed to fail and get a packet error."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.cashQuery, 0)
        return d
    # ------------------------------------------------------------------------
    def setPokerAccount(self, (client, packet), id, packetType ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        if packetType == PACKET_POKER_CREATE_ACCOUNT:
            avatar.handlePacketLogic(PacketPokerCreateAccount(serial= client.getSerial()))
        else:
            avatar.handlePacketLogic(PacketPokerSetAccount(serial= client.getSerial()))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ERROR:
                self.assertEquals(packet.other_type, packetType)
                self.assertEquals(packet.code, PacketPokerSetAccount.PASSWORD_TOO_SHORT)
                self.assertEquals(packet.message, "password must be at least 5 characters long")
        return (client, packet)
    # ------------------------------------------------------------------------
    def test34_setPokerAccount(self):
        """Test sending the set poker account packet."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.setPokerAccount, 0, PACKET_POKER_CREATE_ACCOUNT)
        d.addCallback(self.setPokerAccount, 0, PACKET_POKER_SET_ACCOUNT)
        return d
    # ------------------------------------------------------------------------
    def tourneySelect(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTourneySelect(string = ""))
        count = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_TOURNEY_LIST:
                for p in packet.packets:
                    self.assert_(hasattr(p, 'schedule_serial'))
                    assert p.name.find("sitngo") >= 0 or  p.name.find("egular")
                    # assert p.name.find("registering") >= 0 or  p.name.find("announced")
                    count += 1
        self.assertEquals(count, 2)
        return (client, packet)
    # ------------------------------------------------------------------------
    @attr("og-now")
    def test35_tourneys(self):
        """Test sending the set poker account packet."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.tourneySelect, 0)
        return d
    # ------------------------------------------------------------------------
    calledCashOut = False
    def cashOut(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        PokerAvatarTestCase.calledCashOut = False
        def fakeCashOut(packet):
            PokerAvatarTestCase.calledCashOut = True
        self.originalFunction = avatar.service.cashOut
        avatar.service.cashOut = fakeCashOut
        avatar.handlePacketLogic(PacketPokerCashOut(
            serial= client.getSerial(),
            currency = "http://fake",
            bserial = 0, value = 10
        ))
        return (client, packet)
    # ------------------------------------------------------------------------
    def checkCashOut(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        self.assertEquals(PokerAvatarTestCase.calledCashOut, True)
        avatar.service.cashOut = self.originalFunction
    # ------------------------------------------------------------------------
    def test36_cashOut(self):
        """Test for doing a cash out operation."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.cashOut, 0)
        return d
    # ------------------------------------------------------------------------
    calledCashOutCommit = False
    def cashOutCommit(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        PokerAvatarTestCase.calledCashOutCommit = False
        def fakeCashOutCommit(packet):
            PokerAvatarTestCase.calledCashOutCommit = True
        self.originalFunction = avatar.service.cashOutCommit
        avatar.service.cashOutCommit = fakeCashOutCommit
        avatar.handlePacketLogic(PacketPokerCashOutCommit(transaction_id = "0"))
        return (client, packet)
    # ------------------------------------------------------------------------
    def checkCashOutCommit(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        self.assertEquals(PokerAvatarTestCase.calledCashOutCommit, True)
        avatar.service.cashOutCommit = self.originalFunction
    # ------------------------------------------------------------------------
    def test37_cashOutCommit(self):
        """Test for doing a cash out commit operation."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.cashOutCommit, 0)
        return d
    # ------------------------------------------------------------------------
    def tourneyPlayerList(self, (client, packet), id, tourney_serial ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTourneyRequestPlayersList(tourney_serial = tourney_serial))
        for packet in avatar.resetPacketsQueue():
            count = 0
            if packet.type == PACKET_POKER_TOURNEY_PLAYERS_LIST:
                self.assertEquals(packet.tourney_serial, 1)
                count += 1
            self.assertEquals(count, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test38_tourneyPlayerList(self):
        """Test for listing players in a tourney."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.tourneyPlayerList, 0, 1)
        return d
    # ------------------------------------------------------------------------
    def listPlayers(self, (client, packet), id, gameId ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTableRequestPlayersList(serial = client.getSerial(),
                                                                    game_id = gameId))
        for packet in avatar.resetPacketsQueue():
            count = 0
            if packet.type == PACKET_POKER_PLAYERS_LIST:
                self.assertEquals(packet.players, [('user0', 20, 0), ('user1', 20, 0)])
                count += 1
            self.assertEquals(count, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test39_tablePlayerList(self):
        """Test for listing players in at a table."""
        def client(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        gameId = 2
        d = defer.DeferredList([client(gameId),client(gameId)])
        d.addCallback(fixIt)
        d.addCallback(self.listPlayers, 1, gameId)
        return d
    # ------------------------------------------------------------------------
    def tourneyRegister(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTourneyRegister(serial = client.getSerial(), tourney_serial = 1101134))
        for packet in avatar.resetPacketsQueue():
            count = 0
            if packet.type == PACKET_ERROR:
                self.assertEquals(packet.other_type, PACKET_POKER_TOURNEY_REGISTER)
                self.assertEquals(packet.code, PacketPokerTourneyRegister.DOES_NOT_EXIST)
                count += 1
            self.assertEquals(count, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test40_tourneyRegister(self):
        """Test for registering a players in a tourney."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.tourneyRegister, 0)
        return d
    # ------------------------------------------------------------------------
    def tourneyUnregister(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTourneyUnregister(serial = client.getSerial(),
                                                            game_id = 1101134))
        count = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ERROR:
                self.assertEquals(packet.other_type, PACKET_POKER_TOURNEY_UNREGISTER)
                self.assertEquals(packet.code, PacketPokerTourneyUnregister.DOES_NOT_EXIST)
                count += 1
        self.assertEquals(count, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test41_tourneyUnregister(self):
        """Test for unregistering players from a tourney."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.tourneyUnregister, 0)
        return d
    # ------------------------------------------------------------------------
    def handSelectAll(self, (client, packet), id, whereStr = "" ):
        avatar = self.service.avatars[id]
        # Need more privs to do a HAND_SELECT_ALL
        oldPriv = avatar.user.privilege
        avatar.user.privilege = 32767
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerHandSelectAll(serial = client.getSerial(),
                                                          string = whereStr))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_HAND_LIST:
#             Unclear what this should be....
#                self.assertEquals(packet.count, ????)
                self.assertEquals(packet.start, 0)
                self.assertEquals(packet.hands, [])
                self.assertEquals(packet.total, 0)
                found = True
        self.assertEquals(found, True)
        avatar.user.privilege = oldPriv
        return (client, packet)
    # ------------------------------------------------------------------------
    def handSelectAllMissingPrivsMakesItFail(self, (client, packet), id):
        return self.pingThenExpectPrivilegeFailure((client, packet),
             PacketPokerHandSelectAll(serial = client.getSerial(),
                                      string = ""), id)
    # ------------------------------------------------------------------------
    def test42_handSelectAll(self):
        """Test sending hand select all packet."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.handSelectAll, 0)
        return d
    # ------------------------------------------------------------------------
    def test42_0_handSelectAll_MissingPrivsCauseFail(self):
        """Test failing hand select packet because it has only regular
        privs, no admin privs."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.handSelectAllMissingPrivsMakesItFail, 0)
        return d
    # ------------------------------------------------------------------------
    def handHistory(self, (client, packet), id, gameId ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerHandHistory(game_id = gameId, serial = client.getSerial() ))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_ERROR:
                found = True
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.game_id, 2)
                self.assertEquals(packet.message, "Hand %d was not found in history of player %d"
                                  % (packet.game_id, client.getSerial()))
                self.assertEquals(packet.other_type, PACKET_POKER_HAND_HISTORY)
                self.assertEquals(packet.code, PacketPokerHandHistory.NOT_FOUND)
        self.assertEquals(found, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test43_handHistory(self):
        """Test for hand history packet."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.sitTable, 0, 2)
        d.addCallback(self.readyToPlay, 0, 2)
        d.addCallback(self.handHistory, 0, 2)
        return d
    # ------------------------------------------------------------------------
    def loseConnection(self, (client, packet), gameId):
        table = self.service.getTable(gameId)
        avatar0 = self.service.avatars[0]
        avatar0.logout()
        table.observers.append(avatar0)
        avatar0.login((4, "user0", 32767))
        avatar0.queuePackets()
        count = 0
        for packet in avatar0.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_CARDS:
                count += 1
                self.assertEquals(packet.game_id, gameId)
            elif packet.type == PACKET_POKER_PLAYER_SELF:
                count += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.serial, 4)
            elif packet.type == PACKET_POKER_BLIND_REQUEST:
                count += 1
                self.assertEquals(packet.serial, 4)
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.amount, 2)
                self.assertEquals(packet.dead, 0)
                self.assertEquals(packet.state, "big")
        self.assertEquals(count >= 3, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test44_possibleObserverLoggedIn(self):
        def client1(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        def client2(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        gameId = 2
        dl = defer.DeferredList([client1(gameId),client2(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.dealTable, gameId)
        dl.addCallback(self.loseConnection, gameId)
        return dl
    # ------------------------------------------------------------------------
    def loseConnectionAnte(self, (client, packet), gameId):
        table = self.service.getTable(gameId)
        avatar0 = self.service.avatars[0]
        avatar0.logout()
        table.observers.append(avatar0)
        avatar0.login((4, "user0", 32767))
        avatar0.queuePackets()
        count = 0
        for packet in avatar0.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_CARDS:
                count += 1
                self.assertEquals(packet.game_id, gameId)
            elif packet.type == PACKET_POKER_PLAYER_SELF:
                count += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.serial, 4)
            elif packet.type == PACKET_POKER_ANTE_REQUEST:
                count += 1
                self.assertEquals(packet.serial, 4)
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.amount, 1)
        self.assertEquals(count >= 3, True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test45_possibleObserverLoggedInWithAnte(self):
        def client1(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table4', '10-20_100-2000000_ante-limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 100)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        def client2(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.sendExplain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table4', '10-20_100-2000000_ante-limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 100)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        gameId = 4
        dl = defer.DeferredList([client1(gameId),client2(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.dealTable, gameId)
        dl.addCallback(self.loseConnectionAnte, gameId)
        return dl
    # ------------------------------------------------------------------------
    def processingHand(self, (client, packet), id, gameId):
        avatar = self.service.avatars[id]

        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerProcessingHand(serial = client.getSerial(), game_id = gameId))
        count = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_ERROR:
                count += 1
                self.assertEquals(packet.other_type, PACKET_POKER_PROCESSING_HAND)
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.game_id, 4)
                self.assertEquals(packet.message, "no message")
                self.assertEquals(packet.code, 0)
            if packet.type == PACKET_ACK:
                count += 1
        self.assertEquals(count, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test46_processingHand(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 4, 'Table4', '10-20_100-2000000_ante-limit')
        d.addCallback(self.seatTable, 0, 4)
        d.addCallback(self.buyInTable, 0, 4, 100)
        d.addCallback(self.sitTable, 0, 4)
        d.addCallback(self.processingHand, 0, 4)
        d.addCallback(self.processingHand, 0, 4)
        return d
    # ------------------------------------------------------------------------
    def variousStartPackets(self, (client, packet), id, gameId ):
        # The tests in here changed with r4046, which corrected a bug in
        # the way PACKET_POKER_START was handled.
        avatar = self.service.avatars[id]

        avatar.queuePackets()
        log_history.reset()
        avatar.handlePacketLogic(PacketPokerStart(serial = client.getSerial(), game_id = gameId))
        self.assertEqual(log_history.search("tried to start a new game but is not the owner of the table"), True)
        # Coverage for when the server is shutting down

        avatar.service.shutting_down = True

        avatar.queuePackets()
        log_history.reset()
        avatar.handlePacketLogic(PacketPokerStart(serial = client.getSerial(), game_id = gameId))
        self.assertEqual(log_history.search("Not autodealing because server is shutting down"), True)

        # Coverage for the table owner is not the player, but it would
        # otherwise be a valid start
        avatar.service.shutting_down = False

        table = self.service.getTable(gameId)
        table.owner = 32767  # Something that should never actually be one of my serials

        avatar.resetPacketsQueue()
        avatar.queuePackets()
        log_history.reset()
        avatar.handlePacketLogic(PacketPokerStart(serial = client.getSerial(), game_id = gameId))
        self.assertEquals(log_history.search('tried to start a new game but is not the owner of the table'), True)
    # ------------------------------------------------------------------------
    def test47_startPackets(self):
        def client(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        gameId = 2
        table = self.service.getTable(gameId)
        table.autodeal = False
        dl = defer.DeferredList([client(gameId),client(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.variousStartPackets, 1, gameId)
        return dl
    # ------------------------------------------------------------------------
    def badSeatTable(self, (client, packet), id, gameId):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        seatNumber = id + 1
        def forceFalse(client, seat):
            return False
        originalFunction = table.seatPlayer
        table.seatPlayer = forceFalse

        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSeat(serial = client.getSerial(),
                                                seat = seatNumber, game_id = gameId))
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_SEAT:
                found += 1
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.seat, -1)
                self.assertEquals(packet.serial, client.getSerial())
        self.assertEquals(found, 1)
        table.seatPlayer = originalFunction
        return (client, packet)
    # ------------------------------------------------------------------------
    def test48_seatPackets(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.badSeatTable, 0, 2)
        return d
    # ------------------------------------------------------------------------
    def seatTableNoRole(self, (client, packet), id, gameId):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        seatNumber = id + 1

        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerSeat(serial = client.getSerial(),
                                                seat = seatNumber, game_id = gameId))
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_ERROR:
                found += 1
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.other_type, PACKET_POKER_SEAT)
                self.assertEquals(packet.code, PacketPokerSeat.ROLE_PLAY)
        self.assertEquals(found, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test48_1_seatPacketNoRole(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTableNoRole, 0, 2)
        return d
    # ------------------------------------------------------------------------
    def badBuyRebuyRequest(self, (client, packet), id, gameId):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        def forceFalse(self, amount):
            return False
        originalRebuy = table.rebuyPlayerRequest
        originalBuyin = table.buyInPlayer
        table.rebuyPlayerRequest = forceFalse
        table.buyInPlayer = forceFalse
        for sendPack in (
            PacketPokerBuyIn(serial = client.getSerial(), amount = 100, game_id = gameId),
            PacketPokerRebuy(serial = client.getSerial(), amount = 100, game_id = gameId)
        ):
            avatar.queuePackets()
            avatar.handlePacketLogic(sendPack)
            found = 0
            for packet in avatar.resetPacketsQueue():
                found += 1
                if packet.type == PACKET_POKER_ERROR:
                    self.assertEquals(packet.other_type, sendPack.type)
                    self.assertEquals(packet.game_id, gameId)
                    self.assertEquals(packet.serial, client.getSerial())
            self.assertEquals(found, 1)

        table.rebuyPlayerRequest = originalRebuy
        table.buyInPlayer = originalBuyin
        return (client, packet)
    # ------------------------------------------------------------------------
    def test49_badRebuy(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.badBuyRebuyRequest, 0, 2)
        d.addCallback(self.autoBlindAnte, 0, 2)
        return d
    # ------------------------------------------------------------------------
    def chatItUp(self, (client, packet), id, gameId, myMessage):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerChat(
            serial = client.getSerial(),
            game_id = gameId,
            message = myMessage
        ))
        found = 0
        for packet in avatar.resetPacketsQueue():
            found += 1
            if packet.type == PACKET_POKER_CHAT:
                self.assertEquals(packet.game_id, gameId)
                self.assertEqual(packet.message.find(myMessage) >= 0, True)
        self.assertEquals(found, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test50_chat(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.sitTable, 0, 2)
        d.addCallback(self.readyToPlay, 0, 2)
        d.addCallback(self.chatItUp, 0, 2, "I drink your milkshake!")
        return d
    # ------------------------------------------------------------------------
    def leaveTable(self, (client, packet), id, gameId):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerPlayerLeave(game_id = gameId, serial = client.getSerial()))
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                found += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEqual(packet.seat, 1)
        self.assertEquals(found, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test51_doLeave(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.sitTable, 0, 2)
        d.addCallback(self.readyToPlay, 0, 2)
        d.addCallback(self.leaveTable, 0, 2)
        return d
    # ------------------------------------------------------------------------
    # This test handles various requests that expect some sort of string
    # output as a return (and possibly a single packet).  This is similar to the
    # requestsWithWrongSerial() above, but in this case, we're using the
    # right serial and the game is just in the wrong state or somesuch.
    def variousPacketsWithStringOrSinglePacketReturn(self, (client, packet), avid, gameId):
        avatar = self.service.avatars[avid]
        packetTests = {
            'muck_accept': {
                'output': "muck: game state muck expected, found null",
                'packet': PacketPokerMuckAccept(game_id = gameId, serial = client.getSerial())
            },
            'muck_deny': {
                'output': "muck: game state muck expected, found null",
                'packet': PacketPokerMuckDeny(game_id = gameId, serial = client.getSerial())
            },
            'wait_blind': {
                'output': "player %d cannot pay blind while in state null" % (client.getSerial(),),
                'packet': PacketPokerWaitBigBlind(game_id = gameId, serial = client.getSerial())
            },
            'ante': {
                'output': "attempt to pay the ante of player %d" % client.getSerial(),
                'packet': PacketPokerAnte(game_id = gameId, amount = 5, serial = client.getSerial())
            },
            'lookcards': {
                'answer_type': PACKET_POKER_LOOK_CARDS,
                'packet': PacketPokerLookCards(game_id = gameId, serial = client.getSerial())
            },
            'fold': {
                'output': "attempt to fold for player %d" % client.getSerial(),
                'packet': PacketPokerFold(game_id = gameId, serial = client.getSerial())
            },
            'call': {
                'output': "attempt to call for player %d" % client.getSerial(),
                'packet': PacketPokerCall(game_id = gameId, serial = client.getSerial())
            },
            'raise': {
                'output': "attempt to raise for player %d" % client.getSerial(),
                'packet': PacketPokerRaise(game_id = gameId, amount = 0, serial = client.getSerial())
            },
            'check': {
                'output': "attempt to check for player %d" % client.getSerial(),
                'packet': PacketPokerCheck(game_id = gameId, serial = client.getSerial())
            },
        }
        # Next, we loop through all the serial-related bad pack list,
        # attempting to handle each one.  Also, catch any error packets
        # for those we expect to receive.
        for (_k,info) in packetTests.iteritems():
            log_history.reset()
            avatar.resetPacketsQueue()
            avatar.queuePackets()
            avatar.handlePacketLogic(info['packet'])
            if 'output' in info:
                self.assertEqual(log_history.search(info['output']), True, info['output'])
            found = False
            for packet in avatar.resetPacketsQueue():
                found = True
                self.assertEquals(packet.type, info['answer_type'])
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.serial, client.getSerial())
            self.assertEquals(found, 'answer_type' in info)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test52_variousPackets(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.sitTable, 0, 2)
        d.addCallback(self.readyToPlay, 0, 2)
        d.addCallback(self.variousPacketsWithStringOrSinglePacketReturn, 0, 2)
        return d
    # ------------------------------------------------------------------------
    def autoMuck(self, (client, packet), id, gameId, autoMuckValue ):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerAutoMuck(
            serial= client.getSerial(),
            game_id = gameId,
            auto_muck = autoMuckValue)
        )
        self.assertEquals(autoMuckValue, table.game.getPlayer(client.getSerial()).auto_muck)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test53_autoMuck(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.autoMuck, 0, 2, pokergame.AUTO_MUCK_LOSE)
        return d
    # ------------------------------------------------------------------------
    def tableQuit(self, (client, packet), id, gameId ):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTableQuit(serial= client.getSerial(),
                                                      game_id = gameId))
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                found += 1
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEqual(packet.seat, 1)
        self.assertEquals(found, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test54_doTableQuit(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.tableQuit, 0, 2)
        return d
    # ------------------------------------------------------------------------
    def joinTableForceFail(self, (client, packet), id, gameId, name, struct):
        avatar = self.service.avatars[id]

        table = self.service.getTable(gameId)
        originalJoin = table.joinPlayer
        table.joinPlayer = lambda avatar, reason="": False

        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTableJoin(serial = client.getSerial(), game_id = gameId))
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_ERROR:
                found += 1
                self.assertEquals(packet.serial, client.getSerial())
                self.assertEquals(packet.game_id, gameId)
                self.assertEquals(packet.other_type, PACKET_POKER_TABLE_JOIN)
                self.assertEquals(packet.code, PacketPokerTableJoin.GENERAL_FAILURE)
                self.failUnless(len(packet.message) > 0, "some message should be included")
        self.assertEquals(found, 1)

        return (client, packet)
    # ------------------------------------------------------------------------
    def test55_tableJoinWhenFails(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTableForceFail, 0, 2, 'Table2', '1-2_20-200_limit')
        return d
    # ------------------------------------------------------------------------
    def handReplayWithoutTable(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerHandReplay(serial= client.getSerial()))
        self.assertEqual(log_history.search("loadHand(%d) expected one row got 0" % client.getSerial()), True)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test56_handReplyNoTable(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.handReplayWithoutTable, 0)
        return d
    # ------------------------------------------------------------------------
    def fullQuit(self, (client, packet), id ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketQuit())
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                found += 1
                self.assertEquals(packet.serial, client.getSerial())
        self.assertEquals(found, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test57_doFullQuit(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.fullQuit, 0)
        return d
    # ------------------------------------------------------------------------
    def doLogoutSucceed(self, (client, packet), id):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketLogout())
        found = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                found += 1
                self.assertEquals(packet.serial, client.getSerial())
        self.assertEquals(found, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def doLogoutFail(self, (client, packet), id):
        client.sendPacket(PacketLogout())
        d = client.packetDeferred(True, PACKET_ERROR)
        def checkbadLogoutReturn( (client, packet) ):
            self.assertEquals(packet.code, PacketPokerGetPlayerInfo.NOT_LOGGED)
            self.assertEquals(packet.message, "Not logged in")
            self.assertEquals(packet.other_type, PACKET_LOGOUT)
        d.addCallback(checkbadLogoutReturn)
        return d
    # ------------------------------------------------------------------------
    def test58_packetLogoutSucceed(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnte, 0, 2)
        d.addCallback(self.doLogoutSucceed, 0)
        return d
    # ------------------------------------------------------------------------
    def test59_packetLogoutFailed(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.doLogoutFail, 0)
        return d
    # ------------------------------------------------------------------------
    def test60_handSelectAllWithWhere(self):
        """Test sending hand select all packet."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.handSelectAll, 0, "1 = 1")
        return d
    # ------------------------------------------------------------------------
    def createTableForceFail(self, (client, packet), id):
        avatar = self.service.avatars[id]

        def forceFalse(self, amount):
            return False
        originalCreate = self.service.createTable
        self.service.createTable = forceFalse

        avatar.queuePackets()
        avatar.user.privilege = avatar.user.ADMIN
        
        packets = avatar.handlePacket(PacketPokerTable(
            id = 1, seats  = 5,
            name = "A Testing Cash Table", variant = "holdem",
            betting_structure = '1-2_20-200_limit', player_timeout =  6,
            currency_serial = 0
        ))
        found = False
        for packet in packets:
            if packet.type == PACKET_ERROR:
                found = True
                self.assertEquals(packet.message, PacketPokerTable.REASON_TABLE_CREATE)
                self.assertEquals(packet.other_type, PACKET_POKER_TABLE)
        self.assertEquals(found, True)
        self.service.createTable = originalCreate
        return (client, packet)
    # ------------------------------------------------------------------------
    def test61_tableCreateFails(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.createTableForceFail, 0)
        return d
    # ------------------------------------------------------------------------
    def autoBlindAnteForceTourney(self, (client, packet), id, gameId ):
        avatar = self.service.avatars[id]

        table = self.service.getTable(gameId)
        oldIsTourney = table.game.isTournament
        def forceTrue():
            return True
        table.game.isTournament = forceTrue

        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerAutoBlindAnte(serial= client.getSerial(),
                                                        game_id = gameId))
        found = False
        for packet in avatar.resetPacketsQueue():
            found = True
        # in tourneys, the packet is ignored
        self.assertEquals(found, False)
        table.game.isTournament = oldIsTourney
        return (client, packet)
    # ------------------------------------------------------------------------
    def test62_ignoreAutoBlindAnteInTourney(self):
        """Make sure auto blind/ante setting is ignored when the game is a tourney"""
        # The sequence of how to get yourself seated in a cash game was
        # taken from the instructions at the top of pokerpackets.py
        # labelled "How to sit at a cash game table ?"
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.sendRolePlay)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d.addCallback(self.seatTable, 0, 2)
        d.addCallback(self.buyInTable, 0, 2, 20)
        d.addCallback(self.autoBlindAnteForceTourney, 0, 2)
        return d
    # -------------------------------------------------------------------------
    def joinTableWhenHandRunning(self, (client, packet), id, gameId, name, struct):
        avatar = self.service.avatars[id]
        table = self.service.getTable(gameId)
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerTableJoin(serial = client.getSerial(), game_id = gameId))
        found = 0
        packets = avatar.resetPacketsQueue()
        for packet in packets:
            if packet.type == PACKET_POKER_TABLE:
                found += 1
                self.assertEquals(packet.variant, 'holdem')
                self.assertEquals(packet.betting_structure, struct)
                self.assertEquals(packet.reason, PacketPokerTable.REASON_TABLE_JOIN)
                for (kk, vv) in avatar.tables.items():
                    self.assertEquals(vv.game.id, table.game.id)
                    self.assertEquals(vv.game.name, name)
                    self.assertEquals(vv.game.max_players, 10)
                    self.assertEquals(vv.game.variant, 'holdem')
                    self.assertEquals(vv.game.betting_structure, struct)
            elif packet.type == PACKET_POKER_BATCH_MODE:
                found += 1
                self.assertEquals(packet.serial, 0)
                self.assertEquals(packet.game_id, table.game.id)
            elif packet.type ==  PACKET_POKER_SEATS:
                found += 1
                self.assertEquals(packet.game_id, table.game.id)
            elif packet.type == PACKET_POKER_IN_GAME:
                found += 1
                self.assertEquals(packet.serial, 0)
                self.assertEquals(packet.players, [4, 5])
            elif packet.type ==  PACKET_POKER_BLIND:
                found += 1
                self.assertEquals(packet.serial, 5)
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.amount,  1)
            elif packet.type ==  PACKET_POKER_BLIND_REQUEST:
                found += 1
                self.assertEquals(packet.serial, 4)
                self.assertEquals(packet.game_id, table.game.id)
                self.assertEquals(packet.amount,  2)
                self.assertEquals(packet.state,  'big')
        self.assertEquals(found, 6)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test63_newObserver(self):
        """Test a third player joining the table and receiving packet playback"""
        # To cover a few lines in pokeravatar.join(), I needed a situation
        # where a third client joined while two were already playing a
        # hand.  This test does that.  Note it's the only test that uses
        # the third client.
        def client0(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        def client1(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            d.addCallback(self.autoBlindAnte, index, gameId)
            d.addCallback(self.sitTable, index, gameId)
            d.addCallback(self.readyToPlay, index, gameId)
            return d
        def client2(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            return d

        gameId = 2

        # set autodeal on false; we want to deal only on dealTable
        table = self.service.tables[gameId].autodeal = False

        dl = defer.DeferredList([client0(gameId), client1(gameId), client2(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.dealTable, gameId)
        dl.addCallback(self.joinTableWhenHandRunning, 2, gameId, 'Table2', '1-2_20-200_limit')
        return dl
    # ------------------------------------------------------------------------
    def tinyFunctions(self, (client, packet), id):
        avatar = self.service.avatars[id]
        self.assertEquals(avatar.getUrl(), "")
        self.assertEquals(avatar.getOutfit(), "")
    # ------------------------------------------------------------------------
    def test64_testTinyFunctions(self):
        """Test a few small functions that are not otherwise called"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.tinyFunctions, 0)
        return d
    # ------------------------------------------------------------------------
    def monitor(self, (client, packet)):
        avatar = self.service.avatars[0]
        avatar.queuePackets()
        self.assertEquals(0, len(self.service.monitors))
        avatar.handlePacketLogic(PacketPokerMonitor())
        self.assertEquals(1, len(self.service.monitors))
        return (client, packet)
    # ------------------------------------------------------------------------
    def test65_monitor(self):
        """Test monitor request"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.monitor)
        return d
    # ------------------------------------------------------------------------
    def tourneyManager(self, (client, packet), id, tourney_serial ):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerGetTourneyManager(tourney_serial = tourney_serial))
        for packet in avatar.resetPacketsQueue():
            count = 0
            if packet.type == PACKET_POKER_TOURNEY_MANAGER:
                self.assertEquals(packet.tourney_serial, 1)
                count += 1
            self.assertEquals(count, 1)
        return (client, packet)
    # ------------------------------------------------------------------------
    def test66_tourneyPlayerList(self):
        """Test for listing players in a tourney."""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.tourneyManager, 0, 1)
        return d
    # ------------------------------------------------------------------------
    def test68_handlePacketDefer(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        def handlePacketDefer(x):
            avatar = self.service.avatars[0]
            #
            # returns nothing
            #
            r = avatar.handlePacketDefer(PacketPing())
            self.assertEqual([], r)
            #
            # returns a deferred that returns a packet
            #
            d1 = defer.Deferred()
            def returnDefer1(packet):
                avatar.sendPacket(d1)
            avatar.handlePacketLogic = returnDefer1
            r = avatar.handlePacketDefer(PacketPing())
            self.assertEquals(True, isinstance(r, defer.Deferred))
            def checkDefer(packets):
                self.assertEquals(type(packets), ListType)
                self.assertEquals(PACKET_PING, packets[0].type)
            d1.addCallback(checkDefer)
            d1.callback(PacketPing())
            #
            # returns a list of packets
            #
            d2 = defer.Deferred()
            def returnDefer2(packet):
                avatar.sendPacket(d2)
            avatar.handlePacketLogic = returnDefer2
            r = avatar.handlePacketDefer(PacketPing())
            self.assertEquals(True, isinstance(r, defer.Deferred))
            d2.addCallback(checkDefer)
            d2.callback([PacketPing()])
        d.addCallback(handlePacketDefer)
        return d
    
    # ------------------------------------------------------------------------
    def getPlayerPlaces(self, (client, packet), id, name):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerGetPlayerPlaces(serial= client.getSerial()))
        packets = avatar.resetPacketsQueue()
        self.assertEquals(1, len(packets))
        packet = packets[0]
        self.assertEquals(PACKET_POKER_PLAYER_PLACES, packet.type)
        self.assertEquals([2], packet.tables)
        return (client, packet)

    # ------------------------------------------------------------------------
    def getPlayerPlacesByName(self, (client, packet), id, name):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerGetPlayerPlaces(name = name))
        packets = avatar.resetPacketsQueue()
        self.assertEquals(1, len(packets))
        packet = packets[0]
        self.assertEquals(PACKET_POKER_PLAYER_PLACES, packet.type)
        self.assertEquals([2], packet.tables)
        return (client, packet)

    def getPlayerPlacesNone(self, (client, packet), id, name):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerGetPlayerPlaces(name = name))
        packets = avatar.resetPacketsQueue()
        self.assertEquals(1, len(packets))
        packet = packets[0]
        self.assertEquals(PACKET_POKER_PLAYER_PLACES, packet.type)
        self.assertEquals([], packet.tables)
        return (client, packet)

    def getPlayerPlacesFailed(self, (client, packet), id, name):
        avatar = self.service.avatars[id]
        avatar.queuePackets()
        avatar.handlePacketLogic(PacketPokerGetPlayerPlaces(name = name))
        packets = avatar.resetPacketsQueue()
        self.assertEquals(1, len(packets))
        packet = packets[0]
        self.assertEquals(PACKET_ERROR, packet.type)
        self.assertEquals(PACKET_POKER_PLAYER_PLACES, packet.other_type)
        return (client, packet)
    
    # ------------------------------------------------------------------------
    def test69_getPlayerPlaces(self):
        """Test lookup of where the player is playing."""
        self.createClients(2)
        d1 = self.client_factory[0].established_deferred
        d1.addCallback(self.sendExplain)
        d1.addCallback(self.sendRolePlay)
        d1.addCallback(self.login, 0)
        d1.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        d1.addCallback(self.seatTable, 0, 2)
        d1.addCallback(self.getPlayerPlaces, 0, 1)
        d1.addCallback(self.getPlayerPlacesByName, 0, 'user0')
        d1.addCallback(self.getPlayerPlacesFailed, 0, 'user999')

        d2 = self.client_factory[1].established_deferred
        d2.addCallback(self.sendExplain)
        d2.addCallback(self.sendRolePlay)
        d2.addCallback(self.login, 1)
        d2.addCallback(self.getPlayerPlacesNone, 1, 'user1')        
        return defer.DeferredList([d1, d2]) # the order in which d1 & d2 is run does not matter 

    # -------------------------------------------------------------------------
    def setLocale(self, (client, packet), myLocale, avid = 0, expectSucceed=True):

        avatar = self.service.avatars[avid]
        avatar.queuePackets()
        log_history.reset()
        avatar.handlePacketLogic(PacketPokerSetLocale(serial = client.getSerial(), locale = myLocale))
        foundCount = 0
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_ACK:
                if expectSucceed:
                    # Save the locale we've set so other tests can know if
                    # they need it.
                    self.avatarLocales[avid] = myLocale
                    foundCount += 1
                else:
                    foundCount -= 1
            elif packet.type == PACKET_POKER_ERROR:
                if expectSucceed:
                    foundCount -= 1
                else:
                    self.assertEquals(packet.serial, client.getSerial())
                    self.assertEquals(packet.other_type, PACKET_POKER_SET_LOCALE)
                    foundCount += 1
                    self.failUnless(log_history.search("Locale, 'Klingon_Kronos.UTF-8' not available. Klingon_Kronos.UTF-8 "
                        "must not have been provide via <language/> tag in settings, or errors occured during loading."))
        self.assertEquals(foundCount, 1)
        return (client, packet)
    # -------------------------------------------------------------------------
    def test71_setLocaleAlwaysValid(self):
        """Tests setting of roles"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.setLocale, "en_US", 0)
        d.addCallback(self.quit)
        return d
    # -------------------------------------------------------------------------
    def test72_setLocaleAlwaysFail(self):
        """Tests setting of roles"""
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.setLocale, "Klingon_Kronos", 0, False)
        d.addCallback(self.quit)
        return d
    # ------------------------------------------------------------------------
    def playerTimesoutAndThenLooksAtQueuedPackets(self, (client, packet), gameId):
        avatars = self.service.avatars
        clients = {}
        table = self.service.getTable(gameId)
        for ii in [ 0, 1, 2]:
            clients[ii] = self.service.avatar_collection.get(avatars[ii].getSerial())[0]
            avatars[ii].resetPacketsQueue()
            self.sitTable((clients[ii], None), ii, gameId)
        for ii in [ 0, 1, 2]:
            avatars[ii].resetPacketsQueue()
            self.autoBlindAnte( (clients[ii], None), ii, gameId)
        for ii in [ 0 ,1, 2]:
            avatars[ii].resetPacketsQueue()
            self.readyToPlay( (clients[ii], None), ii, gameId)

        table.autodeal = True
        self.dealTable((client, packet), gameId)
        def findBigBlind(id):
            bbPacket = None
            packets = []
            for ii in [ 1, 2]: packets.extend(avatars[ii].resetPacketsQueue())
            while bbPacket == None:
                for packet in packets:
                    if packet.type == PACKET_POKER_BLIND and packet.serial == avatars[id].getSerial():
                        self.assertEquals(packet.amount, 2)
                        self.assertEquals(packet.game_id, gameId)
                        bbPacket = packet
                        break
            return bbPacket

        self.assertNotEquals(findBigBlind(2), None)

        # Player 0 fails to act in time
        table.playerTimeoutTimer(clients[0].getSerial())

        avatars[1].handlePacketLogic(PacketPokerFold(serial = clients[1].getSerial(),
                                                     game_id = gameId))
        for ii in [ 0, 1, 2]:
            avatars[ii].resetPacketsQueue()
            avatars[ii].queuePackets()
        handSkip = 0
        while handSkip < 5:
            handSkip += 1
            # Player 1 folds, giving this pot to Player 2
            self.dealTable((client, packet), gameId)
            self.assertNotEquals(findBigBlind(1), None)
            avatars[2].handlePacketLogic(PacketPokerFold(serial = clients[2].getSerial(),
                                                         game_id = gameId))
            self.dealTable((client, packet), gameId)
            self.assertNotEquals(findBigBlind(2), None)
            avatars[1].handlePacketLogic(PacketPokerFold(serial = clients[1].getSerial(),
                                                         game_id = gameId))

        # After this loop, a number of heads up hands have been played.
        # Despite the fact that we set avatars[0] to queue packets before
        # the loop started, we find that only the packets from the last
        # hand are present.
        # After this loop, a number of heads up hands have been played.
        # Despite the fact that we set avatars[0] to queue packets before
        # the loop started, we find that only the packets from the last
        # hand are present.
        foldCount = 0
        rakeCount = 0
        winCount = 0
        for pack in avatars[0]._packets_queue:
            self.assertEquals(pack.game_id, gameId)
            if pack.type == PACKET_POKER_FOLD:
                foldCount += 1
            elif pack.type == PACKET_POKER_RAKE:
                self.assertEquals(pack.value, 10)
                rakeCount += 1
            elif pack.type == PACKET_POKER_WIN:
                self.assertEquals(pack.serial, 0)
                winCount += 1
        self.assertEquals([ winCount, rakeCount, foldCount ], [ 10, 0, 10])
        self.assertEquals(winCount, 10)
        return (clients[2], None)
    # ------------------------------------------------------------------------
    def test73_playerTimeoutAndThenViewsQueuedPackets(self):
        """Test when a player was in a hand, reconnects after other hands
        have been played, and expects certain packet playback  packets."""
        def client(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            return d
        gameId = 2
        table = self.service.getTable(gameId)
        table.autodeal = False
        dl = defer.DeferredList([client(gameId), client(gameId), client(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.playerTimesoutAndThenLooksAtQueuedPackets, gameId)
        return dl

    # ------------------------------------------------------------------------
    def playWhileObserverGrows(self, (client, packet), gameId):
        avatars = self.service.avatars
        clients = {}
        table = self.service.getTable(gameId)
        for ii in [ 0, 1]:
            clients[ii] = self.service.avatar_collection.get(avatars[ii].getSerial())[0]
            avatars[ii].resetPacketsQueue()
            self.sitTable((clients[ii], None), ii, gameId)
        for ii in [ 0, 1]:
            avatars[ii].resetPacketsQueue()
            self.autoBlindAnte( (clients[ii], None), ii, gameId)
        for ii in [ 0 ,1]:
            avatars[ii].resetPacketsQueue()
            self.readyToPlay( (clients[ii], None), ii, gameId)

        def findBigBlind(id):
            bbPacket = None
            packets = []
            for ii in [ 0, 1]: packets.extend(avatars[ii].resetPacketsQueue())
            while bbPacket == None:
                for packet in packets:
                    if packet.type == PACKET_POKER_BLIND and packet.serial == avatars[id].getSerial():
                        self.assertEquals(packet.amount, 2)
                        self.assertEquals(packet.game_id, gameId)
                        bbPacket = packet
                        break
            return bbPacket


        for ii in [ 0, 1, 2]:
            clients[ii] = self.service.avatar_collection.get(avatars[ii].getSerial())[0]
            avatars[ii].resetPacketsQueue()

        table.autodeal = True
        handSkip = 0
        while handSkip < 5:
            handSkip += 1
            self.dealTable((client, packet), gameId)
            self.assertNotEquals(findBigBlind(0), None)
            avatars[1].handlePacketLogic(PacketPokerFold(serial = clients[1].getSerial(),
                                                         game_id = gameId))
            self.dealTable((client, packet), gameId)
            self.assertNotEquals(findBigBlind(1), None)
            avatars[0].handlePacketLogic(PacketPokerFold(serial = clients[0].getSerial(),
                                                         game_id = gameId))

        # After this loop, a number of heads up hands have been played.
        # Despite the fact that we set avatars[0] to queue packets before
        # the loop started, we find that only the packets from the last
        # hand are present.
        foldCount = 0
        rakeCount = 0
        winCount = 0
        for pack in avatars[2]._packets_queue:
            self.assertEquals(pack.game_id, gameId)
            if pack.type == PACKET_POKER_FOLD:
                foldCount += 1
            elif pack.type == PACKET_POKER_RAKE:
                self.assertEquals(pack.value, 10)
                rakeCount += 1
            elif pack.type == PACKET_POKER_WIN:
                self.assertEquals(pack.serial, 0)
                winCount += 1
        self.assertEquals([ winCount, rakeCount, foldCount ], [ 10, 0, 10])
        self.assertEquals(winCount, 10)
        return (client, None)
    # ------------------------------------------------------------------------
    def test74_tooManyPacketsGrowOnObserver(self):
        """Test when a player merely observes, the packet queue grows and grows"""
        def client(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            return d
        gameId = 2
        table = self.service.getTable(gameId)
        table.autodeal = False
        dl = defer.DeferredList([client(gameId), client(gameId), client(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.playWhileObserverGrows, gameId)
        return dl
    # ------------------------------------------------------------------------
    def playerSitsBrieflyThenSitsOut(self, (client, packet), gameId):
        avatars = self.service.avatars
        clients = {}
        table = self.service.getTable(gameId)
        for ii in [ 0, 1, 2]:
            clients[ii] = self.service.avatar_collection.get(avatars[ii].getSerial())[0]
            avatars[ii].resetPacketsQueue()
            self.sitTable((clients[ii], None), ii, gameId)
        for ii in [ 0, 1, 2]:
            avatars[ii].resetPacketsQueue()
            self.autoBlindAnte( (clients[ii], None), ii, gameId)
        for ii in [ 0 ,1, 2]:
            avatars[ii].resetPacketsQueue()
            self.readyToPlay( (clients[ii], None), ii, gameId)

        self.sitOut((clients[ii], None), 2, gameId)

        def findBigBlind(id):
            bbPacket = None
            packets = []
            for ii in [ 0, 1]: packets.extend(avatars[ii].resetPacketsQueue())
            while bbPacket == None:
                for packet in packets:
                    if packet.type == PACKET_POKER_BLIND and packet.serial == avatars[id].getSerial():
                        self.assertEquals(packet.amount, 2)
                        self.assertEquals(packet.game_id, gameId)
                        bbPacket = packet
                        break
            return bbPacket

        for ii in [ 0, 1, 2]:
            clients[ii] = self.service.avatar_collection.get(avatars[ii].getSerial())[0]
            avatars[ii].resetPacketsQueue()

        table.autodeal = True
        handSkip = 0
        while handSkip < 5:
            handSkip += 1
            self.dealTable((client, packet), gameId)
            self.assertNotEquals(findBigBlind(0), None)
            avatars[1].handlePacketLogic(PacketPokerFold(serial = clients[1].getSerial(),
                                                         game_id = gameId))
            self.dealTable((client, packet), gameId)
            self.assertNotEquals(findBigBlind(1), None)
            avatars[0].handlePacketLogic(PacketPokerFold(serial = clients[0].getSerial(),
                                                         game_id = gameId))

        # After this loop, a number of heads up hands have been played.
        # Despite the fact that we set avatars[0] to queue packets before
        # the loop started, we find that only the packets from the last
        # hand are present.
        foldCount = 0
        rakeCount = 0
        winCount = 0
        for pack in avatars[2]._packets_queue:
            self.assertEquals(pack.game_id, gameId)
            if pack.type == PACKET_POKER_FOLD:
                foldCount += 1
            elif pack.type == PACKET_POKER_RAKE:
                self.assertEquals(pack.value, 10)
                rakeCount += 1
            elif pack.type == PACKET_POKER_WIN:
                self.assertEquals(pack.serial, 0)
                winCount += 1
        self.assertEquals([ winCount, rakeCount, foldCount ], [ 10, 0, 10])
        self.assertEquals(winCount, 10)
        return (clients[2], None)
    # ------------------------------------------------------------------------
    def test75_playerSitsBrieflyThenOut(self):
        """Test when a player sits in briefly, then sits out.  Packet queue grows?"""
        def client(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            return d
        gameId = 2
        table = self.service.getTable(gameId)
        table.autodeal = False
        dl = defer.DeferredList([client(gameId), client(gameId), client(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.playerSitsBrieflyThenSitsOut, gameId)
        return dl
    # ------------------------------------------------------------------------
    def forceObserverDisconnectPacketQueue(self, (client, packet), gameId):
        avatars = self.service.avatars
        clients = {}
        table = self.service.getTable(gameId)
        for ii in [ 0, 1]:
            clients[ii] = self.service.avatar_collection.get(avatars[ii].getSerial())[0]
            avatars[ii].resetPacketsQueue()
            self.sitTable((clients[ii], None), ii, gameId)
        for ii in [ 0, 1]:
            avatars[ii].resetPacketsQueue()
            self.autoBlindAnte( (clients[ii], None), ii, gameId)
        for ii in [ 0 ,1]:
            avatars[ii].resetPacketsQueue()
            self.readyToPlay( (clients[ii], None), ii, gameId)

        def findBigBlind(id, expectedCount):
            bbPacket = None
            packets = []
            for ii in [0, 1]:
                self.assertEquals(expectedCount, len(avatars[ii]._packets_queue))
                if expectedCount >= 15:
                    self.assertTrue(log_history.search("user %d has more than 15 packets queued; will force-disconnect when 21 are queued" % clients[ii].getSerial()))
                packets.extend(avatars[ii].resetPacketsQueue())
            while bbPacket == None:
                for packet in packets:
                    if packet.type == PACKET_POKER_BLIND and packet.serial == avatars[id].getSerial():
                        self.assertEquals(packet.amount, 2)
                        self.assertEquals(packet.game_id, gameId)
                        bbPacket = packet
                        break
            return bbPacket

        for ii in [ 0, 1, 2]:
            clients[ii] = self.service.avatar_collection.get(avatars[ii].getSerial())[0]
            avatars[ii].resetPacketsQueue()

        table.autodeal = True
        expectedCount = 15

        log_history.reset()
        self.dealTable((client, packet), gameId)
        self.assertNotEquals(findBigBlind(0, expectedCount), None)
        avatars[1].handlePacketLogic(PacketPokerFold(serial = clients[1].getSerial(), game_id = gameId))
        
        # we should get the warning on the observer
        self.assertTrue(log_history.search("user %d has more than 15 packets queued; will force-disconnect when 21 are queued"  % clients[2].getSerial()))
        expectedCount = 22
        log_history.reset()
        self.dealTable((client, packet), gameId)
        self.assertNotEquals(findBigBlind(1, expectedCount), None)
        avatars[0].handlePacketLogic(PacketPokerFold(serial = clients[0].getSerial(), game_id = gameId))
        # This is the point where observer has been disconnected.  We need
        # to create a callback, I picked this function because it appears
        # to be the pure bottom of the chain of items that are called when
        # self.service.destroyAvatar() is called.

        #  Note that we are returning checkLogoutDeferred which should
        #  generate reactor 120 second error if checkLogout is never
        #  called.
        realLogout = avatars[2].user.logout
        self.service.verbose = 6
        log_history.reset()
        checkLogoutDeferred = defer.Deferred()
        # The array can't have a closure around it, it appears.... I did
        # this to save time rather than resarching closures around arrays
        # in Python. :)
        av0 = avatars[0]
        av1 = avatars[1]
        av2 = avatars[2]
        def checkLogout():
            self.assertEquals(log_history.search('connection lost for %s/%d' % (av2.getName(), av2.getSerial())), True)
            self.assertEquals(
                log_history.search('removing player %d from game' % (av2.getSerial(),)), 
                True
            )
            self.assertTrue(len(av2._packets_queue) > 21)
            for pack in av0._packets_queue[-1:], av0._packets_queue[-1:]:
                pack = pack[0]
                self.assertEquals(pack.type, PACKET_POKER_PLAYER_LEAVE)
                self.assertEquals(pack.serial, av2.getSerial())
                self.assertEquals(pack.game_id, gameId)
            self.assertFalse(av2 in self.service.avatars)
            self.assertFalse(av2 in self.service.monitors)
            self.assertEquals([], self.service.avatar_collection.get(av2.user.serial))
            realLogout()
            checkLogoutDeferred.callback(True)
        av2.user.logout = checkLogout
        return checkLogoutDeferred
    # ------------------------------------------------------------------------
    def test76_forceObserverDisconnectPacketQueue(self):
        """Tests packet queue growth and cutoff by setting max length small"""
        def client(gameId):
            index = self.createClient()
            d = self.client_factory[index].established_deferred
            d.addCallback(self.setupCallbackChain)
            d.addCallback(self.sendRolePlay)
            d.addCallback(self.login, index)
            d.addCallback(self.joinTable, index, gameId, 'Table2', '1-2_20-200_limit')
            d.addCallback(self.seatTable, index, gameId)
            d.addCallback(self.buyInTable, index, gameId, 20)
            return d
        gameId = 2
        saveClientQueueMax = self.service.client_queued_packet_max
        self.service.client_queued_packet_max = 21
        table = self.service.getTable(gameId)
        table.autodeal = False
        dl = defer.DeferredList([client(gameId), client(gameId), client(gameId)])
        dl.addCallback(fixIt)
        dl.addCallback(self.forceObserverDisconnectPacketQueue, gameId)
        def resetQueueMax(d, saveClientQueueMax):
            self.service.client_queued_packet_max = saveClientQueueMax
            return d
        dl.addCallback(resetQueueMax, saveClientQueueMax)
        return dl
    # ------------------------------------------------------------------------
    def tourneyCreate(self, (client, packet), id, otherid):
        avatar = self.service.avatars[id]
        avatar.user.privilege = avatar.user.ADMIN
        avatar.queuePackets()
        another_player = self.service.avatars[otherid].user.serial
        avatar.handlePacketLogic(PacketPokerCreateTourney(
            serial = client.getSerial(),
            buy_in = 1,
            players = [another_player],
            players_quota = 2,
            currency_serial = 1,
        ))
        found = False
        for packet in avatar.resetPacketsQueue():
            if packet.type == PACKET_POKER_TOURNEY:
                found = True
        self.assertEquals(found, True)
        return (client, packet)

    # ------------------------------------------------------------------------
    def test80_tourneyCreate(self):
        """Test user created tournament."""
        self.createClients(2)
        d2 = self.client_factory[1].established_deferred
        d2.addCallback(self.sendExplain)
        d2.addCallback(self.login, 1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        d.addCallback(self.tourneyCreate, 0, 1)
        return d

    # ------------------------------------------------------------------------
    def test81_distributePacket(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleDistributedPacket(x):
            avatar = self.service.avatars[0]
            self.service.packet2resthost = lambda packet: (('host', 11111, '/PATH'), 2)
            getOrCreateRestClient = avatar.getOrCreateRestClient
            d = defer.Deferred()
            def getOrCreateRestClientMockup(resthost, game_id):
                client = getOrCreateRestClient(resthost, game_id)
                client.sendPacket = lambda packet, data: d
                return client
            avatar.getOrCreateRestClient = getOrCreateRestClientMockup
            r = avatar.handleDistributedPacket(None, PacketPing(), '{ "type": "PacketPing" }')
            r.addCallback(lambda packets: self.assertEquals(['foo'], packets))
            r.addCallback(lambda arg: self.assertEquals(True, 2 in avatar.game_id2rest_client))
            d.callback(['foo'])
            return d
        d.addCallback(handleDistributedPacket)
        return d
    # ------------------------------------------------------------------------
    def test82_distributePacketNoMoreActiveTable(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = 0.1
        def handleDistributedPacket(x):
            avatar = self.service.avatars[0]
            self.service.packet2resthost = lambda packet: (('host', 11111, '/PATH'), 2)
            getOrCreateRestClient = avatar.getOrCreateRestClient
            clients = {}
            d = defer.Deferred()
            def getOrCreateRestClientMockup(resthost, game_id):
                clients[game_id] = getOrCreateRestClient(resthost, game_id)
                clients[game_id].sendPacket = lambda packet, data: d
                return clients[game_id]
            avatar.getOrCreateRestClient = getOrCreateRestClientMockup
            def clearActiveTable(arg):
                avatar.tables = {}
                return arg
            d.addCallback(clearActiveTable)
            r = avatar.handleDistributedPacket(None, PacketPing(), '{ "type": "PacketPing" }')
            r.addCallback(lambda packets: self.assertEquals(['foo'], packets))
            r.addCallback(lambda arg: self.assertEquals({}, avatar.game_id2rest_client))
            r.addCallback(lambda arg: self.assertEquals(None, clients[2].timer))
            def f(x): PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = -1
            r.addCallback(f)
            d.callback(['foo'])
            return d
        d.addCallback(handleDistributedPacket)
        return d
    # ------------------------------------------------------------------------
    def test82_1_distributePacketNoMoreActiveGame(self): # FIXME
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)                
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = 0.1
        def handleDistributedPacket(x):
            avatar = self.service.avatars[0]
            self.service.packet2resthost = lambda packet: (('host', 11111, '/PATH'), 2)
            getOrCreateRestClient = avatar.getOrCreateRestClient
            clients = {}
            d = defer.Deferred()
            def getOrCreateRestClientMockup(resthost, game_id):
                clients[game_id] = getOrCreateRestClient(resthost, game_id)
                clients[game_id].sendPacket = lambda packet, data: d
                return clients[game_id]
            avatar.getOrCreateRestClient = getOrCreateRestClientMockup
            def clearActiveTable(arg):
                avatar.tables = {}
                avatar.explain.games.games = {}
                return arg
            d.addCallback(clearActiveTable)
            r = avatar.handleDistributedPacket(None, PacketPing(), '{ "type": "PacketPing" }')
            r.addCallback(lambda packets: self.assertEquals([PACKET_POKER_STATE_INFORMATION, PACKET_PING], [p.type for p in packets]))
            r.addCallback(lambda arg: self.assertEquals({}, avatar.game_id2rest_client))
            r.addCallback(lambda arg: self.assertEquals(None, clients[2].timer))
            def f(x): PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = -1
            r.addCallback(f)
            d.callback([PacketPing()])
            return d
        d.addCallback(handleDistributedPacket)
        return d
    # ------------------------------------------------------------------------
    def test82_2_distributePacketDisconnect(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)                
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = 0.1
        def handleDistributedPacket(x):
            avatar = self.service.avatars[0]
            self.service.packet2resthost = lambda packet: (('host', 11111, '/PATH'), 2)
            getOrCreateRestClient = avatar.getOrCreateRestClient
            clients = {}
            d = defer.Deferred()
            def getOrCreateRestClientMockup(resthost, game_id):
                clients[game_id] = getOrCreateRestClient(resthost, game_id)
                clients[game_id].sendPacketData = lambda data: d
                clients[game_id].pendingLongPoll = True
                return clients[game_id]
            avatar.getOrCreateRestClient = getOrCreateRestClientMockup
            def disconnectAvatar(arg):
                avatar.connectionLost('reason')
                return arg
            d.addCallback(disconnectAvatar)
            r = avatar.handleDistributedPacket(None, PacketPing(), '{ "type": "PacketPing" }')
            r.addCallback(lambda packets: self.assertEquals(PACKET_PING, packets[0].type))
            r.addCallback(lambda arg: self.assertEquals({}, avatar.game_id2rest_client))
            r.addCallback(lambda arg: self.assertEquals(None, clients[2].timer))
            def f(x): PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = -1
            r.addCallback(f)
            d.callback('[{ "type": "PacketPing" }]')
            return d
        d.addCallback(handleDistributedPacket)
        return d
    # ------------------------------------------------------------------------
    def test83_distributePacketNoGameId(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = 0.1
        def handleDistributedPacket(x):
            avatar = self.service.avatars[0]
            self.service.packet2resthost = lambda packet: (('host', 11111, '/PATH'), None)
            getOrCreateRestClient = avatar.getOrCreateRestClient
            d = defer.Deferred()
            def getOrCreateRestClientMockup(resthost, game_id):
                client = getOrCreateRestClient(resthost, game_id)
                self.assertEquals(None, client.longPollCallback)
                self.assertEquals(-1, client.longPollFrequency)
                client.sendPacket = lambda packet, data: d
                return client
            avatar.getOrCreateRestClient = getOrCreateRestClientMockup
            r = avatar.handleDistributedPacket(None, PacketPing(), '{ "type": "PacketPing" }')
            r.addCallback(lambda packets: self.assertEquals(['foo'], packets))
            r.addCallback(lambda arg: self.assertEquals({}, avatar.game_id2rest_client))
            d.callback(['foo'])
            return d
        d.addCallback(handleDistributedPacket)
        return d
    # ------------------------------------------------------------------------
    def test84_distributePacketNoRestHost(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleDistributedPacket(x):
            avatar = self.service.avatars[0]
            self.service.packet2resthost = lambda packet: (None, None)
            r = avatar.handleDistributedPacket(None, PacketPing(), '{ "type": "PacketPing" }')
            self.assertEquals([], r)
        d.addCallback(handleDistributedPacket)
        return d
    # ------------------------------------------------------------------------
    def test85_longPoll(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleLongPoll(x):
            avatar = self.service.avatars[0]
            uid = 'ZUID'
            auth = 'ZAUTH'
            avatar.setDistributedArgs(uid, auth)
            client = avatar.getOrCreateRestClient(('host', 11111, 'path'), 2)
            self.failUnlessSubstring(uid, client.path)
            self.failUnlessSubstring(auth, client.path)
            avatar.noqueuePackets()
            d = avatar.handlePacketDefer(PacketPokerLongPoll())
            self.assertEquals(True, avatar._queue_packets)
            self.assertEquals(d, avatar._longpoll_deferred)
            self.assertEquals(False, avatar._block_longpoll_deferred)
            avatar._longpoll_deferred.addCallback(lambda packets: self.assertEquals(PACKET_PING, packets[0].type))
            client.longPollCallback([PacketPing()])
            self.assertEquals(False, avatar.longPollTimer.active())
            return d
        d.addCallback(handleLongPoll)
        return d
    # ------------------------------------------------------------------------
    def test85_1_longPollTimeout(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleLongPoll(x):
            avatar = self.service.avatars[0]
            uid = 'ZUID'
            auth = 'ZAUTH'
            avatar.setDistributedArgs(uid, auth)
            client = avatar.getOrCreateRestClient(('host', 11111, 'path'), 2)
            client.sendPacket = lambda packet, data: defer.Deferred()
            self.failUnlessSubstring(uid, client.path)
            self.failUnlessSubstring(auth, client.path)
            d = avatar.handlePacketDefer(PacketPokerLongPoll())
            self.assertEquals(d, avatar._longpoll_deferred)
            self.assertEquals(False, avatar._block_longpoll_deferred)
            self.assertEquals(True, avatar.longPollTimer.active())
            avatar._packets_queue = ['foo']
            avatar._longpoll_deferred.addCallback(self.assertEquals, ['foo'])
            return d
        d.addCallback(handleLongPoll)
        return d
    # ------------------------------------------------------------------------
    def test85_2_longPollCallback(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleLongPoll(x):
            avatar = self.service.avatars[0]
            uid = 'ZUID'
            auth = 'ZAUTH'
            avatar.setDistributedArgs(uid, auth)
            client = avatar.getOrCreateRestClient(('host', 11111, 'path'), 2)
            client.longPollCallback([PacketPing()])   
            self.assertEquals(1, len(avatar._packets_queue))
        d.addCallback(handleLongPoll)
        return d
    # ------------------------------------------------------------------------
    def test86_longPollReturn(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleLongPollReturn(x):
            avatar = self.service.avatars[0]
            d = avatar.handlePacketDefer(PacketPokerLongPoll())
            avatar._packets_queue = ['foo']
            d.addCallback(self.assertEquals, ['foo'])
            avatar.handlePacketDefer(PacketPokerLongPollReturn())
            self.assertEquals(False, avatar.longPollTimer.active())
            return d
        d.addCallback(handleLongPollReturn)
        return d
    # ------------------------------------------------------------------------
    def test86_2_longPollReturnFlushNextLongPoll(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleLongPollReturn(x):
            avatar = self.service.avatars[0]
            avatar.handlePacketDefer(PacketPokerLongPollReturn())
            self.assertEquals(True, avatar._flush_next_longpoll)
            d = avatar.handlePacketDefer(PacketPokerLongPoll())
            self.assertEquals(None, avatar._longpoll_deferred)
            self.assertEquals(False, avatar._flush_next_longpoll)
            return d
        d.addCallback(handleLongPollReturn)
        return d
    # ------------------------------------------------------------------------
    def test86_3_longPollReturnEmpty(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleLongPollReturn(x):
            avatar = self.service.avatars[0]
            avatar._packets_queue = ['foo']
            packets = avatar.handlePacketDefer(PacketPokerLongPollReturn())
            self.assertEquals([], packets)
        d.addCallback(handleLongPollReturn)
        return d
    # ------------------------------------------------------------------------
    def test87_flushLongPollDeferred(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.setupCallbackChain)
        d.addCallback(self.login, 0)
        d.addCallback(self.joinTable, 0, 2, 'Table2', '1-2_20-200_limit')
        def handleLongPoll(x):
            avatar = self.service.avatars[0]
            avatar._packets_queue = ['foo']
            d = avatar.handlePacketDefer(PacketPokerLongPoll())
            d.addCallback(self.assertEquals, ['foo'])
            self.assertNotEquals(None, d)
            return d
        d.addCallback(handleLongPoll)
        return d
    # ------------------------------------------------------------------------
    def test88_avatar_with_same_login(self):
        _seatPlayer = self.service.seatPlayer
        self.service.seatPlayer = lambda service,*args,**kw: True
        a1 = self.service.createAvatar()
        a1.relogin(1)
        a1.queuePackets()
        a1.handlePacketLogic(PacketPokerTableJoin(serial = 1, game_id = 2))
        a1.handlePacketLogic(PacketPokerSetRole(serial = 1, roles = PacketPokerSetRole.PLAY))
        a1.handlePacketLogic(PacketPokerSeat(serial = 1, seat = 1, game_id = 2))
        a2 = self.service.createAvatar()
        a2.relogin(1)
        a2.queuePackets()
        a2.handlePacketLogic(PacketPokerTableJoin(serial = 1,game_id = 2))
        self.assertEquals(2, len(self.service.avatar_collection.get(1)))
        self.assertEquals(2, len(self.service.tables[2].avatar_collection.get(1)))
        self.assertEquals(True, 1 in self.service.tables[2].game.serial2player)
        self.service.destroyAvatar(a2)
        self.assertEquals(1, len(self.service.tables[2].avatar_collection.get(1)))
        self.assertEquals(True, 1 in self.service.tables[2].game.serial2player)
        self.service.seatPlayer = _seatPlayer

    def test89_canPerformTourneyChanges(self):
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        def checkForPrivileges((client,packet)):
            avatar = self.service.avatars[0]
            tourney = self.service.tourneys[1]
            # user cannot perform changes as a regular user
            can_perform_changes, error = avatar.canPerformTourneyChanges(avatar.getSerial(),tourney.serial)
            self.assertFalse(can_perform_changes)
            # if the user is the bailor, he can perform changes
            old_bailor_serial, tourney.bailor_serial = tourney.bailor_serial, avatar.getSerial()
            can_perform_changes, error = avatar.canPerformTourneyChanges(avatar.getSerial(),tourney.serial)
            self.assertTrue(can_perform_changes)
            tourney.bailor_serial = old_bailor_serial
            # if the user is admin, he can perform changes
            avatar.user.privilege = avatar.user.ADMIN
            can_perform_changes, error = avatar.canPerformTourneyChanges(avatar.getSerial(),tourney.serial)
            self.assertTrue(can_perform_changes)
            return (client,packet)
            
        d.addCallback(checkForPrivileges)
        return d
    
    def test90_tourneyStart(self):
        tourney = self.service.tourneys[1]
        tourney.players_quota = 3
        tourney.register(1000)
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        def startTourney((client, packet)):
            avatar = self.service.avatars[0]
            avatar.queuePackets()
            tourney.bailor_serial = avatar.getSerial()
            
            # cannot start tourney with less than 2 players
            avatar.handlePacketLogic(PacketPokerTourneyStart(
                serial = avatar.getSerial(),
                tourney_serial = tourney.serial
            ))
            found = False
            packets = [
                p for p in avatar.resetPacketsQueue() 
                if p.type == PACKET_ERROR 
                and p.other_type == PACKET_POKER_TOURNEY 
                and p.code == PacketPokerTourneyStart.NOT_ENOUGH_USERS
            ]
            self.assertTrue(len(packets) > 0)
            self.assertEqual(tourney.state,TOURNAMENT_STATE_REGISTERING)
            
            # can start if at least 2 players are registered
            tourney.register(1001)
            avatar.handlePacketLogic(PacketPokerTourneyStart(
                serial = avatar.getSerial(),
                tourney_serial = tourney.serial
            ))
            packets = [
                p for p in avatar.resetPacketsQueue() 
                if p.type == PACKET_ACK 
            ]
            self.assertTrue(len(packets) > 0)
            self.assertEqual(tourney.state,TOURNAMENT_STATE_RUNNING)
            return (client, packet)
        d.addCallback(startTourney)
        return d
    
    def test91_tourneyCancel(self):
        tourney = self.service.tourneys[1]
        tourney.players_quota = 3
        tourney.register(1000)
        self.createClients(1)
        d = self.client_factory[0].established_deferred
        d.addCallback(self.sendExplain)
        d.addCallback(self.login, 0)
        def cancelTourney((client, packet)):
            avatar = self.service.avatars[0]
            avatar.queuePackets()
            tourney.bailor_serial = avatar.getSerial()
            
            # cannot start tourney with less than 2 players
            avatar.handlePacketLogic(PacketPokerTourneyCancel(
                serial = avatar.getSerial(),
                tourney_serial = tourney.serial
            ))
            packets = [
                p for p in avatar.resetPacketsQueue() 
                if p.type == PACKET_ACK 
            ]
            self.assertTrue(len(packets) > 0)
            self.assertEqual(tourney.state,TOURNAMENT_STATE_CANCELED)
            return (client, packet)
        d.addCallback(cancelTourney)
        return d
##############################################################################
class PokerAvatarNoClientServerTestCase(unittest.TestCase):
    timeout = 500
    
    class MockPlayerInfo:
        def __init__(mpiSelf):
            mpiSelf.url = "http://example.org/"
            mpiSelf.outfit = "naked"
            mpiSelf.locale = 'mylocale'
            mpiSelf.name = 'Doyle Brunson'
    class MockService:
        def __init__(msSelf):
            msSelf.verbose = 6
            def transFunc(locale, encoding = ''):
                if locale == 'mylocale':
                    return lambda s: "MYTRANSLATION"
                else:
                    return lambda s: "BROKEN FAIL"
            msSelf.locale2translationFunc = transFunc
            msSelf.avatar_collection = PokerAvatarCollection()

        def getClientQueuedPacketMax(self):
            return 200000
        def getPlayerInfo(msSelf, serial):
            return PokerAvatarNoClientServerTestCase.MockPlayerInfo()
        def getPlayerPlaces(msSelf, serial):
            class MockPlace:
                def __init__(mpSelf): mpSelf.tourneys = "MOCKPLACES"
            return MockPlace()
        def destroyAvatar(msSelf, avatar):
            avatar.connectionLost("Disconnected")

    class MockExplain:
        def __init__(meSelf): meSelf.handleSerialPackets = []
        def handleSerial(meSelf, pack):
            meSelf.handleSerialPackets.append(pack)
    # ------------------------------------------------------
    def setUp(self):
        testclock._seconds_reset()        

        self.avatarLocales = {}
        self.avatarLocales[0] = "default"
        self.avatarLocales[1] = "default"
    # ------------------------------------------------------------------------
    def test01_reloginCoverage(self):
        """No packet actualy does a relogin, this covers it 'by-hand', as
        it were."""
        from pokernetwork import pokeravatar

        service = PokerAvatarNoClientServerTestCase.MockService()
        avatar = pokeravatar.PokerAvatar(service)
        explain = PokerAvatarNoClientServerTestCase.MockExplain()
        saveExplain = avatar.explain
        avatar.explain = explain

        avatar.localeFunc = lambda s: "DONOTOVERRIDE"

        avatar.relogin(1042)
        self.assertEquals(avatar.user.serial, 1042)
        self.assertEquals(avatar.user.name, 'Doyle Brunson')
        self.assertEquals(avatar.user.url, "http://example.org/")
        self.assertEquals(avatar.user.outfit, "naked")
        self.assertEquals(avatar.user.privilege, pokeravatar.User.REGULAR)
        self.assertEquals(avatar.tourneys, "MOCKPLACES")

        self.assertEquals([avatar], service.avatar_collection.get(1042))

        avatar.explain = saveExplain

        self.assertEquals(len(explain.handleSerialPackets), 1)
        self.assertEquals(explain.handleSerialPackets[0].serial, 1042)
        self.assertEquals(explain.handleSerialPackets[0].type, PACKET_SERIAL)

        self.assertEquals(avatar.localeFunc("DUMMY"),  "DONOTOVERRIDE")
    # ------------------------------------------------------------------------
    def test02_relogin_localeAlreadySet(self):
        """No packet actualy does a relogin, this covers it 'by-hand', as
        it were."""
        from pokernetwork import pokeravatar

        service = PokerAvatarNoClientServerTestCase.MockService()
        avatar = pokeravatar.PokerAvatar(service)
        explain = PokerAvatarNoClientServerTestCase.MockExplain()
        saveExplain = avatar.explain
        avatar.explain = explain

        avatar.relogin(1042)
        self.assertEquals(avatar.user.serial, 1042)
        self.assertEquals(avatar.user.name, 'Doyle Brunson')
        self.assertEquals(avatar.user.url, "http://example.org/")
        self.assertEquals(avatar.user.outfit, "naked")
        self.assertEquals(avatar.user.privilege, pokeravatar.User.REGULAR)
        self.assertEquals(avatar.tourneys, "MOCKPLACES")

        self.assertEquals([avatar], service.avatar_collection.get(1042))

        avatar.explain = saveExplain

        self.assertEquals(len(explain.handleSerialPackets), 1)
        self.assertEquals(explain.handleSerialPackets[0].serial, 1042)
        self.assertEquals(explain.handleSerialPackets[0].type, PACKET_SERIAL)

        self.assertEquals(avatar.localeFunc("DUMMY"), "MYTRANSLATION")
    # ------------------------------------------------------------------------
    def test03_relogin_localeNotFound(self):
        """No packet actualy does a relogin, this covers it 'by-hand', as
        it were."""
        from pokernetwork import pokeravatar

        service = PokerAvatarNoClientServerTestCase.MockService()
        def transFunc(l, codeset = ''): return None
        service.locale2translationFunc = transFunc
        avatar = pokeravatar.PokerAvatar(service)
        explain = PokerAvatarNoClientServerTestCase.MockExplain()
        saveExplain = avatar.explain
        avatar.explain = explain

        avatar.relogin(1042)
        self.assertEquals(avatar.user.serial, 1042)
        self.assertEquals(avatar.user.name, 'Doyle Brunson')
        self.assertEquals(avatar.user.url, "http://example.org/")
        self.assertEquals(avatar.user.outfit, "naked")
        self.assertEquals(avatar.user.privilege, pokeravatar.User.REGULAR)
        self.assertEquals(avatar.tourneys, "MOCKPLACES")

        self.assertEquals([avatar], service.avatar_collection.get(1042))

        avatar.explain = saveExplain

        self.assertEquals(len(explain.handleSerialPackets), 1)
        self.assertEquals(explain.handleSerialPackets[0].serial, 1042)
        self.assertEquals(explain.handleSerialPackets[0].type, PACKET_SERIAL)

        self.assertEquals(None, avatar.localeFunc)

    # ------------------------------------------------------------------------
    def test04_relogin_avatarExists(self):
        """relogin is called where an avatar already exists."""
        from pokernetwork import pokeravatar

        serial = 1042

        service = PokerAvatarNoClientServerTestCase.MockService()
        def transFunc(l, codeset = ''): return None
        service.locale2translationFunc = transFunc
        avatar_first = pokeravatar.PokerAvatar(service)
        #
        # pre-existing avatar
        #
        avatar_second = pokeravatar.PokerAvatar(service)
        # It is only possible to be added to the collection if you
        # logged in prevously, then you must have a serial
        avatar_second.user.serial = serial
        service.avatar_collection.add(avatar_second)
        self.assertEquals([avatar_second], service.avatar_collection.get(serial))

        explain = PokerAvatarNoClientServerTestCase.MockExplain()
        saveExplain = avatar_first.explain
        avatar_first.explain = explain

        avatar_first.relogin(serial)
        
        self.assertEquals(avatar_first.user.serial, serial)
        self.assertEquals(avatar_first.user.name, 'Doyle Brunson')
        self.assertEquals(avatar_first.user.url, "http://example.org/")
        self.assertEquals(avatar_first.user.outfit, "naked")
        self.assertEquals(avatar_first.user.privilege, pokeravatar.User.REGULAR)
        self.assertEquals(avatar_first.tourneys, "MOCKPLACES")

        self.assertEquals([avatar_second, avatar_first], service.avatar_collection.get(serial))

        avatar_first.explain = saveExplain

        self.assertEquals(len(explain.handleSerialPackets), 1)
        self.assertEquals(explain.handleSerialPackets[0].serial, serial)
        self.assertEquals(explain.handleSerialPackets[0].type, PACKET_SERIAL)

        self.assertEquals(None, avatar_first.localeFunc)
        
    # ------------------------------------------------------------------------
    def test05_explain_throws(self):
        """explain throws cause the explain instance to be discarded
        and the avatar do be destroyed."""

        from pokernetwork import pokeravatar

        serial = 1042

        service = PokerAvatarNoClientServerTestCase.MockService()
        def forceAvatarDestroyMockup(avatar):
            forceAvatarDestroyMockup.called = True
        service.forceAvatarDestroy = forceAvatarDestroyMockup
        avatar = pokeravatar.PokerAvatar(service)
        class Explain:
            def explain(self, what):
                raise Exception("FAILURE")
        log_history.reset()
        avatar.explain = Explain()
        avatar.queuePackets()
        avatar.sendPacket(Packet())
        packets = avatar.resetPacketsQueue()
        self.assertEquals(PACKET_ERROR, packets[0].type)
        self.assertSubstring('FAILURE', packets[0].message)
        self.assertEquals(True, log_history.search('FAILURE'))
        self.assertEquals(None, avatar.explain)
        self.assertEquals(True, forceAvatarDestroyMockup.called)

def fixIt(client_info):
    # return the last packet of a client_info list
    for (_packet,client) in client_info: pass
    return client
##############################################################################

def GetTestSuite():
    loader = runner.TestLoader()
    # loader.methodPrefix = "_test"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(PokerAvatarLocaleTestCase))
    suite.addTest(loader.loadClass(PokerAvatarTestCase))
    suite.addTest(loader.loadClass(PokerAvatarNoClientServerTestCase))
    return suite

def Run():
    return runner.TrialRunner(
        reporter.TextReporter,
        tracebackFormat='default'
    ).run(GetTestSuite())

# ------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
