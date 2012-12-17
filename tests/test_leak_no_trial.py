#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2008, 2009 Loic Dachary <loic@dachary.org>
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

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from config import config
import sqlmanager

from twisted.internet import selectreactor, main
class MyReactor(selectreactor.SelectReactor):
      def runUntilCurrent(self):
            self._cancellations = 20000000
            selectreactor.SelectReactor.runUntilCurrent(self)
from twisted.internet import defer, reactor
from twisted.application import internet
from twisted.python import failure
from twisted.python.runtime import seconds
import twisted.internet.base
twisted.internet.base.DelayedCall.debug = False

from twisted.web import client, http

from tests import testclock

from pokernetwork import pokermemcache
from pokernetwork import pokersite
from pokernetwork import pokernetworkconfig
from pokernetwork import pokerservice
from pokerpackets.networkpackets import *

settings_xml_server = """<?xml version="1.0" encoding="UTF-8"?>
<server ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

  <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />
  <table name="Table2" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />

  <listen tcp="19481" />
  <resthost host="127.0.0.1" port="19481" path="/POKER_REST" />

  <cashier acquire_timeout="5" pokerlock_queue_timeout="30" user_create="yes" />
    <database
        host="%(dbhost)s" name="%(dbname)s"
        user="%(dbuser)s" password="%(dbuser_password)s"
        root_user="%(dbroot)s" root_password="%(dbroot_password)s"
        schema="%(tests_path)s/../database/schema.sql"
        command="%(mysql_command)s" />
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

class LeakTestCase:

    def destroyDb(self, *a):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )

    def initServer(self):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml_server)
        self.server_service = pokerservice.PokerService(settings)
        self.server_service.disconnectAll = lambda: True
        self.server_service.startService()
        self.server_site = pokersite.PokerSite(settings, pokerservice.PokerRestTree(self.server_service))
        self.server_port = reactor.listenTCP(19481, self.server_site, interface="127.0.0.1")

    def setUp(self):
        testclock._seconds_reset()
        pokermemcache.memcache = pokermemcache.MemcacheMockup
        pokermemcache.memcache_singleton.clear()
        pokermemcache.memcache_expiration_singleton.clear()
        self.destroyDb()
        self.initServer()

    def tearDownServer(self):
        self.server_site.stopFactory()
        d = self.server_service.stopService()
        d.addCallback(lambda x: self.server_port.stopListening())
        return d

    def tearDown(self):
        d = self.tearDownServer()
        d.addCallback(self.destroyDb)
        d.addCallback(lambda x: reactor.disconnectAll())
        return d

    def cleanMemcache(self, x):
        pokermemcache.memcache_singleton.clear()
        pokermemcache.memcache_expiration_singleton.clear()

    def test01_ping(self):
        """
        VIRT (samples: 167, step 3s)
        34372, stable
        """
        def f(ignored):
            d = client.getPage("http://127.0.0.1:19481/POKER_REST", postdata = '{"type":"PacketPing"}')
            d.addCallback(self.cleanMemcache)
            d.addCallback(f)
        f(None)

    def test02_joinTable(self):
        """
        VIRT (samples: 63, step: 3s)
        35792, stable
        """
        def f(ignored, i):
            serial = 0
            session = 'session' + str(i)
            self.server_site.memcache.set(session, str(serial))
            headers = { 'Cookie': 'TWISTED_SESSION='+session }
            d = client.getPage("http://127.0.0.1:19481/POKER_REST", postdata = '{"type":"PacketPokerTableJoin","game_id":1}', headers = headers)
            d.addCallback(lambda x: client.getPage("http://127.0.0.1:19481/POKER_REST", postdata = '{"type":"PacketPokerTableQuit","game_id":1}', headers = headers))
            d.addCallback(self.cleanMemcache)
            d.addCallback(f, i+1)
        i = 1
        f(None, i)

    def test03_joinTable_guppy(self):
        import guppy, gc
        hpy = guppy.hpy()
        def f(ignored, last, first, i):
            gc.collect()
            next = hpy.heap()
            print 'SINCE LAST TIME'
            print next - last
            print 'SINCE FOREVER'
            print last - first
            serial = 0
            session = 'session' + str(i)
            self.server_site.memcache.set(session, str(serial))
            headers = { 'Cookie': 'TWISTED_SESSION='+session }
            d = client.getPage("http://127.0.0.1:19481/POKER_REST", postdata = '{"type":"PacketPokerTableJoin","game_id":1}', headers = headers)
            d.addCallback(lambda x: client.getPage("http://127.0.0.1:19481/POKER_REST", postdata = '{"type":"PacketPokerTableQuit","game_id":1}', headers = headers))
            d.addCallback(self.cleanMemcache)
            d.addCallback(f, next, first, i+1)
        first = hpy.heap()
        i = 1
        f(None, first, first, i)

def run():
    #main.installReactor(MyReactor())
    t = LeakTestCase()
    t.setUp()
    t.test01_ping()
    reactor.run()


if __name__ == '__main__':
    run()
