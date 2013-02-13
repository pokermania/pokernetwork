#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2008, 2009 Bradley M. Kuhn <bkuhn@ebb.org>
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

from twisted.trial import unittest, runner, reporter
import _mysql_exceptions
import warnings
import twisted.internet.base
from twisted.internet import reactor

twisted.internet.base.DelayedCall.debug = False
import libxml2
import re

verbose = int(os.environ.get('VERBOSE_T', '-1'))

from pokernetwork import pokerdatabase
from pokernetwork import pokernetworkconfig
from pokernetwork import version

import MySQLdb

actualSchemaFile = path.join(TESTS_PATH, "../database/schema.sql")

settings_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<server verbose="4">
  <database
    host="%(dbhost)s" name="%(dbname)s"
    user="%(dbuser)s" password="%(dbuser_password)s"
    root_user="%(dbroot)s" root_password="%(dbroot_password)s"
    schema="%(tests_path)s/../database/schema.sql"
    command="%(mysql_command)s" />
</server>
""" % {
    'dbhost': config.test.mysql.host,
    'dbname': config.test.mysql.database,
    'dbuser': config.test.mysql.user.name,
    'dbuser_password': config.test.mysql.user.password,
    'dbroot': config.test.mysql.root_user.name,
    'dbroot_password': config.test.mysql.root_user.password,
    'tests_path': TESTS_PATH,
    'mysql_command': config.test.mysql.command
}
settings_missing_schema_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<server verbose="4">
  <database
    host="%(dbhost)s" name="%(dbname)s"
    user="%(dbuser)s" password="%(dbuser_password)s"
    root_user="%(dbroot)s" root_password="%(dbroot_password)s"
    schema="/this/is/not/a/file/and/should/not/be/there/not-my-schema-go-away.sql"
    command="%(mysql_command)s" />
</server>
""" % {
    'dbhost': config.test.mysql.host,
    'dbname': config.test.mysql.database,
    'dbuser': config.test.mysql.user.name,
    'dbuser_password': config.test.mysql.user.password,
    'dbroot': config.test.mysql.root_user.name,
    'dbroot_password': config.test.mysql.root_user.password,
    'mysql_command': '/usr/bin/env mysql'
}
settings_root_both_users_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<server verbose="4">
  <database 
    host="%(dbhost)s" name="%(dbname)s"
    user="%(dbroot)s" password="%(dbroot_password)s"
    root_user="%(dbroot)s" root_password="%(dbroot_password)s"
    schema="%(tests_path)s/../database/schema.sql"
    command="%(mysql_command)s" />
</server>
""" % {
    'dbhost': config.test.mysql.host,
    'dbname': config.test.mysql.database,
    'dbroot': config.test.mysql.root_user.name,
    'dbroot_password': config.test.mysql.root_user.password,
    'tests_path': TESTS_PATH,
    'mysql_command': config.test.mysql.command
}
settings_missing_root_users_xml = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="4">
  <database
    host="%(dbhost)s"  name="%(dbname)s"
    user="%(dbuser)s" password="%(dbuser_password)s"
    schema="%(tests_path)s/../database/schema.sql"
    command="%(mysql_command)s" />
</server>
""" % {
    'dbhost': config.test.mysql.host,
    'dbname': config.test.mysql.database,
    'dbuser': config.test.mysql.user.name,
    'dbuser_password': config.test.mysql.user.password,
    'tests_path': TESTS_PATH,
    'mysql_command': '/usr/bin/env mysql'
}
class PokerDatabaseTestCase(unittest.TestCase):
    def destroyDb(self, *a):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )
    # ----------------------------------------------------------------------------
    def setUp(self):
        self.tearDown()
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml)
        self.settings = settings

        r = re.compile("""INSERT\s+INTO\s+server\s+\(\s*version\s*\)\s+VALUES\s*\("([\d\.]+)"\s*\)""", flags=re.I)
        infile = open(actualSchemaFile, "r")
        self.pokerdbVersion = "0.0.0"
        while infile:
            line = infile.readline()
            m = re.match(r, line)
            if m:
                self.pokerdbVersion = m.group(1)
                break
        infile.close()
        # We should be able to find the version number
        self.assertNotEquals(self.pokerdbVersion, "0.0.0")
    # ----------------------------------------------------------------------------
    def tearDown(self):
        try:
            self.db.close()
        except:
            pass
        try:
            settings = pokernetworkconfig.Config([])
            settings.loadFromString(settings_xml)
            parameters = settings.headerGetProperties("/server/database")[0]
            db = MySQLdb.connect(
                host = parameters["host"],
                port = int(parameters.get("port", '3306')),
                user = parameters["root_user"],
                passwd = parameters["root_password"],
                db = 'mysql'
            )
            try:
                db.query("REVOKE ALL PRIVILEGES, GRANT OPTION FROM '%s'" % parameters['user'])
                db.query("drop user '%s'" % parameters['user'])
            except:
                db.query("delete from user where user = '%s'" % parameters['user'])

            db.query("FLUSH PRIVILEGES")
            db.close()
        except Exception:
            assert("Unable to delete the user, " + parameters["user"] + "; some tests will fail incorrectly.")
        try: del self.db
        except: pass
        try: self.destroyDb()
        except: pass
    # ----------------------------------------------------------------------------
    def test01_upgrade(self):
        self.db = pokerdatabase.PokerDatabase(self.settings)
        self.db.setVersionInDatabase("0.0.0")
        self.db.version = version.Version("0.0.0")
        self.db.upgrade(path.join(TESTS_PATH, 'test_pokerdatabase/good'), False)
        self.assertEquals(self.db.getVersion(), self.pokerdbVersion)
    # ----------------------------------------------------------------------------
    def test02_dbVersionTooOld(self):
        class DummyMySQL:
            def get_server_info(self):
                return "3.2.5"
            def query(self, string):
                return string
            def close(self):
                pass
        def dummyConnect(host, port, user, passwd, db='mysql', reconnect=1):
            parameters = self.settings.headerGetProperties("/server/database")[0]
            if user == parameters['user'] and user != 'root':
                raise Exception("SqlError")
            else:
                return DummyMySQL()
        realconnect = MySQLdb.connect
        MySQLdb.connect = dummyConnect
        try:
            self.db = pokerdatabase.PokerDatabase(self.settings)
        except UserWarning, uw:
            self.assertEqual(uw.args[0], "PokerDatabase: MySQL server version is 3.2.5 but version >= 5.0 is required")
        finally:
            MySQLdb.connect = realconnect
    # ----------------------------------------------------------------------------
    def test03_schemaFileMissing(self):
        settings = pokernetworkconfig.Config([])
        settings.doc = libxml2.parseMemory(settings_missing_schema_xml,
                                           len(settings_missing_schema_xml))
        settings.header = settings.doc.xpathNewContext()
        self.settings = settings
        try:
            self.db = pokerdatabase.PokerDatabase(self.settings)
            assert("Schema file was missing so this line should not be reached.")
        except UserWarning, uw:
            self.assertEqual(uw.args[0], "PokerDatabase: schema /this/is/not/a/file/and/should/not/be/there/not-my-schema-go-away.sql file not found")
    # ----------------------------------------------------------------------------
    def test04_rootBothUsers(self):
        self.settings = pokernetworkconfig.Config([])
        self.settings.loadFromString(settings_root_both_users_xml)
        try:
            self.db = pokerdatabase.PokerDatabase(self.settings)
        except MySQLdb.OperationalError as oe:
            print self.settings.headerGetProperties('/server/database')[0]
            self.assertEquals(oe.args[0], 1396)
            self.assertEquals(oe.args[1], "Operation CREATE USER failed for 'root'@'%'")
        self.assertEquals(self.db.getVersion(), self.pokerdbVersion)
    # ----------------------------------------------------------------------------
    def test05_missingRootUser(self):
        self.settings = pokernetworkconfig.Config([])
        self.settings.loadFromString(settings_missing_root_users_xml)
        try:
            self.db = pokerdatabase.PokerDatabase(self.settings)
            assert False, "Root user information was missing so this line should not be reached."
        except MySQLdb.OperationalError, oe: # handle trouble
            self.assertEquals(oe.args[1], "Access denied for user 'pokernetwork'@'localhost' (using password: YES)")
            self.assertEquals(oe.args[0], 1045)
    # ----------------------------------------------------------------------------
    def test06_databaseAlreadyExists(self):
        """Test for when the database already exists"""
        self.settings = pokernetworkconfig.Config([])
        self.settings.loadFromString(settings_root_both_users_xml)
        parameters = self.settings.headerGetProperties("/server/database")[0]
        db = MySQLdb.connect(host = parameters["host"],
                             port = int(parameters.get("port", '3306')),
                             user = parameters["root_user"],
                             passwd = parameters["root_password"])
        db.query("CREATE DATABASE " + parameters["name"])
        db.close()
        self.db = pokerdatabase.PokerDatabase(self.settings)
        self.assertEquals(self.db.getVersion(), '1.0.5')
    # ----------------------------------------------------------------------------
    def test07_multipleRowsInVersionTable(self):
        """Test for when the database already exists"""
        import MySQLdb
        from pokernetwork.pokerdatabase import ExceptionUpgradeFailed

        settings = pokernetworkconfig.Config([])
        settings.doc = libxml2.parseMemory(settings_xml, len(settings_xml))
        settings.header = settings.doc.xpathNewContext()
        self.settings = settings
        parameters = settings.headerGetProperties("/server/database")[0]

        self.db = pokerdatabase.PokerDatabase(self.settings)

        self.db.db.query("DROP TABLE IF EXISTS server;")
        self.db.db.query("""CREATE TABLE server (version VARCHAR(16) NOT NULL) ENGINE=InnoDB CHARSET=utf8;""")
        self.db.db.query("""INSERT INTO server (version) VALUES ("1.1.0");""")
        self.db.db.query("""INSERT INTO server (version) VALUES ("1.2.0");""")
        try:
            self.db.setVersionInDatabase("1.3.0")
        except ExceptionUpgradeFailed, euf: # handle trouble
            self.assertEquals(euf.args[0], "UPDATE server SET version = '1.3.0': changed 2 rows, expected one or zero")
    # ----------------------------------------------------------------------------
    def test08_forceTestDatabaseTooOld(self):
        import pokernetwork.version
        ver = pokernetwork.version.Version("32767.32767.32767")
        realDBVersion = pokerdatabase.version
        pokerdatabase.version = ver

        settings = pokernetworkconfig.Config([])
        settings.doc = libxml2.parseMemory(settings_xml, len(settings_xml))
        settings.header = settings.doc.xpathNewContext()
        self.settings = settings
        parameters = settings.headerGetProperties("/server/database")[0]

        try:
            self.db = pokerdatabase.PokerDatabase(self.settings)
            self.db.checkVersion()
            assert("Should have gotten ExceptionDatabaseTooOld and this line should not have been reached.")
        except pokerdatabase.ExceptionDatabaseTooOld, edto:
            self.assertEquals(edto.args, ())
            pokerdatabase.version = realDBVersion  # Restore original version
    # ----------------------------------------------------------------------------
    def test09_forceTestPokerNetworkTooOld(self):
        settings = pokernetworkconfig.Config([])
        settings.doc = libxml2.parseMemory(settings_xml, len(settings_xml))
        settings.header = settings.doc.xpathNewContext()
        self.settings = settings
        parameters = settings.headerGetProperties("/server/database")[0]
        try:
            self.db = pokerdatabase.PokerDatabase(self.settings)
            import pokernetwork.version
            ver = pokernetwork.version.Version("32767.32767.32767")
            realDBVersion = self.db.version
            self.db.version = ver

            self.db.checkVersion()
            assert("Should have gotten ExceptionSoftwareTooOld and this line should not have been reached.")
        except pokerdatabase.ExceptionSoftwareTooOld, edto:
            self.assertEquals(edto.args, ())
            self.db.version = realDBVersion  # Restore original version
    # ----------------------------------------------------------------------------
    def test10_badUpgradeSqlFiles(self):
        self.db = pokerdatabase.PokerDatabase(self.settings)
        self.db.setVersionInDatabase("0.0.5")
        self.db.version = version.Version("0.0.5")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', _mysql_exceptions.Error)
                self.db.upgrade(path.join(TESTS_PATH, 'test_pokerdatabase/bad'), False)
        except pokerdatabase.ExceptionUpgradeFailed, euf:
            self.assertEquals(euf.args[0], "upgrade failed")
        self.assertEquals(self.db.getVersion(), "0.0.5")
    # ----------------------------------------------------------------------------
    def test11_confirmLiteralMethodPassThrough(self):
        """test11_confirmLiteralMethodPassThrough
        The method "literal" in the database class should simply pass
        through to the internal representation method of the same name."""
        class MockDatabaseWithOnlyLiteral():
            def literal(mdSelf, args): return "LITERAL TEST " + args

        self.db = pokerdatabase.PokerDatabase(self.settings)
        saveRealDb = self.db.db
        self.db.db = MockDatabaseWithOnlyLiteral()

        self.assertEquals(self.db.literal("ahoy hoy!"),  "LITERAL TEST ahoy hoy!")
        self.db.db = saveRealDb
        
# --------------------------------------------------------------------------------
def GetTestedModule():
    return pokerdatabase
  
# --------------------------------------------------------------------------------

def GetTestSuite():
    loader = runner.TestLoader()
    suite = loader.loadClass(PokerDatabaseTestCase)
    return suite

def Run():
    return runner.TrialRunner(
        reporter.TextReporter,
        tracebackFormat='default',
    ).run(GetTestSuite())

# --------------------------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
