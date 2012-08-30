#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
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
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from twisted.trial import unittest, runner, reporter

from pokernetwork.pokerbotlogic import StringGenerator, NoteGenerator, PokerBot

class StringGeneratorTestCase(unittest.TestCase):

    def test_all(self):
        generator = StringGenerator("PREFIX")
        generator.command = "echo USERONE ; echo USERTWO"
        self.assertEqual("PREFIXUSERTWO", generator.getName())
        self.assertEqual(1, len(generator.pool))
        self.assertEqual("USERONE", generator.getPassword())
        self.assertEqual(0, len(generator.pool))
        generator.command = ""
        self.failUnlessRaises(UserWarning, generator.getName)
        
class NoteGeneratorTestCase(unittest.TestCase):

    def test_all(self):
        generator = NoteGenerator("printf 'one\ttwo\n' ; printf 'three\tfour\n'")
        self.assertEqual(['three', 'four'], generator.getNote())
        self.assertEqual(['one', 'two'], generator.getNote())
        generator.command = ""
        self.failUnlessRaises(UserWarning, generator.getNote)
        
# ----------------------------------------------------------------

def GetTestSuite():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test40"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(StringGeneratorTestCase))
    suite.addTest(loader.loadClass(NoteGeneratorTestCase))
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
