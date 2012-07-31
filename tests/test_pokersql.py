#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Loic Dachary <loic@dachary.org>
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

import unittest, sys, os
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))
sys.path.insert(1, path.join(TESTS_PATH, "../../common"))

from config import config
import sqlmanager

settings_xml_server = """<?xml version="1.0" encoding="UTF-8"?>
<server verbose="3" admin="yes">

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
    'engine_path': config.test.engine_path,
    'mysql_command': config.test.mysql.command
}

from pokernetwork import pokersql
from pokernetwork import pokernetworkconfig

class SqlTestCase(unittest.TestCase):

    def destroyDb(self, *a):
        sqlmanager.query("DROP DATABASE IF EXISTS %s" % (config.test.mysql.database,),
            user=config.test.mysql.root_user.name,
            password=config.test.mysql.root_user.password,
            host=config.test.mysql.host
        )

    def setUp(self):
        self.destroyDb()
        
    def tearDown(self):
        self.destroyDb()

    def test01_getPath(self):
        self.assertTrue("poker.server.xml" in pokersql.getPath(['a/b/foo.bar']))
        self.assertTrue("config.xml" in pokersql.getPath(['a/b/config.xml']))

    def test02_getSettings(self):
        settings = pokersql.getSettings(path.join(TESTS_PATH, 'pokersql.xml'))
        self.assertEquals('true', settings.headerGet("/server/@admin"))
        caught = False
        try:
            pokersql.getSettings(path.join(TESTS_PATH, 'pokersqlfail.xml'))
        except AssertionError, e:
            self.assertTrue('enable' in str(e))
            caught = True
        self.assertTrue(caught)

    def test03_runQuery(self):
        settings = pokernetworkconfig.Config([])
        settings.loadFromString(settings_xml_server)
        #
        # return selected rows
        #
        value = '4242'
        os.environ['QUERY_STRING'] = 'query=select%20' + value + '&output=rows'
        output = pokersql.runQuery(settings)
        self.assertTrue('Content-type:' in output, output)
        self.assertTrue(value in output, output)
        #
        # return the number of affected rows
        #
        os.environ['QUERY_STRING'] = 'query=select%200' + value
        output = pokersql.runQuery(settings)
        self.assertTrue('Content-type:' in output, output)
        self.assertTrue('\n1' in output, output)
        os.environ['QUERY_STRING'] = 'query=select%200' + value + '&output=rowcount'
        output = pokersql.runQuery(settings)
        self.assertTrue('Content-type:' in output, output)
        self.assertTrue('\n1' in output, output)
        #
        # return the latest autoincrement
        #
        os.environ['QUERY_STRING'] = 'query=INSERT%20INTO%20messages()VALUES()&output=lastrowid'
        output = pokersql.runQuery(settings)
        self.assertTrue('Content-type:' in output, output)
        self.assertTrue('\n1' in output, output)
        os.environ['QUERY_STRING'] = 'query=INSERT%20INTO%20messages()VALUES()&output=lastrowid'
        output = pokersql.runQuery(settings)
        self.assertTrue('Content-type:' in output, output)
        self.assertTrue('\n2' in output, output)

    def test04_run(self):
        self.assertEquals("Content-type: text/plain\n\n", pokersql.run([path.join(TESTS_PATH, 'pokersql.xml')]))
        
#--------------------------------------------------------------
def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SqlTestCase))
    return suite
    
#--------------------------------------------------------------
def Run(verbose = 1):
    return unittest.TextTestRunner(verbosity=verbose).run(GetTestSuite())
    
#--------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
