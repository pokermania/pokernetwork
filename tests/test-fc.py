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
# the Free Software Foundation; either version 3 of the License, or
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
#  Cedric Pinson <cpinson@freesheep.org>
# 

import sys, os
sys.path.insert(0, "./..")
sys.path.insert(0, "..")

from pokernetwork.pokerpackets import *
from pokerui.pokerrenderer import PokerRenderer
from pokerui.pokerrenderer import  LEAVING_DONE, CANCELED, SIT_OUT, LEAVING, LEAVING_CONFIRM, JOINING, JOINING_MY, REBUY, PAY_BLIND_ANTE, PAY_BLIND_ANTE_SEND, MUCK, USER_INFO, HAND_LIST, SEARCHING_MY_CANCEL, SEARCHING_MY, LOBBY, IDLE, OUTFIT, QUIT, CASHIER, QUIT_DONE, TOURNAMENTS, TOURNAMENTS_REGISTER, TOURNAMENTS_UNREGISTER,  SEATING, LOGIN, BUY_IN
from pokerui.pokerinterface import INTERFACE_YESNO
from pokernetwork.pokerclient import PokerClientFactory
from pokernetwork.pokerclient import PokerClientProtocol
from pokernetwork.packets import PacketQuit, PacketSerial, PACKET_QUIT
from pokernetwork.pokerpackets import PacketPokerId, PACKET_POKER_GET_PERSONAL_INFO, PACKET_POKER_GET_USER_INFO
from pokerengine.pokergame import *
import unittest

#-----------------
class PokerInteractorsMockup:
    def __init__(self):
        self.call_destroy = False

    def destroy(self):
        self.call_destroy = True

    def setProtocol(self, protocol):
        pass

class PokerRendererMockup(PokerRenderer):
    def __init__(self):
	self.factory = PokerFactoryMockup()
	self.verbose = 3
        self.state = IDLE
        self.stream_mode = True
        self.state_outfit = None
        self.interactors = PokerInteractorsMockup()
        self.send_packet = None
        self.call_showYesNo = False
        self.call_hideYesNo = False
        self.quit_state = None
        self.change_state = []
        self.call_hideTournaments = False
        self.call_hideLobby = False
        self.call_showLobby = False
        self.call_hideTournaments = False
        self.call_showTournaments = False
        self.call_hideHands = False
        self.call_hideMuck = False
        self.call_hideCashier = False
        self.call_showCashier = False
        self.call_showOutfit = False
        self.call_hideOutfit = False
        self.call_showMessage = False
        self.call_requestBuyIn = False
        self.state_hands = {}
        self.call_showHands = False
        self.call_hideHands = False
        self.call_queryHands = False
        self.call_postMuck = False
        self.call_showMuck = False
        self.call_payAnte = False
        self.call_payBlind = False
        self.call_hideBuyIn = False
        self.call_sitActionsHide = False
        self.setProtocol(PokerProtocolMockup())
        self.replayGameId = -1
        self.stream_mode = True
        self.factory.interface.registerHandler("sit_out", self.sitOut)
        self.packet_processed = []

    def _handleConnection(self, protocol, packet):
        self.packet_processed.append(packet)
        PokerRenderer._handleConnection(self, protocol, packet)
        
    def isSeated(self):
        return False

    def sitActionsHide(self):
        self.call_sitActionsHide = True

    def hideBuyIn(self):
        self.call_hideBuyIn = True

    def payAnte(self, arg):
        self.call_payAnte = True

    def payBlind(self, arg):
        self.call_payBlind = True

    def postMuck(self, arg):
        self.call_postMuck = True

    def showMuck(self, arg):
        self.call_showMuck = True

    def queryHands(self):
        self.call_queryHands = True

    def requestBuyIn(self, game):
        self.call_requestBuyIn = True
        return True

    def showHands(self):
        self.call_showHands = True

    def hideHands(self):
        self.call_hideHands = False
        
    def hideLobby(self):
        self.call_hideLobby = True

    def showMessage(self, msg, dummy):
        self.call_showMessage = msg

    def showTournaments(self):
        self.call_showTournaments = True

    def hideTournaments(self):
        self.call_hideTournaments = True

    def showOutfit(self):
        self.call_showOutfit = True

    def hideCashier(self):
        self.call_hideCashier = True

    def showCashier(self):
        self.call_showCashier = True

    def hideOutfit(self):
        self.call_hideOutfit = True

    def showLobby(self):
        self.call_showLobby = True

    def hideMuck(self):
        self.call_hideMuck = True
        
    def showYesNoBox(self, msg):
        self.call_showYesNo = True;

    def hideHands(self):
        self.call_hideHands = True;

    def hideYesNoBox(self):
        self.call_hideYesNo = True;

#    def sendPacket(self, packet):
#        self.send_packet = packet

    def queryTournaments(self):
        pass

    def queryLobby(self):
        pass

    def chatHide(self):
        pass
        
    def render(self, packet):
        print "render packet %s\n" % str(packet)

    def changeState(self, state, *args, **kwargs):
        self.change_state.append((self.state, state))
        PokerRenderer.changeState(self, state, *args, **kwargs)

class PokerUserMockup:
    def __init__(self):
        pass

    def isLogged(self):
        return True
        
class TransportMockup:
    def __init__(self):
        pass
    
    def write(self, arg):
        print arg

class QueueMockup:
    def __init__(self):
        self.delay = -1
    
class PokerProtocolMockup(PokerClientProtocol):
    def __init__(self):
	self.packets = []
        self.user = PokerUserMockup()
        self.send_packet = None
        self.factory = PokerFactoryMockup()
        self.publish_packets = []
        self._poll = False
        self.established = True
        self.currentGameId = 0
        self._prefix = "protocol "
        self.callbacks = {
            'current': {},
            'not_current': {},
            'outbound': {}
            }
        self.lagmax_callbacks = []
        self.transport = TransportMockup()
#        UGAMEClientProtocol.sendPacket = self.mySendPacket
#    def schedulePacket(self, packet):
#	self.packets.append(packet)

#    def sendPacket(self, packet):
#        self.send_packet = packet

    def getSerial(self):
        return 1 # me

    def getOrCreateQueue(self, id):
        return QueueMockup()

    def mySendPacket(self, packet):
        print packet
    

class PokerInterfaceMockup:
    def __init__(self):
	self.verbose = 3
        self.callbacks = {}

    def showMenu(self):
        pass

    def hideMenu(self):
        pass
    
    def chatShow(self):
        pass

    def registerHandler(self, key, func):
        self.callbacks[key] = func

    def sitActionsSitOut(self, status, message, insensitive = ""):
        print "PokerInterfaceProtocol:sitActions sit_out"

    def sitActionsAuto(self, status):
        print "PokerInterfaceProtocol:sitActions auto"
        

class PokerSettingMockup:
    def __init__(self):
        pass

    def headerGet(self, path):
        return "yes"

class DelaysMockup:
    def __init__(self):
        pass

    def get(self, game, event):
        return 2
    
class PokerFactoryMockup(PokerClientFactory):
    def __init__(self):
	self.verbose = 3
	self.chat_config = {'max_chars': 80,
			    'line_length': 80}
        self.interface = PokerInterfaceMockup()
        self.call_quit = False
        self.call_getGame = False
        self.settings = PokerSettingMockup()
        game = PokerGame("url", False, "dirs")
        game.state = GAME_STATE_END
        game.serial2player[0] = PokerPlayer(0,0)
        game.serial2player[1] = PokerPlayer(1,0)
        game.serial2player[2] = PokerPlayer(2,0)
        game.serial2player[3] = PokerPlayer(3,0)
        self.games = {}
        self.games[0] = game
        self.delays = DelaysMockup()
        
    def isConnectionLess(self, packet):
        return False

    def gameExists(self, game_id):
        return True

    def quit(self):
        self.call_quit = True

    def getGame(self, id):
        return self.games[id]

class PokerPacketChatMockup:
    def __init__(self, message):
	self.message = message
	self.serial = 0
	self.game_id = 0


class PokerRendererTestCase(unittest.TestCase):
    
    #------------------------------------------------------
    def setUp(self):
	self.renderer = PokerRendererMockup()
    
    #------------------------------------------------------    
    def tearDown(self):
	self.renderer = None
        
    def test_fuckingChair(self):
        packet = PacketPokerInGame(game_id = 0, players = [ 1, 2 ,3, 4] )
        self.renderer._handleConnection(self.renderer.protocol, packet)
        packet = PacketPokerDealer(game_id = 0, dealer = 2, previous_dealer = 1)
        self.renderer._handleConnection(self.renderer.protocol, packet)
        # simulate a click on the sitout check box
        self.renderer.sitOut(True)
        
        
#        self.render.sitActionsUpdate()
#        packet = PacketPokerSitOut(serial = 1, game_id = 0)
#        self.renderer.sendPacket(packet)
        

#------------------------------------------------------


def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PokerRendererTestCase))
    return suite
    
#------------------------------------------------------
def GetTestedModule():
    return pokerrenderer
  
#------------------------------------------------------
def Run(verbose = 2):
    return unittest.TextTestRunner(verbosity=verbose).run(GetTestSuite())
    
#------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "( cd .. ; ./config.status tests/test-quit.py ) ; ( cd ../tests ; make TESTS='test-quit.py' check )"
# End:
