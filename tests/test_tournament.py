#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# more information about the above line at http://www.python.org/dev/peps/pep-0263/
#
# Copyright (C) 2009 Bradley M. Kuhn <bkuhn@ebb.org>
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

import sys
import re
from os import path
import random
from pokerengine.pokergame import GAME_STATE_BLIND_ANTE, GAME_STATE_END,\
    GAME_STATE_MUCK, GAME_STATE_NULL

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from config import config
from log_history import log_history

import libxml2
import time

import twisted

from twisted.internet import selectreactor
selectreactor.install()

from tests import testclock
from twisted.trial import unittest, runner, reporter
from twisted.internet import reactor, defer

twisted.internet.base.DelayedCall.debug = True

import reflogging
log = reflogging.root_logger.get_child('test-tournaments')

import pokernetwork
from pokernetwork.pokertable import PokerTable, PokerAvatarCollection
from pokerengine.pokertournament import TOURNAMENT_STATE_RUNNING
from pokernetwork.pokeravatar import PokerAvatar
from pokerpackets.networkpackets import PacketPokerPlayerInfo
from twisted.internet.defer import DeferredList
from functools import wraps

from pokerpackets.networkpackets import *
from pokernetwork import pokertable, pokernetworkconfig
from pokernetwork.pokerservice import PokerService

settings_xml = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="4" autodeal="yes" max_missed_round="5">
  <delays autodeal_tournament_min="2" autodeal="2" autodeal_max="2" autodeal_check="0" round="0" position="0" showdown="0" finish="0" />

  <path>%(engine_path)s/conf %(tests_path)s/../conf</path>
  <users temporary="BOT.*"/>
</server>
""" % {
    'tests_path': TESTS_PATH,
    'engine_path': config.test.engine_path
}

def noop(*a, **kw): return

class MockCursor:
    rowcount = 1
    
    def execute(self, query, args=None):
        self._executed = query % args if args else query
        
    def close(self):
        return
    
class MockDb:
    def cursor(self):
        return MockCursor()
    def literal(self, what):
        return what

class MockTable(PokerTable):
    def syncDatabase(self, history):
        return
    def _initLockCheck(self):
        self._lock_check = None
    def getPlayerInfo(self, serial):
        return PacketPokerPlayerInfo(
            serial = serial,
            name = 'Player %d' % serial,
            url = 'default',
            outfit = 'default'
        )

def wrap_with_db(fn):
    @wraps(fn)
    def wrap_fn(self_, *a, **kw):
        self_._db_cnt = getattr(self_, '_db_cnt', 0) + 1
        if self_._db_cnt == 1: self_.db = MockDb()
        ret = fn(self_, *a, **kw)
        self_._db_cnt -= 1
        if self_._db_cnt <= 0: del self_.db
        return ret
    return wrap_fn
            
class MockService(PokerService):
    log = log.get_child('MockService')
    
    def __init__(self, settings):
        self.log = MockService.log.get_instance(self, refs=[
            ('Service', self, lambda mc: 1)
        ])
        
        self.settings = settings
        self.dirs = settings.headerGet("/server/path").split()
        
        self.tourney_table_serial = 1
        
        self.missed_round_max = 5
        self.shutting_down = False
        self.monitors = {}
        self.monitor_plugins = []
        self.has_ladder = False
        self.refill = False
        self.schedule2tourneys = {}
        self.tourneys = {}
        self.tables = {}
        self.timer = {}
        self.timer_remove_player = {}
        
        self.simultaneous = 10
        self.joined_count = 2*32
        self.avatar_collection = PokerAvatarCollection("service")
        
        self.delays = {'extra_wait_sng_start': 0, 'autodeal_check': 2, 'autodeal_tournament_min': 2, 'autodeal': 2, 'autodeal_max': 2}
        self._table_id = 0
        self._hand_id = 0
        
        
    
    def spawnTable(self, serial, **kw):
        table = MockTable(self, serial, kw)
        self.tables[serial] = table
        return table
    
    def createHand(self, game_id, tourney_serial=None):
        self._hand_id += 1
        return self._hand_id
    
    def buyOutPlayer(self, serial, table_id, currency_serial):
        return
    
    def leavePlayer(self, serial, table_id, currency_serial):
        return
    
    def movePlayer(self, serial, from_table_id, to_table_id):
        return 0
    
    def updateTableStats(self, game, observers, waiting):
        return
    
    def destroyTable(self, table_id):
        return
    
    def deleteTableEntry(self, table):
        return
    
    def getName(self, serial):
        return 'Name %d' % serial

    def tourneyFinished(self, tourney):
        return True
    
    def tourneyBroadcastStart(self, tourney_serial):
        return
    
    def tourneySetUpLockCheck(self, tourney, old_state, new_state):
        return
    
    def tourneyIsRelevant(self, tourney):
        return True
    
    @wrap_with_db
    def tourneyMovePlayer(self, tourney, from_game_id, to_game_id, serial):
        return PokerService.tourneyMovePlayer(self, tourney, from_game_id, to_game_id, serial)
    
    @wrap_with_db
    def tourneyRemovePlayer(self, tourney, serial, now=False):
        return PokerService.tourneyRemovePlayer(self, tourney, serial, now=now)
    
    @wrap_with_db
    def tourneyNewState(self, tourney, old_state, new_state):
        return PokerService.tourneyNewState(self, tourney, old_state, new_state)
    
    def tourneyRegister(self, packet, via_satellite=False):
        serial = packet.serial
        tourney_serial = packet.tourney_serial
        tourney = self.tourneys.get(tourney_serial,None)
        tourney.register(serial,self.getName(serial))
        return True
    
    def tourneyGameFilled(self, tourney, game):
        table = self.getTable(game.id)
        for player in game.playersAll():
            player.setUserData({'ready': True})
        table.update()
        
    def createTable(self, owner, description):
        self._table_id += 1
        table = self.spawnTable(self._table_id, **description)
        table.owner = owner
        return table

    def isTemporaryUser(self, serial):
        return False
    
class MockClient(PokerAvatar):
    log = log.get_child('MockClient')
    
    class User:
        def __init__(self, serial):
            self.serial = serial
            self.name = 'User %d' % serial
            
        def isLogged(self):
            return True

    def __init__(self, serial, service):
        self.log = MockClient.log.get_instance(self, refs=[
            ('User', self, lambda mc: mc.serial)
        ])
        
        self.serial = serial
        self.service = service
        self.deferred = None
        self.raise_if_packet = None
        self.filters = None
        self.packets = []
        self.user = MockClient.User(serial)
        self.tables = {}
        
        self.finished = defer.Deferred()
        self._handlers = []

    def getSerial(self):
        return self.user.serial
    
    def join(self, table, reason=""):
        PokerAvatar.join(self, table, reason)
    
    def _checkForFilter(self, packet, packet_filter):
        if hasattr(packet_filter, '__call__'):
            return packet_filter(packet)
        else:
            return packet.type == packet_filter
        
    def sendPacket(self, packet):
        # print 'sendPacket - serial: %d, packet: %s' % (self.getSerial(), packet)
        self.packets.append(packet)
        
        for (packet_filter, handler) in self._handlers:
            found = self._checkForFilter(packet, packet_filter)
            if found: handler(packet)

    def registerHandler(self, packet_filter, handler):
        self._handlers.append((packet_filter, handler))
    
    def handleRank(self, packet):
        # print 'handleRank - serial: %d, rank: %d' % (self.getSerial(), packet.rank)
        self.finished.callback((self.getSerial(), packet))
    
    def handlePosition(self, packet):
        # print 'playBySerial - serial: %d, packet: %s' % (self.getSerial(), packet)
        
        table = self.tables[packet.game_id]
        action = self._chooseAction(packet)
        reactor.callLater(0, self._issueAction, table.game.id, action)

    def filterPosition(self, packet):
        if not hasattr(packet, 'game_id') or packet.game_id not in self.tables: return False
        game_state = self.tables[packet.game_id].game.state
        return game_state not in (GAME_STATE_BLIND_ANTE, GAME_STATE_END, GAME_STATE_MUCK, GAME_STATE_NULL) \
            and packet.type == PACKET_POKER_POSITION \
            and packet.serial == self.getSerial()
    
    def _chooseAction(self, packet):
        rand = random.random()
        if rand > 0.6: return 'raise'
        else: return 'call'
        
    def _issueAction(self, game_id, action):
        if game_id not in self.tables:
            # print '_issueAction - not in tables - serial: %d, game_id: %d' % (self.getSerial(), game_id)
            return
        
        table = self.tables[game_id]
        game = table.game
        serial = self.getSerial()
        player = game.serial2player.get(serial, None)
        
        if player is None:
            # print '_issueAction - player is None - serial: %d, game_id: %d' % (serial, game_id)
            return

        if not game.isRunning():
            # can happen if only one player is active
            # print '_issueAction - game is not running - serial: %d, game_id: %d, state: %s' % (serial, game_id, game.state)
            return
        
        # print '_issueAction - serial: %d, game_id: %d, state: %s, action: %s' % (serial, game_id, game.state, action)
        
        if action == 'call':
            game.call(serial)
        if action == 'raise':
            game.callNraise(serial, 0)
        elif action == 'allin':
            game.callNraise(serial, 2**31)
            
        table.update()

                        
          
# --------------------------------------------------------------------------------

class TournamentTestCase(unittest.TestCase):
    timeout = 3600
    
    def setUp(self):
        testclock._seconds_reset()
        random.seed(1)
        settings = pokernetworkconfig.Config([])
        settings.doc = libxml2.parseMemory(settings_xml, len(settings_xml))
        settings.header = settings.doc.xpathNewContext()
        self.service = MockService(settings)
        self.clients = {}
        self.tourney = None
        
    def getTourneyMap(self, **kw):
        tourney_map = {
            'serial': 1,
            'resthost_serial': 0,
            'schedule_serial': 100,
            'name': 'Tourney %d' % 1,
            'players_quota': 2,
            'players_min': 2,
            'seats_per_game': 2,
            'variant': 'holdem',
            'start_time': time.time() + 24*3600,
            'sit_n_go': 'n',
            'bailor_serial': 0,
            'player_timeout': 60,
            'via_satellite': 0,
            'satellite_of': 0,
            'satellite_player_count': 0,
            'rebuy_delay': 0,
            'inactive_delay': 0,
            'betting_structure': 'level-15-30-no-limit'
        }
        tourney_map.update(kw)
        return tourney_map
    
    def createTourney(self, **kw):
        tm = self.getTourneyMap(**kw)
        self.tourney = self.service.spawnTourneyInCore(tm, tm['serial'], tm['schedule_serial'], 1, 1)
        for serial in range(1,tm['players_quota']+1):
            self.clients[serial] = self.createPlayer(serial)
            self.registerToTourney(serial, self.tourney.serial)

    def registerToTourney(self, serial, tourney_serial):
        packet = type("MockPacket",(object,),{"serial": serial, "tourney_serial": tourney_serial})
        self.service.autorefill(serial)
        self.service.tourneyRegister(packet)
    
    def createPlayer(self, serial):
        client = MockClient(serial, self.service)
        self.service.avatar_collection.add(client)
        return client
    
    def testNormalGame(self):
        '''all players play normally'''
        
        self.createTourney(players_quota=5, players_min=5, seats_per_game=2)
        tourney, clients = self.tourney, self.clients
        tourney.changeState(TOURNAMENT_STATE_RUNNING)
        
        dl = []
        for client in clients.itervalues():
            client.registerHandler(PACKET_POKER_TOURNEY_RANK, client.handleRank)
            client.registerHandler(client.filterPosition, client.handlePosition)
            dl.append(client.finished)
        dl = DeferredList(dl)

        for game_id,game in tourney.id2game.items():
            table = self.service.tables[game_id]
            for serial in game.serial2player:
                client = clients[serial]
                table.joinPlayer(client)
                table.update()
        
        return dl

    def testInactiveDelay(self):
        '''all but one player is inactive. this player should win'''
        
        self.createTourney(players_quota=5, players_min=5, seats_per_game=2, inactive_delay=1000)
        tourney, clients = self.tourney, self.clients
        tourney.changeState(TOURNAMENT_STATE_RUNNING)

        serial = 1
        client_online = None
        table_online = None
        
        dl = []
        for client in clients.itervalues():
            client.registerHandler(PACKET_POKER_TOURNEY_RANK, client.handleRank)
            dl.append(client.finished)
        dl = DeferredList(dl)
        
        for game_id,game in tourney.id2game.items():
            if serial in game.serial2player:
                table_online = self.service.tables[game_id]
                client_online = clients[serial]
                client_online.registerHandler(client_online.filterPosition, client_online.handlePosition)
                break
        
        def checkForRank(res): self.assertEquals(tourney.winners[0], client_online.getSerial())
        dl.addCallback(checkForRank)
        
        table_online.joinPlayer(client_online)
        table_online.update()
        
        return dl
    
    def testAllInactive(self):
        '''everybody is inactive. the tourney should finish quickly nevertheless'''
        
        self.createTourney(players_quota=30, players_min=30, seats_per_game=5, inactive_delay=1)
        tourney, clients = self.tourney, self.clients
        tourney.changeState(TOURNAMENT_STATE_RUNNING)

        dl = []
        for client in clients.itervalues():
            client.registerHandler(PACKET_POKER_TOURNEY_RANK, client.handleRank)
            dl.append(client.finished)
        dl = DeferredList(dl)
        
        def checkHandId(res):
            self.assertTrue(self.service._hand_id <= 9, "should only take a few hands to finish")
            
        dl.addCallback(checkHandId)
        return dl
    
    def testEqualBroke(self):
        self.createTourney(players_quota=8, players_min=8, seats_per_game=4, inactive_delay=1000)
        tourney, clients = self.tourney, self.clients
        
        self.service.getTableAutoDeal = lambda: False
        tourney.changeState(TOURNAMENT_STATE_RUNNING)
        
        dl = []
        for client in clients.itervalues():
            client._chooseAction = lambda packet: 'allin'
            client.registerHandler(PACKET_POKER_TOURNEY_RANK, client.handleRank)
            client.registerHandler(client.filterPosition, client.handlePosition)
            dl.append(client.finished)
        dl = DeferredList(dl)
        
        for game in tourney.id2game.itervalues():
            game.ante_info = {'value': 5, 'change': None}
            for player in game.playersAll()[:-1]:
                player.money = 5
        
        self.service.getTableAutoDeal = lambda: True
        self.service.tourneyDeal(tourney)
        
        return dl
    
    def testOnlyOneAction(self):
        '''one player does one action. he should win the tourney.'''
        
        self.createTourney(players_quota=8, players_min=8, seats_per_game=4, inactive_delay=1000)
        tourney, clients = self.tourney, self.clients
        tourney.changeState(TOURNAMENT_STATE_RUNNING)

        serial = 1
        client_online = clients[serial]
        table_online = None
        
        dl = []
        for client in clients.itervalues():
            client.registerHandler(PACKET_POKER_TOURNEY_RANK, client.handleRank)
            dl.append(client.finished)
        dl = DeferredList(dl)
        
        for game_id,game in tourney.id2game.items():
            if serial in game.serial2player:
                table_online = self.service.tables[game_id]
                break
        
        def handleOneCall(packet):
            client_online.handlePosition(packet)
            client_online._handlers.pop()
            
        client_online._chooseAction = lambda packet: 'call'
        client_online.registerHandler(client_online.filterPosition, handleOneCall)
        
        def checkForRank(res): self.assertEquals(tourney.winners[0], client_online.getSerial())
        dl.addCallback(checkForRank)
        
        table_online.joinPlayer(client_online)
        table_online.update()
        
        return dl        
        
        
# --------------------------------------------------------------------------------

def GetTestSuite():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(TournamentTestCase))
    return suite

def Run():
    return runner.TrialRunner(
        reporter.TextReporter,
        tracebackFormat='default'
    ).run(GetTestSuite())
    
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
    
