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

import tempfile, shutil
import unittest, sys, os
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))
sys.path.insert(1, path.join(TESTS_PATH, "../../common"))

from config import config
import sqlmanager

# environ needed because makeService would overwrite the root_logger
# setting if it was not set
os.environ['LOG_LEVEL'] = '10'
from log_history import log_history

from twisted.internet import reactor, defer

from cStringIO import StringIO

settings_xml_server_open_options = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

  <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />
  <table name="Table2" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />

  <listen tcp="19481" %(listen_options)s />
  <resthost host="127.0.0.1" port="19481" path="/POKER_REST" />

  <cashier acquire_timeout="5" pokerlock_queue_timeout="30" user_create="yes" />
  <database name="pokernetworktest" host="localhost" user="pokernetworktest" password="pokernetwork"
            root_user="@MYSQL_TEST_DBROOT@" root_password="@MYSQL_TEST_DBROOT_PASSWORD@" schema="@srcdir@/../../database/schema.sql" command="@MYSQL@" />
  <path>.. ../@srcdir@ @POKER_ENGINE_PKGDATADIR@/conf @POKER_NETWORK_PKGSYSCONFDIR@ %(additional_path)s</path>
  <users temporary="BOT.*"/>
</server>
"""
# ------------------------------------------------------------    
class PokerServerRunTestCase(unittest.TestCase):
    def destroyDb(self, *a):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )
    # -------------------------------------------------------------------------
    def setUp(self):
        self.destroyDb()
        self.tmpdir = tempfile.mkdtemp()
    # -------------------------------------------------------------------------
    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        
    # -------------------------------------------------------------------------
    def holdStdout(self):
        self.saveSysout = sys.stdout
        sys.stdout = StringIO()
    # -------------------------------------------------------------------------
    def test01_validConfig_mockupStartApplication(self):
        """test01_validConfig_mockupStartApplication
        Test that the pokerserver application runs properly.  Since the
        reactor.run() is called by pokerserver's run(), this test might
        HANG INDEFINITELY for some types of test failures.  Unlikely but
        possible."""
        from pokernetwork.pokerserver import run as pokerServerRun

        from twisted.application import app
        configFile = os.path.join(self.tmpdir, "ourconfig.xml")
        configFH = open(configFile, "w")
        configFH.write(settings_xml_server_open_options % { 
            'listen_options': '', 
            'additional_path': self.tmpdir
        })
        configFH.close()

        def mockStartApplication(application, val):
            from twisted.python.components import Componentized
            self.failUnless(isinstance(application, Componentized))
            self.assertEquals(val, None)
        savedStartApplication = app.startApplication
        app.startApplication = mockStartApplication

        def doCallback(val):
            self.assertEquals(val, "done")
            app.startApplication = savedStartApplication
            reactor.stop()

        defferedStillRunningMeansReactorNotStarted = defer.Deferred()
        defferedStillRunningMeansReactorNotStarted.addCallback(doCallback)
        
        reactor.callLater(1, lambda: defferedStillRunningMeansReactorNotStarted.callback("done"))
        pokerServerRun([configFile])
# ------------------------------------------------------------    
class PokerServerLoadingSSLTestCase(unittest.TestCase):
    # ----------------------------------------------------------------
    def test01_openSSLMissing(self):
        """test01_openSSLMissing"""
        import sys

        for mod in ['OpenSSL', 'pokernetwork', 'pokerserver']:
            if sys.modules.has_key(mod): del sys.modules[mod]

        realImporter = __builtins__['__import__'] if type(__builtins__) is dict else __builtins__.__import__

        def failSSLImport(moduleName, *args, **kwargs):
            if moduleName == "OpenSSL":
                raise ImportError("SSL was imported")
            else:
                return realImporter(moduleName, *args, **kwargs)
        
        if type(__builtins__) is dict: __builtins__['__import__']  = failSSLImport
        else: __builtins__.__import__  = failSSLImport

        from pokernetwork import pokerserver as ps

        self.failIf(ps.HAS_OPENSSL, "HAS_OPENSSL should be False when OpenSSL.SSL is not available")

        if type(__builtins__) is dict: __builtins__['__import__']  = realImporter
        else: __builtins__.__import__  = realImporter
# ------------------------------------------------------------
def GetTestSuite():
    # loader.methodPrefix = "_test"
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PokerServerLoadingSSLTestCase))
    suite.addTest(unittest.makeSuite(PokerServerRunTestCase))
    return suite
# -----------------------------------------------------------------------------
def Run(verbose = 1):
    return unittest.TextTestRunner(verbosity=verbose).run(GetTestSuite())
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
