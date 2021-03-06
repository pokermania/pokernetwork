#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, 2008 Loic Dachary <loic@dachary.org>
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

import unittest, sys, os, shutil
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from pokernetwork import pokernetworkconfig

class PokerNetworkConfigTestCase(unittest.TestCase):
    
    #--------------------------------------------------------------
    def setUp(self):
        self.Config = pokernetworkconfig.Config([path.join(TESTS_PATH, 'conf')])
        shutil.copyfile(path.join(TESTS_PATH, '../conf/poker.server.xml.in'), path.join(TESTS_PATH, 'conf/poker.server.xml.tmp'))
    
    #--------------------------------------------------------------    
    def tearDown(self):
        del self.Config
        os.remove(path.join(TESTS_PATH, 'conf/poker.server.xml.tmp'))
        
    #--------------------------------------------------------------    
    def test_loadFromString(self):

        self.Config.loadFromString("""<?xml version="1.0" encoding="UTF-8"?><server></server>""")
        self.assertNotEqual(self.Config.header, None)

    #--------------------------------------------------------------    
    def test_load(self):
        self.assertEqual(True, self.Config.load("poker.server.xml.tmp"))
        pokernetworkconfig.Config.upgrades_repository = '@srcdir@'
        self.assertEqual(True, self.Config.load("poker.server.xml.tmp"))
        self.Config.checkVersion = lambda field, version, repository: False
        self.assertEqual(False, self.Config.load("poker.server.xml.tmp"))
        
    #--------------------------------------------------------------    
    def test_notify(self):
        def f(config): pass
        self.Config.loadFromString("""<?xml version="1.0" encoding="UTF-8"?><server name='value'></server>""")
        self.Config.notifyUpdates(f)
        self.Config.denotifyUpdates(f)
        self.Config.notifyUpdates(f)
        self.Config.headerSet("/server/@name", "othervalue")
        
#--------------------------------------------------------------
def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PokerNetworkConfigTestCase))
    return suite
    
#--------------------------------------------------------------
def GetTestedModule():
    return pokernetworkconfig
  
#--------------------------------------------------------------
def Run(verbose = 1):
    unittest.TextTestRunner(verbosity=verbose).run(GetTestSuite())
    
#--------------------------------------------------------------
if __name__ == '__main__':
    Run()
