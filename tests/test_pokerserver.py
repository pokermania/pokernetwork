#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# more information about the above line at http://www.python.org/dev/peps/pep-0263/
#
# Copyright (C) 2009 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
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
import sys, os, tempfile, shutil, exceptions, libxml2
from os import path
from twisted.internet import defer

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from config import config

# environ needed because makeService would overwrite the root_logger
# setting if it was not set
os.environ['LOG_LEVEL'] = '10'
from log_history import log_history

import sqlmanager

import twisted
from twisted.trial import unittest, runner, reporter
from pokernetwork.pokerserver import makeService, makeApplication
from pokernetwork.pokerserver import run as pokerServerRun
from twisted.application.internet import SSLServer
from twisted.application.internet import TCPServer
from twisted.web.server import Site as TwistedSite
from twisted.conch.ssh.transport import SSHServerTransport
from pokernetwork.pokerservice import PokerService, PokerRestTree, PokerFactoryFromPokerService, SSLContextFactory
from pokernetwork.pokersite import PokerSite
from pokernetwork.pokertable import PokerTable

ssl_factory_str = "<<class 'twisted.internet.ssl.Port'> of pokernetwork.pokerservice.PokerFactoryFromPokerService on %d>"
ssl_site_str = "<<class 'twisted.internet.ssl.Port'> of pokernetwork.pokersite.PokerSite on %d>"
ssl_web_site_str = "<<class 'twisted.internet.ssl.Port'> of twisted.web.server.Site on %d>"
 
if twisted.version.major >= 11:
    ssl_factory_str = ssl_site_str = ssl_web_site_str = "<<class 'twisted.internet.tcp.Port'> of twisted.protocols.tls.TLSMemoryBIOFactory on %d>"

    
settings_xml_server_manhole = """\
<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

  <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />
  <table name="Table2" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />

  <listen tcp="19481" manhole="%%(manhole_port)i" />
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

# Dummy CERT borrowed from Debian's snake-oil certificate.  Including it
# here since I can't assume what distribution I am on.

snake_oil_cert = """-----BEGIN CERTIFICATE-----
MIIDKzCCApQCCQDEKuqSPjfcEDANBgkqhkiG9w0BAQUFADCB2TELMAkGA1UEBhMC
WFgxKjAoBgNVBAgTIVRoZXJlIGlzIG5vIHN1Y2ggdGhpbmcgb3V0c2lkZSBVUzET
MBEGA1UEBxMKRXZlcnl3aGVyZTEOMAwGA1UEChMFT0NPU0ExPDA6BgNVBAsTM09m
ZmljZSBmb3IgQ29tcGxpY2F0aW9uIG9mIE90aGVyd2lzZSBTaW1wbGUgQWZmYWly
czEXMBUGA1UEAxMObWFwbGUuc2ZsYy12cG4xIjAgBgkqhkiG9w0BCQEWE3Jvb3RA
bWFwbGUuc2ZsYy12cG4wHhcNMDkwMTAyMTg1NzA0WhcNMDkwMjAxMTg1NzA0WjCB
2TELMAkGA1UEBhMCWFgxKjAoBgNVBAgTIVRoZXJlIGlzIG5vIHN1Y2ggdGhpbmcg
b3V0c2lkZSBVUzETMBEGA1UEBxMKRXZlcnl3aGVyZTEOMAwGA1UEChMFT0NPU0Ex
PDA6BgNVBAsTM09mZmljZSBmb3IgQ29tcGxpY2F0aW9uIG9mIE90aGVyd2lzZSBT
aW1wbGUgQWZmYWlyczEXMBUGA1UEAxMObWFwbGUuc2ZsYy12cG4xIjAgBgkqhkiG
9w0BCQEWE3Jvb3RAbWFwbGUuc2ZsYy12cG4wgZ8wDQYJKoZIhvcNAQEBBQADgY0A
MIGJAoGBAO0t+HjxiiliSHO9kge943+cXHGCtJp4/RPpHDN7hbpblY+FYCjuCmW/
/m2G59aMMl2Uwj1BO8cDwdGDtkNV21vcIo0siSD9VREFiYcLthaOK98muqD+Tfqa
MuGzZyui1RKuirCZzqyJPS2SXOtWSXUW8YQa75y/o4vcQSWWZ3VDAgMBAAEwDQYJ
KoZIhvcNAQEFBQADgYEApx7Q+PzLgdJu7OQJ776Kr+EI+Ho03pM5Nb5e26P5ZL6h
hk+gRLfBt8q3bihx4qjBSOpx1Qxq+BAMg6SAkDzkz+tN2CSr/vv2uuc26cDaf1co
oKCay2gMThIoURl+FSPeWAraGWbrcVy9ctoCipxMza9fn42dbn9OHxP/M+0qgvY=
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDtLfh48YopYkhzvZIHveN/nFxxgrSaeP0T6Rwze4W6W5WPhWAo
7gplv/5thufWjDJdlMI9QTvHA8HRg7ZDVdtb3CKNLIkg/VURBYmHC7YWjivfJrqg
/k36mjLhs2crotUSroqwmc6siT0tklzrVkl1FvGEGu+cv6OL3EEllmd1QwIDAQAB
AoGBAL4ws+QABIOE/YZaSKSOn8Rv1S1s23hXdtGlh2i9L5It6LOrB14q7AmFuPeJ
S5We3LBwHoZSLiY7nAtvLBO44GmwpSiJuLaI0z/7YIqkS6KjiDy1GFdQ5IEaRzxK
nyDcvES4h4QdOa/UeMEWg8TmasEoG3Wm3+aZt5KRz57HQQJRAkEA/uN0aw+1jqVP
YKbG89k7DEdNOdfgLjFofXruwXPfQmEFNg3Vp5ke1SeaR0tzYDXgZ5fDlwnR0EgA
HrR0om3PKwJBAO42vxdAVjrfMt0ws0wTmKS7mLlY8p7dKVKKIwP6F2b/61QyEX7z
czjyBaegw8qbX93OD0g2TETms73Py4WFJkkCQBV97FUSsAZlHfpSVbg9+uKgKHzW
HQsIE31xHiylro+USrIyHG/TU2w5uKKGVCYqpM9XVqCnrU9Yotnz8Vm41J0CQQCf
VccjikkjP8AJ61VCgakMJt7UuwYt9Mh7CSK6ukGFB5Ek1AiX3ccoQ9o8cXAEyUCq
X/Yg2xDQ1W9Mev0q5hDhAkBKSJF0V/24bz27z1yUSzHRHO3FAKXepkR81g6IRl41
r9nOQTOBo04TLBXtyP+o7GFNzBjEm6fVaqwk5SVsdQ+t
-----END RSA PRIVATE KEY-----
"""
settings_xml_server_open_options = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="6" ping="300000" autodeal="yes" simultaneous="4" chat="yes" >
  <delays autodeal="20" round="0" position="0" showdown="0" autodeal_max="1" finish="0" messages="60" />

  <table name="Table1" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />
  <table name="Table2" variant="holdem" betting_structure="100-200_2000-20000_no-limit" seats="10" player_timeout="60" currency_serial="1" />

  <listen tcp="19481" %%(listen_options)s />
  <resthost host="127.0.0.1" port="19481" path="/POKER_REST" />

  <cashier acquire_timeout="5" pokerlock_queue_timeout="30" user_create="yes" />
  <database
    host="%(dbhost)s" name="%(dbname)s"
    user="%(dbuser)s" password="%(dbuser_password)s"
    root_user="%(dbroot)s" root_password="%(dbroot_password)s"
    schema="%(tests_path)s/../database/schema.sql"
    command="%(mysql_command)s" />
  <path>%(engine_path)s/conf %(tests_path)s/conf %%(additional_path)s</path>
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


class PokerServerMakeServiceManholeTestCase(unittest.TestCase):
    def setUp(self):
        log_history.reset()
        self.tmpdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tmpdir, "poker.server.xml")
        f = open(self.filename, "w")
        self.manhole_port = 33333
        f.write(settings_xml_server_manhole % {'manhole_port': self.manhole_port})
        f.close()
        self.service = makeService(self.filename)
        self.service.startService()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        d = self.service.stopService()
        return d

    def test01_manhole(self):
        self.assertEquals(self.service.namedServices.keys(), ['manhole'])
        manhole = self.service.getServiceNamed('manhole')
        self.assertNotEqual(None, manhole)
        self.assertEqual(self.manhole_port, manhole._port.port)
        self.assertEqual('127.0.0.1', manhole._port.interface)
        self.assertEqual(SSHServerTransport, manhole._port.factory.protocol)
        self.assertEquals(manhole._port.connected, 1)
        self.assertEquals(manhole.parent, self.service)
        self.failUnless(manhole.running)

class PokerServerMakeServiceCoverageTestCase(unittest.TestCase):
    def setupDb(self):
        sqlmanager.setup_db(
            TESTS_PATH + "/../database/schema.sql", (
                ("INSERT INTO tableconfigs (name, variant, betting_structure, seats, currency_serial) VALUES (%s, 'holdem', %s, 10, 1)", (
                    ('Table1','100-200_2000-20000_no-limit'),
                    ('Table2','100-200_2000-20000_no-limit'),
                )),
                ("INSERT INTO tables (resthost_serial, tableconfig_serial) VALUES (%s, %s)", (
                    (1, 1),
                    (1, 2),
                )),
            ),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host,
            port=config.test.mysql.port,
            database=config.test.mysql.database
        )

    def setUp(self):
        log_history.reset()
        self.setupDb()
        self.tmpdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tmpdir, "poker.server.xml")

    def createService(self):
        self.service = makeService(self.filename)
        self.service.startService()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        d = self.service.stopService() if hasattr(self, 'service') else defer.succeed(None) 
        return d

    def createConfig(self, optionsDict):
        configFH = open(self.filename, "w")
        configFH.write(settings_xml_server_open_options % optionsDict)
        configFH.close()

    def createPemFile(self):
        pemFile = os.path.join(self.tmpdir, "poker.pem")
        pemFH = open(pemFile, "w")
        pemFH.write(snake_oil_cert)
        pemFH.close()

    def test00_missingSettingsFile(self):
        caughtIt = False
        try:
            self.createService()
            self.fail("previous line should have thrown exception")
        except exceptions.SystemExit, e:
            self.assertEquals(e.__str__(), "1")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")

    def xtest01_emptySettingsFile(self):
        f = open(self.filename, "w")
        f.close()
        caughtIt = False
        try:
            self.createService()
            self.fail("previous line should have thrown exception")
        except libxml2.parserError, e:
            self.assertEquals(e.__str__(),'xmlParseFile() failed')
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")

    def test02_tcpSsl_hasSSL(self):
        self.createConfig({'listen_options': 'tcp_ssl="3234"', 'additional_path': self.tmpdir})
        self.createPemFile()

        self.createService()

        # Only named service that we could possibly expect is manhole, and
        # that's not turned on here.  Hence:
        self.assertEquals(self.service.namedServices, {})

        self.assertEquals(len(self.service.services), 3)
        for service in self.service.services:
            self.assertEquals(service.parent, self.service)
            if isinstance(service, PokerService):
                # self.assertEquals(len(service.tables.keys()), 2)
                # self.failUnless(isinstance(service.tables[1], PokerTable))
                # self.failUnless(isinstance(service.tables[2], PokerTable))
                pass
            elif isinstance(service, TCPServer):
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokerservice.PokerFactoryFromPokerService on") == 0)
                self.failUnless(service._port.port > 1024)
                self.assertNotEquals(service._port.port, 3234)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, SSLServer):
                self.failUnless(isinstance(service.args[1], PokerFactoryFromPokerService))
                self.failUnless(isinstance(service.args[2], SSLContextFactory))
                self.assertEquals(service._port.__str__(), ssl_factory_str % 3234)
                self.assertEquals(service._port.port, 3234)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            else:
                self.fail("Unknown service found in multiservice list")

    def test03_tcpSsl_hasSSL_noPemFile(self):
        self.createConfig({'listen_options': 'tcp_ssl="3234"', 'additional_path': self.tmpdir})
        caughtIt = False
        try:
            self.createService()
            self.fail("previous line should have thrown exception")
        except Exception, ee:
            self.assertEquals(str(ee),"no poker.pem found in the setting's server path")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")

    def test04_httpSSL_hasSSL_noPemFile(self):
        self.createConfig({'listen_options': 'http_ssl="3234"', 'additional_path': self.tmpdir})
        caughtIt = False
        try:
            self.createService()
            self.fail("previous line should have thrown exception")
        except Exception, ee:
            self.assertEquals(str(ee), "no poker.pem found in the setting's server path")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")

    def test05_httpSSL_hasSSL(self):
        self.createConfig({'listen_options': 'http_ssl="9356"', 'additional_path': self.tmpdir})
        self.createPemFile()

        self.createService()

        # Only named service that we could possibly expect is manhole, and
        # that's not turned on here.  Hence:
        self.assertEquals(self.service.namedServices, {})

        self.assertEquals(len(self.service.services), 3)
        for service in self.service.services:
            self.assertEquals(service.parent, self.service)
            if isinstance(service, PokerService):
                # self.assertEquals(len(service.tables.keys()), 2)
                # self.failUnless(isinstance(service.tables[1], PokerTable))
                # self.failUnless(isinstance(service.tables[2], PokerTable))
                pass
            elif isinstance(service, TCPServer):
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokerservice.PokerFactoryFromPokerService on") == 0)
                self.failUnless(service._port.port > 1024)
                self.assertNotEquals(service._port.port, 9356)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, SSLServer):
                self.failUnless(isinstance(service.args[1], TwistedSite))
                self.failUnless(isinstance(service.args[2], SSLContextFactory))
                self.assertTrue(service._port.__str__() in (ssl_site_str % 9356, ssl_web_site_str % 9356))                
                self.assertEquals(service._port.port, 9356)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            else:
                self.fail("Unknown service found in multiservice list")

    def test06_restSSL_hasSSL_noPemFile(self):
        self.createConfig({'listen_options': 'rest_ssl="10234"', 'additional_path': self.tmpdir})
        caughtIt = False
        try:
            self.createService()
            self.fail("previous line should have thrown exception")
        except Exception, ee:
            self.assertEquals(str(ee),"no poker.pem found in the setting's server path")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")

    def test07_restSSL_hasSSL(self):
        self.createConfig({'listen_options': 'rest_ssl="10234"', 'additional_path': self.tmpdir})
        self.createPemFile()

        self.createService()

        # Only named service that we could possibly expect is manhole, and
        # that's not turned on here.  Hence:
        self.assertEquals(self.service.namedServices, {})

        self.assertEquals(len(self.service.services), 3)
        for service in self.service.services:
            self.assertEquals(service.parent, self.service)
            if isinstance(service, PokerService):
                # self.assertEquals(len(service.tables.keys()), 2)
                # self.failUnless(isinstance(service.tables[1], PokerTable))
                # self.failUnless(isinstance(service.tables[2], PokerTable))
                pass
            elif isinstance(service, TCPServer):
                self.assertTrue(0 == service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokerservice.PokerFactoryFromPokerService on"))
                self.failUnless(service._port.port > 1024)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, SSLServer):
                self.failUnless(isinstance(service.args[1], PokerSite))
                self.failUnless(isinstance(service.args[1].resource, PokerRestTree))
                self.failUnless(isinstance(service.args[2], SSLContextFactory))
                self.assertTrue(service._port.__str__() in (ssl_site_str % 10234, ssl_web_site_str % 10234))
                self.assertEquals(service._port.port, 10234)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            else:
                self.fail("Unknown service found in multiservice list")

    def test08_plainREST(self):
        self.createConfig({'listen_options': 'rest="11944"', 'additional_path': self.tmpdir})
        self.createService()

        # Only named service that we could possibly expect is manhole, and
        # that's not turned on here.  Hence:
        self.assertEquals(self.service.namedServices, {})

        self.assertEquals(len(self.service.services), 3)
        count = 0
        for service in self.service.services:
            self.assertEquals(service.parent, self.service)
            if isinstance(service, PokerService):
                count += 1
                # self.assertEquals(len(service.tables.keys()), 2)
                # self.failUnless(isinstance(service.tables[1], PokerTable))
                # self.failUnless(isinstance(service.tables[2], PokerTable))
                pass
            elif isinstance(service, TCPServer) and service._port.port == 11944:
                count += 1
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokersite.PokerSite on 11944>") == 0)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, TCPServer):
                count += 1
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokerservice.PokerFactoryFromPokerService on") == 0)
                self.failUnless(service._port.port > 1024)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            else:
                self.fail("Unknown service found in multiservice list")
        self.assertEquals(len(self.service.services), count)

    def test09_plainHTTP(self):
        self.createConfig({'listen_options': 'http="10235"', 'additional_path': self.tmpdir})
        self.createService()

        # Only named service that we could possibly expect is manhole, and
        # that's not turned on here.  Hence:
        self.assertEquals(self.service.namedServices, {})

        self.assertEquals(len(self.service.services), 3)
        count = 0
        for service in self.service.services:
            self.assertEquals(service.parent, self.service)
            if isinstance(service, PokerService):
                count += 1
                # self.assertEquals(len(service.tables.keys()), 2)
                # self.failUnless(isinstance(service.tables[1], PokerTable))
                # self.failUnless(isinstance(service.tables[2], PokerTable))
                pass
            elif isinstance(service, TCPServer) and service._port.port == 10235:
                count += 1
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of twisted.web.server.Site on 10235>") == 0)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, TCPServer):
                count += 1
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokerservice.PokerFactoryFromPokerService on") == 0)
                self.failUnless(service._port.port > 1024)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            else:
                self.fail("Unknown service found in multiservice list")
        self.assertEquals(len(self.service.services), count)

    def test10_everythingOn(self):
        #"19481"
        self.createConfig({
            'listen_options':'http="7658" http_ssl="6675" rest="5563" rest_ssl="7765" tcp_ssl="9123" manhole="10143"',
            'additional_path': self.tmpdir
        })
        self.createPemFile()
        self.createService()

        self.assertEquals(self.service.namedServices.keys(), ['manhole'])
        self.failUnless(isinstance(self.service.namedServices['manhole'], TCPServer))

        # Check Manhole first
        manhole = self.service.getServiceNamed('manhole')
        self.assertNotEqual(None, manhole)
        self.assertEqual(10143, manhole._port.port)
        self.assertEqual('127.0.0.1', manhole._port.interface)
        self.assertEqual(SSHServerTransport, manhole._port.factory.protocol)
        self.assertEquals(manhole._port.connected, 1)
        self.assertEquals(manhole.parent, self.service)
        self.failUnless(manhole.running)

        self.assertEquals(len(self.service.services), 8)
        count = 0
        for service in self.service.services:
            self.assertEquals(service.parent, self.service)
            if isinstance(service, PokerService):
                count += 1
                # self.assertEquals(len(service.tables.keys()), 2)
                # self.failUnless(isinstance(service.tables[1], PokerTable))
                # self.failUnless(isinstance(service.tables[2], PokerTable))
                pass
            elif isinstance(service, TCPServer) and service._port.port == 19481:
                count += 1
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokerservice.PokerFactoryFromPokerService on 19481") == 0)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, TCPServer) and service._port.port == 10143:
                count += 1
                self.assertEquals(
                    str(service._port),
                    "<<class 'twisted.internet.tcp.Port'> of twisted.conch.manhole_ssh.ConchFactory on 10143>"
                )
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '127.0.0.1')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, SSLServer) and service._port.port == 9123:
                count += 1
                self.failUnless(isinstance(service.args[1], PokerFactoryFromPokerService))
                self.failUnless(isinstance(service.args[2], SSLContextFactory))
                self.assertEquals(service._port.__str__(), ssl_factory_str % 9123)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, SSLServer) and service._port.port == 6675:
                count += 1
                self.failUnless(isinstance(service.args[1], TwistedSite))
                self.failUnless(isinstance(service.args[2], SSLContextFactory))
                self.assertTrue(service._port.__str__() in (ssl_site_str % 6675, ssl_web_site_str % 6675))
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, SSLServer) and service._port.port == 7765:
                count += 1
                self.failUnless(isinstance(service.args[1], PokerSite))
                self.failUnless(isinstance(service.args[1].resource, PokerRestTree))
                self.failUnless(isinstance(service.args[2], SSLContextFactory))
                self.assertEquals(service._port.__str__(), ssl_site_str % 7765)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, TCPServer) and service._port.port == 5563:
                count += 1
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of pokernetwork.pokersite.PokerSite on 5563>") == 0)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            elif isinstance(service, TCPServer) and service._port.port == 7658:
                count += 1
                self.failUnless(service._port.__str__().find("<<class 'twisted.internet.tcp.Port'> of twisted.web.server.Site on 7658>") == 0)
                self.assertEquals(service._port.port, service._port._realPortNumber) 
                self.assertEquals(service._port.interface, '')
                self.assertEquals(service._port.connected, 1)
                self.assertNotEquals(service._port.socket, None)
                self.failUnless(service.running)
            else:
                self.fail("Unknown service found in multiservice list")
        self.assertEquals(len(self.service.services), count)

class PokerServerMakeApplicationCoverageTestCase(unittest.TestCase):

    def setUp(self):
        log_history.reset()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test00_missingConfigFileGivenOnCLI(self):
        doesNotExistFile = os.path.join(self.tmpdir, "thisdoesnotexist.xml")
        caughtIt = False
        try:
            makeApplication([doesNotExistFile])
            self.fail("previous line should have thrown exception")
        except exceptions.SystemExit, e:
            self.assertEquals(e.__str__(), "1")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")

    def test01_missingConfigFileGivenOnCLI_sysVersionDitched(self):
        doesNotExistFile = os.path.join(self.tmpdir, "doesnotexists.xml")
        saveSysVersion = sys.version
        sys.version = "BMK"
        caughtIt = False
        try:
            makeApplication([doesNotExistFile])
            self.fail("previous line should have thrown exception")
        except exceptions.SystemExit, e:
            self.assertEquals(e.__str__(), "1")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")
        sys.version = saveSysVersion

    def test02_validConfig(self):
        configFile = os.path.join(self.tmpdir, "ourconfig.xml")
        configFH = open(configFile, "w")
        configFH.write(settings_xml_server_open_options % { 'listen_options': '', 'additional_path': ''})
        configFH.close()
        application =  makeApplication([configFile])
        from twisted.python.components import Componentized
        self.failUnless(isinstance(application, Componentized))


class PokerServerRunCoverageTestCase(unittest.TestCase):
    def destroyDb(self):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )

    def setUp(self):
        log_history.reset()
        self.destroyDb()
        self.tmpdir = tempfile.mkdtemp()
        

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        

    def test00_missingConfigFileGivenOnCLI(self):
        doesNotExistFile = os.path.join(self.tmpdir, "thisdoesnotexist.xml")
        caughtIt = False
        try:
            pokerServerRun([doesNotExistFile])
            self.fail("previous line should have thrown exception")
        except exceptions.SystemExit, e:
            self.assertEquals(e.__str__(), "1")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")
        self.assertTrue(log_history.search("reactor already installed"))
        
    def test01_missingConfigFileGivenOnCLI_forceReactorInstall(self):
        import platform
        from twisted.internet import epollreactor
        doesNotExistFile = os.path.join(self.tmpdir, "thisdoesnotexist.xml")
        caughtIt = False

        saveSystem = None 
        if platform.system() == "Windows":
            def fakeSystem(): return "NotWindowsButReallyIs"
            saveSystem, platform.system = platform.system, fakeSystem

        reactorCalled = [False]
        def reactorFake(): reactorCalled[0] = True
        saveReactor, epollreactor.install = epollreactor.install, reactorFake

        reactorModulesSave = sys.modules['twisted.internet.reactor']
        del sys.modules['twisted.internet.reactor']

        try:
            pokerServerRun([doesNotExistFile])
            self.fail("previous line should have thrown exception")
        except exceptions.SystemExit, e:
            self.assertEquals(e.__str__(), "1")
            caughtIt = True
        self.failUnless(caughtIt, "Should have caught an Exception")
        
        self.assertTrue(log_history.search("installing epoll reactor"))

        self.failUnless(reactorCalled[0], "epoll reactor should have been installed")

        if saveSystem: platform.system = saveSystem
        epollreactor.install = saveReactor
        sys.modules['twisted.internet.reactor'] = reactorModulesSave


def GetTestSuite():
    loader = runner.TestLoader()
    # loader.methodPrefix = "_test"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(PokerServerMakeServiceManholeTestCase))
    suite.addTest(loader.loadClass(PokerServerRunCoverageTestCase))
    suite.addTest(loader.loadClass(PokerServerMakeServiceCoverageTestCase))
    suite.addTest(loader.loadClass(PokerServerMakeApplicationCoverageTestCase))
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
