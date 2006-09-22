#!/usr/bin/python2.4
# -*- mode: python -*-
#
# Copyright (C) 2006 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#  J.Jeannin <griim.work@gmail.com>
#

import sys, os
sys.path.insert(0, "./..")
sys.path.insert(0, "..")

from pokerui.pokerrenderer import PokerRenderer
from pokerui.pokerrenderer import LOBBY, IDLE, OUTFIT, QUIT, CASHIER, QUIT_DONE, TOURNAMENTS
from pokerui.pokerinterface import INTERFACE_YESNO

import unittest

#-----------------
class PokerInteractorsMockup:
    def __init__(self):
        pass

    def destroy(self):
        print "destroy interactors"

class PokerRendererMockup(PokerRenderer):
    def __init__(self):
	self.factory = PokerFactoryMockup()
	self.verbose = 3
	self.protocol = PokerProtocolMockup()
        self.state = IDLE
        self.stream_mode = True
        self.state_outfit = None
        self.interactors = PokerInteractorsMockup()

    def isSeated(self):
        return False

    def hideLobby(self):
        pass

    def showOutfit(self):
        pass

    def hideOutfit(self):
        pass

    def showLobby(self):
        pass

    def showYesNoBox(self, msg):
        print msg

    def showTournaments(self, *args):
        pass

    def queryTournaments(self):
        pass

    def queryLobby(self):
        pass

    def chatHide(self):
        pass
        
    def render(self, packet):
        print "render packet %s" % str(packet)

    def sendPacket(self, packet):
        print "sendPacket packet %s" % str(packet)

class PokerUserMockup:
    def __init__(self):
        pass

    def isLogged(self):
        return True
        
class PokerProtocolMockup:
    def __init__(self):
	self.packets = []
        self.user = PokerUserMockup()
        
    def schedulePacket(self, packet):
	self.packets.append(packet)

    def sendPacket(self, packet):
        print "protocol send packet %s" % str(packet)

    def getSerial(self):
        return 0
        
class PokerInterfaceMockup:
    def __init__(self):
	self.verbose = 3
        self.callbacks = {}
#        self.callbacks[INTERFACE_YESNO] = lambda: self.printInterfaceYesNo()

    def printInterfaceYesNo(self):
        print INTERFACE_YESNO
        
    def showMenu(self):
        pass

    def hideMenu(self):
        pass
    
    def chatShow(self):
        pass

    def registerHandler(self, key, func):
        self.callbacks[key] = func

class PokerFactoryMockup:
    def __init__(self):
	self.verbose = 3
	self.chat_config = {'max_chars': 80,
			    'line_length': 80}
        self.interface = PokerInterfaceMockup()

    def quit(self):
        print "factory quit"
        
class PokerPacketChatMockup:
    def __init__(self, message):
	self.message = message
	self.serial = 0
	self.game_id = 0

class PokerRendererTestCase(unittest.TestCase):
    
    # -----------------------------------------------------------------------------------------------------
    def setUp(self):
	self.renderer = PokerRendererMockup()
    
    # -----------------------------------------------------------------------------------------------------    
    def tearDown(self):
	self.renderer = None
        
    # -----------------------------------------------------------------------------------------------------    
    def test_StateQUITFromOUTFIT(self):
        self.renderer.state = OUTFIT
	self.assertEquals(self.renderer.state, OUTFIT)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, LOBBY)

    def test_StateQUITFromIDLE_YES(self):
        self.renderer.state = IDLE
	self.assertEquals(self.renderer.state, IDLE)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = True)
	self.assertEquals(self.renderer.state, QUIT_DONE)
        
    def test_StateQUITFromIDLE_NO(self):
        self.renderer.state = IDLE
	self.assertEquals(self.renderer.state, IDLE)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = False)
	self.assertEquals(self.renderer.state, IDLE)

    def test_StateQUITFromLOBBY_NO(self):
        self.renderer.state = LOBBY
	self.assertEquals(self.renderer.state, LOBBY)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = False)
	self.assertEquals(self.renderer.state, LOBBY)

    def test_StateQUITFromLOBBY_YES(self):
        self.renderer.state = LOBBY
	self.assertEquals(self.renderer.state, LOBBY)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = True)
	self.assertEquals(self.renderer.state, QUIT_DONE)

    def test_StateQUITFromCASHIER_YES(self):
        self.renderer.state = CASHIER
	self.assertEquals(self.renderer.state, CASHIER)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = True)
	self.assertEquals(self.renderer.state, QUIT_DONE)

    def test_StateQUITFromCASHIER_NO(self):
        self.renderer.state = CASHIER
	self.assertEquals(self.renderer.state, CASHIER)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = False)
	self.assertEquals(self.renderer.state, CASHIER)

    def test_StateQUITFromTOURNAMENT_NO(self):
        self.renderer.state = TOURNAMENTS
	self.assertEquals(self.renderer.state, TOURNAMENTS)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = False)
	self.assertEquals(self.renderer.state, TOURNAMENTS)

    def test_StateQUITFromTOURNAMENT_YES(self):
        self.renderer.state = TOURNAMENTS
	self.assertEquals(self.renderer.state, TOURNAMENTS)
        self.renderer.pythonEvent("QUIT")
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.confirmQuit(response = True)
	self.assertEquals(self.renderer.state, QUIT_DONE)

    def test_StateLOBBYFromQUIT(self):
        self.renderer.quit_state = LOBBY
        self.renderer.state = QUIT
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.changeState(LOBBY)
	self.assertEquals(self.renderer.state, LOBBY)

    def test_StateTOURNAMENTFromQUIT(self):
        self.renderer.quit_state = LOBBY
        self.renderer.state = QUIT
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.changeState(TOURNAMENTS)
	self.assertEquals(self.renderer.state, TOURNAMENTS)

    def test_StateOUTFITFromQUIT(self):
        self.renderer.quit_state = LOBBY
        self.renderer.state = QUIT
	self.assertEquals(self.renderer.state, QUIT)
        self.renderer.changeState(OUTFIT)
	self.assertEquals(self.renderer.state, OUTFIT)


# -----------------------------------------------------------------------------------------------------
def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PokerRendererTestCase))
    return suite
    
# -----------------------------------------------------------------------------------------------------
def GetTestedModule():
    return pokerrenderer
  
# -----------------------------------------------------------------------------------------------------
def Run(verbose = 2):
    return unittest.TextTestRunner(verbosity=verbose).run(GetTestSuite())
    
# -----------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "( cd .. ; ./config.status tests/test-pokerrenderer.py ) ; ( cd ../tests ; make TESTS='test-pokerrenderer.py' check )"
# End:
