#!/usr/bin/env python
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
#                    24 rue vieille du temple, 75004 Paris
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
#
import sys, os
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from config import config
from log_history import log_history
import sqlmanager

import libxml2

from twisted.trial import unittest, runner, reporter
import twisted.internet.base

twisted.internet.base.DelayedCall.debug = False

from twisted.python.runtime import seconds

from pokernetwork import pokerservice
from pokernetwork import pokernetworkconfig
from pokernetwork.pokerdatabase import PokerDatabase

settings_xml_server = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="3" ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" />

  <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="4" currency_serial="1" />
  <table name="Table2" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="4" currency_serial="1" />

  <listen tcp="19480" />

  <cashier acquire_timeout="5" pokerlock_queue_timeout="30" />
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

class PokerCrashTestCase(unittest.TestCase):

    def destroyDb(self, *a):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )

    def setUpServer(self):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml_server)
        #
        # Setup database
        #
        self.db = PokerDatabase(settings)
        #
        # Setup server
        #
        self.service = pokerservice.PokerService(settings)
        self.service.verbose = 6

    # -------------------------------------------------
    def setUp(self):
        self.destroyDb()
        self.setUpServer()

    def tearDown(self):
        self.db.close()
        return self.service.stopService()

    def test01_cleanupCrashedTables(self):
        cursor = self.db.cursor()
        #
        # Although the name is not in the configuration file (settings),
        # it has a matching resthost_serial and is cleanedup
        #
        cursor.execute('INSERT INTO user2table (user_serial, table_serial, money, bet) VALUES (1000, 142, 10, 1)')
        cursor.execute("INSERT INTO users (serial, created, name, password) VALUES (1000, 0, 'testuser', '')")
        cursor.execute("INSERT INTO user2money (user_serial, currency_serial, amount) VALUES (1000, 1, 0)")
        #
        # resthost_serial does not match, the records are left untouched
        #
        cursor.execute('INSERT INTO user2table (user_serial, table_serial, money, bet) VALUES (1000, 202, 10, 1)')
        #
        # Table1 is in the configuration file and cleaned up even though
        # resthost_serial does not match
        #
        cursor.execute('INSERT INTO tableconfigs (serial, name, variant, betting_structure, currency_serial) VALUES (1, "Table1", "holdem", "2-4-no-limit", 1)')
        cursor.execute('INSERT INTO tables (serial, resthost_serial, tableconfig_serial) VALUES (303, 1, 1)')
        self.service.startService()
        cursor.execute("SELECT user_serial,table_serial FROM user2table")
        self.assertEqual(2, cursor.rowcount)
        self.assertEqual(((1000, 142),(1000, 202)), cursor.fetchall())
        cursor.execute("SELECT serial FROM tables")
        self.assertEqual((303,), cursor.fetchone())
        cursor.execute("SELECT amount FROM user2money")
        #TODO this test sucks, data gets intermixed, rework!
        # self.assertEqual(11, cursor.fetchall())
        cursor.close()

    def test02_cleanupTourneys_refund(self):
        tourney_serial = '10'
        user_serial = '200'
        buy_in = '300'
        currency_serial = '44'
        cursor = self.db.cursor()
        cursor.execute('INSERT INTO tourneys (serial,name,buy_in,currency_serial,description_short,description_long,variant,betting_structure,schedule_serial) VALUES (%s, "one", %s, %s, "", "", "holdem", "2-4-no-limit", 0)', ( tourney_serial, buy_in, currency_serial ))
        cursor.execute('INSERT INTO user2tourney (user_serial,currency_serial,tourney_serial) VALUES (%s,1,%s)', ( user_serial, tourney_serial ))
        cursor.execute('INSERT INTO user2money (user_serial,currency_serial,amount) VALUES (%s,%s,0)', ( user_serial, currency_serial ))
        cursor.execute('SELECT * FROM tourneys WHERE serial = ' + tourney_serial)
        self.assertEqual(1, cursor.rowcount)
        cursor.execute('SELECT amount FROM user2money WHERE user_serial = %s AND currency_serial = %s', ( user_serial, currency_serial ))
        self.assertEqual((0,), cursor.fetchone())
        self.service.startService()
        cursor.execute('SELECT * FROM tourneys WHERE serial = ' + tourney_serial)
        self.assertEqual(0, cursor.rowcount)
        cursor.execute('SELECT amount FROM user2money WHERE user_serial = %s AND currency_serial = %s', ( user_serial, currency_serial ))
        self.assertEqual((300,), cursor.fetchone())
        cursor.close()

    def test02_cleanupTourneys_restore(self):
        regular_tourney_serial = '10'
        sng_tourney_serial = '40'
        user_serial = '200'
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM tourneys_schedule")
        #
        # Sit and go in 'registering' state is trashed
        #
        cursor.execute('INSERT INTO tourneys (serial,name,description_short,description_long,variant,betting_structure,currency_serial,schedule_serial) VALUES (%s, "one", "", "", "holdem", "2-4-no-limit", 0, 0)', sng_tourney_serial)
        cursor.execute('INSERT INTO user2tourney (user_serial,currency_serial,tourney_serial) VALUES (%s,1,%s)', ( user_serial, sng_tourney_serial ))
        cursor.execute('SELECT * FROM tourneys WHERE serial = ' + sng_tourney_serial)
        self.assertEqual(1, cursor.rowcount)
        #
        # Regular in 'registering' state is kept
        #
        cursor.execute('INSERT INTO tourneys (serial,name,sit_n_go,start_time,description_short,description_long,variant,betting_structure,currency_serial,schedule_serial) VALUES (%s, "one", "n", %s, "", "", "holdem", "2-4-no-limit", 0, 0)', ( regular_tourney_serial, seconds() + 2000))
        cursor.execute('INSERT INTO user2tourney (user_serial,currency_serial,tourney_serial) VALUES (%s,1,%s)', ( user_serial, regular_tourney_serial ))
        cursor.execute('SELECT * FROM tourneys WHERE serial = ' + regular_tourney_serial)
        self.assertEqual(1, cursor.rowcount)
        #
        # Run cleanupTourneys as a side effect
        #
        self.service.startService()
        #
        # Sanity checks
        #
        self.assertEqual([int(regular_tourney_serial)], self.service.tourneys.keys())
        cursor.execute('SELECT * FROM user2tourney WHERE tourney_serial = %s', regular_tourney_serial)
        self.assertEqual(1, cursor.rowcount)
        cursor.execute('SELECT * FROM user2tourney WHERE tourney_serial = %s', sng_tourney_serial)
        self.assertEqual(0, cursor.rowcount)
        cursor.execute('SELECT * FROM user2tourney')
        self.assertEqual(1, cursor.rowcount)
        cursor.execute('SELECT * FROM tourneys')
        self.assertEqual(1, cursor.rowcount)
        cursor.close()

# -----------------------------------------------------------------------------------------------------

def GetTestSuite():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test09"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(PokerCrashTestCase))
    return suite

def Run():
    return runner.TrialRunner(reporter.TextReporter,
#                              tracebackFormat='verbose',
                              tracebackFormat='default',
                              ).run(GetTestSuite())

# -----------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
