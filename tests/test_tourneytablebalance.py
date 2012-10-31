#!/usr/bin/env python
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
# more information about the above line at http://www.python.org/dev/peps/pep-0263/
#
# Copyright (C)       2008 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C)       2006 Mekensleep <licensing@mekensleep.com>
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
#  Bradley M. Kuhn <bkuhn@ebb.org>
#
import sys, os
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))
sys.path.insert(1, path.join(TESTS_PATH, "../../common"))

from config import config
from log_history import log_history
import sqlmanager

import libxml2

from tests import testclock

from twisted.trial import unittest, runner, reporter
import twisted.internet.base
from twisted.internet import reactor, defer

twisted.internet.base.DelayedCall.debug = False


from pokerengine import pokertournament, pokergame
from pokernetwork import pokerservice, pokernetworkconfig
from pokernetwork import currencyclient
from pokernetwork import pokerdatabase
currencyclient.CurrencyClient = currencyclient.FakeCurrencyClient
from pokerpackets.networkpackets import *

class ConstantDeckShuffler:
    def shuffle(self, what):
        what[:] = [40, 13, 32, 9, 19, 31, 15, 14, 50, 34, 20, 6, 43, 44, 28, 29, 48, 3, 21, 45, 23, 37, 35, 11, 5, 22, 24, 30, 27, 39, 46, 33, 0, 8, 1, 42, 36, 16, 49, 2, 10, 26, 4, 18, 7, 41, 47, 17]

pokergame.shuffler = ConstantDeckShuffler()

class ConstantPlayerShuffler:
    def shuffle(self, what):
        what.sort()

pokertournament.shuffler = ConstantPlayerShuffler()

settings_xml = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" max_joined="1000" simultaneous="4" chat="yes" remove_completed="1" >
  <delays autodeal="18" round="12" position="60" showdown="30" finish="18" />

  <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />
  <table name="Table2" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />

  <listen tcp="19480" />

  <language value="en_US.UTF-8"/>

  <stats type="RankPercentile"/>

  <tourney_attrs type="SponsoredPrizes"/>

  <refill serial="1" amount="10000000" />

  <cashier acquire_timeout="5" pokerlock_queue_timeout="30" user_create="yes" />
  <database
    host="%(dbhost)s" name="%(dbname)s"
    user="%(dbuser)s" password="%(dbuser_password)s"
    root_user="%(dbroot)s" root_password="%(dbroot_password)s"
    schema="%(tests_path)s/../database/schema.sql"
    command="%(mysql_command)s" />
  <path>%(engine_path)s/conf %(tests_path)s/../conf</path>
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
class UserMockup:
    def isLogged(self): return True
        
class ClientMockup:
    def __init__(self, serial):
        self.user = UserMockup()
        self.serial = serial
        self.packet_end_tournament = None
        self.packets = []
        self.tables = {}
        self.joinedTables = []
        self.deferred = None
        self._queue_packets = False

    def getPlayerInfo(self):
        class MockInfo:
            def __init__(miSelf):
                miSelf.name =  "PLAYER INFO: %d" % self.serial
                miSelf.url  = "http://example.org"
                miSelf.outfit  = "naked"
        return MockInfo()

    def sendPacket(self, packet):
        self.packets.append(packet)
        if self.deferred and self.type == packet.type:
                reactor.callLater(0, lambda: self.deferred.callback(packet))
        
    def join(self, table, reason = ""):
        self.joinedTables.append(table)
        self.tables[table.game.id] = table

    def getSerial(self):
        return self.serial

    def sendPacketVerbose(self, packet):
        self.sendPacket(packet)

    def waitFor(self, type):
        self.deferred = defer.Deferred()
        self.type = type
        return self.deferred

class TourneyTableBalanceTestCase(unittest.TestCase):

    def destroyDb(self, *a):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )

    # ----------------------------------------------------------------
    def setUp(self):
        testclock._seconds_reset()
        self.destroyDb()
        self.settings = settings = pokernetworkconfig.Config([])
        settings.doc = libxml2.parseMemory(settings_xml, len(settings_xml))
        settings.header = settings.doc.xpathNewContext()
        self.db = pokerdatabase.PokerDatabase(settings)
        self.service = pokerservice.PokerService(settings)
        self.default_money = 10000000
#        self.service.verbose = 0
#        self.service.verbose = 4
    # ----------------------------------------------------------------
    def tearDown(self):
        self.db.close()
        for t in self.service.tables.values(): t.destroy()
        d = self.service.stopService()
        d.addCallback(lambda x: self.destroyDb())
        return d
    # ----------------------------------------------------------------
    def createUsers(self):
        cursor = self.db.cursor()
        for user_number in (1, 2, 3, 4, 5, 6):
            cursor.execute("INSERT INTO users (name, password, created) VALUES ('user%d', 'password%d', 0)" % ( user_number, user_number ))
            self.assertEqual(1, cursor.rowcount)

        self.user_serials = []
        for _ii in range(0,6): self.user_serials.append(None)
        (self.user_serials[0], _name, _privilege), _message = self.service.auth(PACKET_LOGIN, ("user1", "password1"), "role1")
        (self.user_serials[1], _name, _privilege), _message = self.service.auth(PACKET_LOGIN, ("user2", "password2"), "role1")
        (self.user_serials[2], _name, _privilege), _message = self.service.auth(PACKET_LOGIN, ("user3", "password3"), "role1")
        (self.user_serials[3], _name, _privilege), _message = self.service.auth(PACKET_LOGIN, ("user4", "password4"), "role1")
        (self.user_serials[4], _name, _privilege), _message = self.service.auth(PACKET_LOGIN, ("user5", "password5"), "role1")
        (self.user_serials[5], _name, _privilege), _message = self.service.auth(PACKET_LOGIN, ("user6", "password6"), "role1")

        cursor.close()
    # ----------------------------------------------------------------
    def test01_sixPlayersTourney5PerTable(self):
        """test01_sixPlayersTourney5PerTable

        Test the condition where six players sign up for a tourney that
        has five people per table.  It has been reported that this causes
        5 people at one table and 1 player at the other"""

        pokerservice.UPDATE_TOURNEYS_SCHEDULE_DELAY = 1
        pokerservice.CHECK_TOURNEYS_SCHEDULE_DELAY = 0.1

        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO `tourneys_schedule` (`name`, `description_short`, `description_long`, `players_quota`, `variant`, `betting_structure`, `seats_per_game`, `currency_serial`, `buy_in`, `rake`, `sit_n_go`, `start_time`, `register_time`, `respawn`, `respawn_interval`, `players_min`, `breaks_first`)" \
            "VALUES ('Only6', 'Sit and Go 6 players and only 6, Holdem', 'Sit and Go 6 players only', '6', 'holdem', 'level-15-30-no-limit', '5', 1, '0', '0', 'y', '0', '0', 'y', '0', '6', 1 )"
        )
        cursor.close()

        self.service.startService()
        self.createUsers()
        tourneys = self.service.tourneySelect('Only6')
        self.assertEquals(len(tourneys), 1)
        t = tourneys[0]
        self.assertEquals(t['name'], 'Only6')
        self.assertEquals(t['betting_structure'], 'level-15-30-no-limit')
        self.assertEquals(t['players_quota'], 6L)
        self.assertEquals(t['players_min'], 6L)
        self.assertEquals(t['seats_per_game'], 5L)
        tourneySerial = t['serial']

        clients = {}
        for userSerial in self.user_serials:
            clients[userSerial] = ClientMockup(userSerial)
            self.service.avatar_collection.add(userSerial, clients[userSerial])
            self.service.tourneyRegister(PacketPokerTourneyRegister(serial=userSerial, tourney_serial=tourneySerial))

        tourneys =  self.service.tourneys.values()

        sixTourney = [t for t in self.service.tourneys.itervalues() if t.name=='Only6'][0]
        self.assertEquals(sixTourney.serial, tourneySerial)

        d = defer.Deferred()
        def checkTourney(status):
            self.assertEquals(pokertournament.TOURNAMENT_STATE_RUNNING, sixTourney.state)
            self.assertEquals(self.service.joined_count, 6)
            for game in sixTourney.games:
                # tables should be equalized
                self.assertTrue(len(game.serial2player.keys()) >= 2)
            
        d.addCallback(checkTourney)

        reactor.callLater(3, d.callback, True)

        return d
# ----------------------------------------------------------------

def GetTestSuite():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(TourneyTableBalanceTestCase))
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
