#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008, 2009 Loic Dachary    <loic@dachary.org>
# Copyright (C) 2009 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2009 Johan Euphrosine <proppy@aminche.com>
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

import simplejson as json

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer, reactor
import twisted.internet.base
twisted.internet.base.DelayedCall.debug = False

from twisted.web import client

from tests import testclock

from pokernetwork import pokermemcache
from pokernetwork import pokersite
from pokernetwork import pokernetworkconfig
from pokernetwork import pokerservice
from pokerpackets.networkpackets import *
from pokernetwork.pokerrestclient import PokerRestClient
PokerRestClient.DEFAULT_LONG_POLL_FREQUENCY = -1
import time

settings_xml_server = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

  <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />
  <table name="Table2" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />

  <listen tcp="19482" />
  <resthost host="127.0.0.1" port="19482" path="/POKER_REST" />

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

settings_xml_explain = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

  <listen tcp="19481" />
  <resthost host="127.0.0.1" port="19481" path="/POKER_REST" name="explain1" />

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

settings_xml_proxy = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

  <listen tcp="19480" />

  <rest_filter>pokernetwork.sessionproxyfilter</rest_filter>

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
class SessionProxyFilterTestCase(unittest.TestCase):
    def destroyDb(self, *a):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )
    # --------------------------------------------------------------
    def initServer(self):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml_server)
        self.server_service = pokerservice.PokerService(settings)
        self.server_service.disconnectAll = lambda: True
        self.server_service.startService()
        self.server_site = pokersite.PokerSite(settings, pokerservice.PokerRestTree(self.server_service))
        self.server_site.memcache = pokermemcache.MemcacheMockup.Client([])
        self.server_port = reactor.listenTCP(19482, self.server_site, interface="127.0.0.1")
    # --------------------------------------------------------------
    def initExplain(self):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml_explain)
        self.explain_service = pokerservice.PokerService(settings)
        self.explain_service.disconnectAll = lambda: True
        self.explain_service.startService()
        self.explain_site = pokersite.PokerSite(settings, pokerservice.PokerRestTree(self.explain_service))
        self.explain_site.memcache = pokermemcache.MemcacheMockup.Client([])
        self.explain_port = reactor.listenTCP(19481, self.explain_site, interface="127.0.0.1")        
    # --------------------------------------------------------------
    def initProxy(self):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml_proxy)
        self.proxy_service = pokerservice.PokerService(settings)
        self.proxy_service.disconnectAll = lambda: True
        self.proxy_service.startService()
        self.proxy_site = pokersite.PokerSite(settings, pokerservice.PokerRestTree(self.proxy_service))
        self.proxy_site.memcache = pokermemcache.MemcacheMockup.Client([])
        self.proxy_port = reactor.listenTCP(19480, self.proxy_site, interface="127.0.0.1")
    # --------------------------------------------------------------
    def setUp(self):
        testclock._seconds_reset()
        pokermemcache.memcache = pokermemcache.MemcacheMockup
        pokermemcache.memcache_singleton = {}
        pokermemcache.memcache_singleton_expiration = {}
        pokermemcache.memcache_singleton_log = []
        self.destroyDb()
        self.initServer()
        self.initExplain()
        self.initProxy()        
    # --------------------------------------------------------------
    def tearDownServer(self):
        self.server_site.stopFactory()
        d = self.server_service.stopService()
        d.addCallback(lambda x: self.server_port.stopListening())
        return d
    # --------------------------------------------------------------
    def tearDownExplain(self):
        self.proxy_site.stopFactory()
        d = self.explain_service.stopService()
        d.addCallback(lambda x: self.explain_port.stopListening())
        return d
    # --------------------------------------------------------------
    def tearDownProxy(self):
        self.proxy_site.stopFactory()
        d = self.proxy_service.stopService()
        d.addCallback(lambda x: self.proxy_port.stopListening())
        return d
    # --------------------------------------------------------------
    def tearDown(self):
        d = defer.DeferredList((
            self.tearDownServer(),
            self.tearDownExplain(),
            self.tearDownProxy()            
        ))
        d.addCallback(self.destroyDb)
        d.addCallback(lambda x: reactor.disconnectAll())
        return d
    # --------------------------------------------------------------
    def test01_ping_proxy(self):
        """
        Ping to the proxy.
        """
        d = client.getPage(
            "http://127.0.0.1:19480/POKER_REST?uid=1bebebaffe&auth=deadbeef",
            postdata='{"type": "PacketPing"}'
        )
        def checkPing(result):
            self.assertEqual('[]', str(result))
        d.addCallback(checkPing)
        return d
    # --------------------------------------------------------------
    def test02_tableJoin(self):
        """
        Join a table thru a proxy.
        """
        uid = '1bebebaffe'
        session = 'deadbeef'
        resthost = ('127.0.0.1', 19481, '/POKER_REST')
        self.proxy_site.memcache.set(uid, resthost)
        d = client.getPage(
            "http://127.0.0.1:19480/POKER_REST?uid=%s&auth=%s" % (uid, session),
            postdata='{"type":"PacketPokerTableJoin","game_id":1}'
        )
        def checkTable(result):
            packets = json.loads(result)
            self.assertEqual('PacketPokerTable', packets[0]['type'])
            self.assertEqual('Table1', packets[0]['name'])
            self.assertEqual(resthost, self.proxy_site.memcache.get(uid))
            set_uid_log = [v for (l, (k, v, t)) in self.proxy_site.memcache.log if k == uid]
            self.assertFalse(('127.0.0.1', 19482, '/POKER_REST') in set_uid_log)
        d.addCallback(checkTable)
        return d
    # --------------------------------------------------------------
    def test03_tableJoinNoRestHostExplain(self):
        """
        Join a table thru an explain server without reshost being set for the session.
        """
        uid = '1bebebaffe'
        session = 'deadbeef'
        resthost = ('127.0.0.1', 19481, '/POKER_REST')
        d = client.getPage(
            "http://127.0.0.1:19481/POKER_REST?uid=%s&auth=%s" % (uid, session),
            postdata='{"type":"PacketPokerTableJoin","game_id":1}'
        )
        def checkTable(result):
            packets = json.loads(result)
            self.assertEqual('PacketPokerTable', packets[0]['type'])
            self.assertEqual('Table1', packets[0]['name'])
            self.assertEqual(resthost, self.proxy_site.memcache.get(uid))
            set_uid_log = [v for (l, (k, v, t)) in self.proxy_site.memcache.log if k == uid]
            self.assertFalse(('127.0.0.1', 19482, '/POKER_REST') in set_uid_log)
        d.addCallback(checkTable)
        return d
    # --------------------------------------------------------------
    def test04_tableJoinNoRestHostProxy(self):
        """
        Join a table thru a proxy server without reshost being set for the session.
        """
        uid = '1bebebaffe'
        session = 'deadbeef'
        resthost = ('127.0.0.1', 19481, '/POKER_REST')
        d = client.getPage(
            "http://127.0.0.1:19480/POKER_REST?uid=%s&auth=%s" % (uid, session),
            postdata='{"type":"PacketPokerTableJoin","game_id":1}'
        )
        def checkTable(result):
            packets = json.loads(result)
            self.assertEqual('PacketPokerTable', packets[0]['type'])
            self.assertEqual('Table1', packets[0]['name'])
            self.assertEqual(resthost, self.proxy_site.memcache.get(uid))
            set_uid_log = [v for (l, (k, v, t)) in self.proxy_site.memcache.log if k == uid]
            self.assertFalse(('127.0.0.1', 19482, '/POKER_REST') in set_uid_log)
        d.addCallback(checkTable)
        return d    

################################################################################

def GetTestSuite():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test02"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(SessionProxyFilterTestCase))
    return suite

def Run():
    return runner.TrialRunner(
        reporter.TextReporter,
        tracebackFormat='default',
    ).run(GetTestSuite())

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
