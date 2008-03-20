#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
#  Loic Dachary <loic@gnu.org>
#  Cedric Pinson <cpinson@freesheep.org>

from twisted.internet import reactor

from string import join
from time import sleep
from formatter import DumbWriter
from StringIO import StringIO
from types import *
from random import choice

from pokereval import PokerEval
from pokerengine.pokergame import PokerGameClient, PokerPlayer, history2messages
from pokerengine.pokercards import PokerCards
from pokerengine.pokerchips import PokerChips
from pokerengine import pokergame

from pokernetwork.pokerclientpackets import *
from pokernetwork.pokerclient import ABSOLUTE_LAGMAX
from pokernetwork.pokerchildren import PokerChildBrowser
from pokernetwork.user import checkNameAndPassword
from pokerui import pokerinterface
from pokerui.pokerinteractor import PokerInteractor, PokerInteractorSet
from pokerui.pokerchat import PokerChat

import linecache
import os
import sys

import platform
import locale
import gettext

if platform.system() == "Windows":

    lang = locale.getdefaultlocale()[0][:2]  
    try:
        cur_lang = gettext.translation("poker2d", localedir="./../../locale",languages=[lang])
        cur_lang.install()
    except IOError:
        _ = lambda text:text

else:
    gettext.bind_textdomain_codeset("poker2d","UTF-8")
    gettext.install("poker2d")

LOBBY = "lobby"
SEARCHING_MY = "searching_my"
SEARCHING_MY_CANCEL = "searching_my_cancel"
SEATING = "seating"
IDLE = "idle"
LOGIN = "login"
LOGIN_DONE = "login_done"
HAND_LIST = "list_hands"
USER_INFO = "user_info"
USER_INFO_DONE = "user_info_done"
BUY_IN = "buy_in"
BUY_IN_DONE = "buy_in_done"
REBUY = "rebuy"
REBUY_DONE = "rebuy_done"
MUCK = "muck"
PAY_BLIND_ANTE = "pay_blind_ante"
PAY_BLIND_ANTE_SEND = "pay_blind_ante_send"
PAY_BLIND_ANTE_DONE = "pay_blind_ante_done"
CASHIER = "cashier"
OUTFIT = "outfit"
OUTFIT_DONE = "outfit_done"
TOURNAMENTS = "tournaments"
TOURNAMENTS_REGISTER = "tournaments_register"
TOURNAMENTS_REGISTER_DONE = "tournaments_register_done"
TOURNAMENTS_UNREGISTER = "tournaments_unregister"
TOURNAMENTS_UNREGISTER_DONE = "tournaments_unregister_done"
JOINING = "joining"
JOINING_MY = "joining_my"
JOINING_DONE = "joining_done"
LEAVING = "leaving"
LEAVING_DONE = "leaving_done"
LEAVING_CANCEL = "leaving_cancel"
LEAVING_CONFIRM = "leaving_confirm"
CANCELED = "canceled"
SIT_OUT = "sit_out"
QUIT = "quit"
QUIT_DONE = "quit_done"

def global_trace(frame, event, arg):
    return local_trace
def local_trace(frame, event, arg):
    if event == "line":
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        print "%s(%d): %s" % (filename, lineno, linecache.getline(filename, lineno))

class PokerInteractors:

    def __init__(self, factory, renderer):
        self.renderer = renderer
        self.factory = factory
        self.protocol = None
        self.interactors_map = { }
        # reentrant update call workaround
        self.interactorActioned = None
        
    def setProtocol(self, protocol):
        self.protocol = protocol
        if protocol:
            protocol.registerHandler(True, PACKET_POKER_STREAM_MODE, self._handleConnection)
            protocol.registerHandler(True, PACKET_POKER_END_ROUND, self._handleConnection)
            protocol.registerHandler(True, PACKET_POKER_END_ROUND_LAST, self._handleConnection)
            protocol.registerHandler(True, PACKET_POKER_BEGIN_ROUND, self._handleConnection)
            protocol.registerHandler(True, PACKET_POKER_SELF_IN_POSITION, self._handleConnection)
            protocol.registerHandler(True, PACKET_POKER_SELF_LOST_POSITION, self._handleConnection)
            protocol.registerHandler(True, PACKET_POKER_HIGHEST_BET_INCREASE, self._handleConnection)

    def _handleConnection(self, protocol, packet):
        if self.factory.verbose > 3: print "PokerInteractors::_handleConnection: " + str(packet)

        game = self.factory.packet2game(packet)
        
        if packet.type == PACKET_POKER_STREAM_MODE:
            self.handleInteractors(game)
            self.interactorsSyncDisplay(game.id)
    
        elif packet.type == PACKET_POKER_END_ROUND:
            self.cancelAllInteractors(game.id)
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_END_ROUND_LAST:
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_BEGIN_ROUND:
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_SELF_IN_POSITION:
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_SELF_LOST_POSITION:
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_HIGHEST_BET_INCREASE:
            interactor_set = self.getOrCreateInteractorSet(game.id)
            interactors = interactor_set.items
            fold_interactor = interactors['fold']
            self.cancelAllInteractorButThisOne(fold_interactor)
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_BET_LIMIT:
            self.handleInteractors(game)

    def destroy(self):
        protocol = self.protocol
        if protocol:
            protocol.unregisterHandler(True, PACKET_POKER_STREAM_MODE, self._handleConnection)
            protocol.unregisterHandler(True, PACKET_POKER_END_ROUND, self._handleConnection)
            protocol.unregisterHandler(True, PACKET_POKER_END_ROUND_LAST, self._handleConnection)
            protocol.unregisterHandler(True, PACKET_POKER_BEGIN_ROUND, self._handleConnection)
            protocol.unregisterHandler(True, PACKET_POKER_SELF_IN_POSITION, self._handleConnection)
            protocol.unregisterHandler(True, PACKET_POKER_SELF_LOST_POSITION, self._handleConnection)
            protocol.unregisterHandler(True, PACKET_POKER_HIGHEST_BET_INCREASE, self._handleConnection)
        self.renderer = None
        self.protocol = None
        self.factory = None
        
    def deleteInteractorSet(self, game_id):
        if self.interactors_map.has_key(game_id):
            del self.interactors_map[game_id]

    def getOrCreateInteractorSet(self, game_id):
        if self.interactors_map.has_key(game_id) == False:
            display = self.factory.settings.headerGet("/settings/@display3d") == "yes" and "3d" or "2d"
            kwargs = { 'check': PokerInteractor("check",
                                                self.interactorAction,
                                                self.interactorDisplayNode,
                                                self.interactorSelectedCallback,
                                                self.factory.config.headerGetProperties("/sequence/interactors"+display+"/check/map")[0],
                                                game_id,
                                                self.factory.verbose,
                                                str(game_id)),
                       'fold': PokerInteractor("fold",
                                               self.interactorAction,
                                               self.interactorDisplayNode,
                                               self.interactorSelectedCallback,
                                               self.factory.config.headerGetProperties("/sequence/interactors"+display+"/fold/map")[0],
                                               game_id,
                                               self.factory.verbose,
                                               str(game_id)),
                       'call': PokerInteractor("call",
                                               self.interactorAction,
                                               self.interactorDisplayNode,
                                               self.interactorSelectedCallback,
                                               self.factory.config.headerGetProperties("/sequence/interactors"+display+"/call/map")[0],
                                               game_id,
                                               self.factory.verbose,
                                               str(game_id)),                                                               
                       'raise': PokerInteractor("raise",
                                                self.interactorAction,
                                                self.interactorDisplayNode,
                                                self.interactorSelectedCallback,
                                                self.factory.config.headerGetProperties("/sequence/interactors"+display+"/raise/map")[0],
                                                game_id,
                                                self.factory.verbose,
                                                str(game_id)) }                                                               
            self.interactors_map[game_id] = PokerInteractorSet(**kwargs)
        return self.interactors_map[game_id]        

    def handleInteractors(self, game):
        interactor_set = self.getOrCreateInteractorSet(game.id)
        interactors = interactor_set.items
        serial = self.protocol.getSerial()
        if game.willAct(serial):
            def updateInteractor(interactor, enabled, isInPosition, userData):
                if enabled:
                    interactor.setEnableIfDisabled()
                    interactor.setUserData(userData)
                    interactor.setInPosition(isInPosition)
                else:
                    interactor.disable()
                interactor.update()
                return enabled

            isInPosition = game.getSerialInPosition() == serial
            player = game.getPlayer(serial)
            # reentrant update call workaround
            self.interactorActioned = None
            updateInteractor(interactors["check"], game.canCheck(serial), isInPosition, [ game.id ])
            updateInteractor(interactors["fold"], game.canFold(serial), isInPosition, [ game.id ])
            updateInteractor(interactors["call"], game.canCall(serial), isInPosition, [ game.id ])
            updateInteractor(interactors["raise"], game.canRaise(serial), isInPosition, [ player.money, game.highestBetNotFold(), game.id ])
            # reentrant update call workaround
            if self.interactorActioned:
                self.disableAllInteractorButThisOne(self.interactorActioned)
        else:
            for (name, interactor) in interactors.iteritems():
                interactor.disable()
                interactor.update()

    def cancelAllInteractors(self, game_id):
        interactor_set = self.getOrCreateInteractorSet(game_id)
        interactors = interactor_set.items
        for (name, interactor) in interactors.iteritems():
            interactor.cancel()
            interactor.update()
        
    def disableAllInteractorButThisOne(self, interactor):
        keep = interactor.name
        interactor_set = self.getOrCreateInteractorSet(interactor.game_id)
        interactors = interactor_set.items
        for (name, interactor) in interactors.iteritems():
            if keep != name:
                interactor.disable()
                interactor.update()

    def cancelAllInteractorButThisOne(self, interactor):
        keep = interactor.name
        interactor_set = self.getOrCreateInteractorSet(interactor.game_id)
        interactors = interactor_set.items
        for (name, interactor) in interactors.iteritems():
            if keep != name:
                interactor.cancel()
                interactor.update()
    
    def interactorDisplayNode(self, interactor):
        if interactor.game_id == self.protocol.getCurrentGameId():
            game = self.factory.getGame(interactor.game_id)
            if game and interactor.stateHasChanged():
                if self.factory.verbose > 3: print "interactor:" + interactor.name + " default=" + interactor.getDefault() + " clicked=" + interactor.getClicked()
                self.render(PacketPokerDisplayNode(name = interactor.name, state = "default", style = interactor.getDefault(), selection = interactor.selected_value))
                self.render(PacketPokerDisplayNode(name = interactor.name, state = "clicked", style = interactor.getClicked(), selection = interactor.selected_value))
        
    def interactorsSyncDisplay(self, game_id):
        if not self.factory.display: return
        if self.factory.verbose > 3: print "interactorsSyncDisplay"
        game = self.factory.getGame(game_id)
        interactor_set = self.getOrCreateInteractorSet(game_id)
        interactors = interactor_set.items
        for (name, interactor) in interactors.iteritems():
            if self.factory.verbose > 3: print "interactor:" + interactor.name + " default=" + interactor.getDefault() + " clicked=" + interactor.getClicked()
            self.render(PacketPokerDisplayNode(name = interactor.name, state = "default", style = interactor.getDefault(), selection = interactor.selected_value))
            self.render(PacketPokerDisplayNode(name = interactor.name, state = "clicked", style = interactor.getClicked(), selection = interactor.selected_value))
                
    def interactorAction(self, interactor):
        # reentrant update call workaround
        self.interactorActioned = interactor
        game = self.factory.getGame(interactor.game_id)
        packet = interactor.getSelectedValue()
        if packet.type == PACKET_POKER_FOLD:
            serial = self.protocol.getSerial()
            if game.canCheck(serial):
                interface = self.renderer.factory.interface
                if interface:
                    self.renderer.interactorSelectedData = interactor
                    self.renderer.interactorSelectedDataPacket = packet
                    self.renderer.showCheckWarningBox()
                    interface.registerHandler(pokerinterface.INTERFACE_CHECK_WARNING, self.interactorCheckWarning)
                    return
        self.protocol.sendPacket(packet)

    def interactorCheckWarning(self, response):
        self.renderer.hideCheckWarningBox()
        interactor = self.renderer.interactorSelectedData
        self.renderer.interactorSelectedData = None
        packet = self.renderer.interactorSelectedDataPacket
        self.renderer.interactorSelectedDataPacket = None
        game = self.factory.getGame(interactor.game_id)
        if response == "check":
            packet = PacketPokerCheck(game_id = game.id,
                                      serial = self.protocol.getSerial())
            self.protocol.sendPacket(packet)
        elif response == "fold":
            self.protocol.sendPacket(packet)
        elif response == "cancel":
            interactor.setEnableIfActivated()
            self.handleInteractors(game)

    def interactorSelectedCallback(self, interactor):
        self.cancelAllInteractorButThisOne(interactor)

    def interactorSelected(self, packet):
        if self.protocol.getCurrentGameId() == packet.game_id:
            if packet.type == PACKET_POKER_FOLD:
                name = "fold"
            elif packet.type == PACKET_POKER_CHECK:
                name = "check"
            elif packet.type == PACKET_POKER_CALL:
                name = "call"
            elif packet.type == PACKET_POKER_RAISE:
                name = "raise"
            else:
                print "*CRITICAL* unexpected event %s " % event
                return

            interactor = self.getOrCreateInteractorSet(packet.game_id).items[name]
            interactor.select(packet)
            interactor.update()

    def render(self, packet):
        self.renderer.render(packet)

class PokerRenderer:

    def __init__(self, factory):
        self.verbose = factory.verbose
        self.replayStepping = True
        self.replayGameId = None
        self.money = { 'default': { 'name': 'Custom', 'unit': 'C', 'cent': 'cts' } }
        money_serial = 1
        self.money_serial2name = {}
        for key in ( 'money_one', 'money_two' ):
            self.money[key] = factory.config.headerGetProperties("/sequence/" + key)
            if not self.money[key]:
                self.money[key] = self.money['default'].copy()
                self.money[key]['serial'] = money_serial
                money_serial += 1
            else:
                self.money[key] = self.money[key][0]
                self.money[key]['serial'] = int(self.money[key]['serial'])
            self.money_serial2name[self.money[key]['serial']] = key
        self.state = IDLE

        self.state_buy_in = ()

        self.state_login = ()
        self.state_outfit = None
        self.quit_state = None
        
        self.state_tournaments = factory.settings.headerGetProperties("/settings/tournaments")
        if not self.state_tournaments:
            print "CRITICAL: missing /settings/tournaments"
        else:
            self.state_tournaments = self.state_tournaments[0]
        self.state_tournaments['cashier_label'] = factory.config.headerGet("/sequence/cashier/@enter")
        self.state_tournaments["current"] = 0
        self.state_tournaments['currency_serial'] = int(self.state_tournaments['currency_serial'])

        self.state_lobby = factory.settings.headerGetProperties("/settings/lobby")
        if not self.state_lobby:
            print "CRITICAL: missing /settings/lobby"
        else:
            self.state_lobby = self.state_lobby[0]
        self.state_lobby['cashier_label'] = factory.config.headerGet("/sequence/cashier/@enter")
        self.state_lobby["current"] = 0
        self.state_lobby['currency_serial'] = int(self.state_lobby['currency_serial'])

        self.state_joining_my = 0

        self.state_cashier = { 'exit_label': factory.config.headerGet("/sequence/cashier/@exit") }
        self.state_muck = None

        state_hands = factory.settings.headerGetProperties("/settings/handlist")
        if not state_hands:
            self.state_hands = { "start": 0, "count": 100 }
        else:
            self.state_hands = {}
            for (key, value) in state_hands[0].iteritems():
                self.state_hands[key] = int(value)
        
        self.factory = factory
        self.protocol = None
        self.stream_mode = True
        self.bet_step = 1 # else if a human is already here we don't receive a packet POKER_BET_LIMIT and if we don't receive this packet bet_step is not defined
        self.interactors = PokerInteractors(factory, self)
        
        self.chat_words = factory.config.headerGetProperties("/sequence/chatwords/word")
        self.interactorSelectedData = None
        self.interactorSelectedDataPacket = None

    def linetrace(self):
        sys.settrace(global_trace)

    def pythonEvent(self, event, map = None):
        if self.verbose:
            print "pythonEvent %s %s" % (event,str(map))

        if event == "QUIT":
            if self.state == OUTFIT:
                self.changeState(OUTFIT_DONE)
            else:
                self.quit()
                
    def setProtocol(self, protocol):
        self.protocol = protocol
        if protocol:
            self.protocol.user_info = None
            protocol.registerHandler("current", None, self._handleConnection)
            protocol.registerHandler("outbound", None, self._handleConnection)
            protocol.registerLagmax(self.updateLagmax)
            self.interactors.setProtocol(protocol)

    def showYourRank(self, tourney_serial, rank, players, money):
        msg = _("Tourney %(num_tourney)d\n Your rank is %(your_rank)d on %(num_players)d\nYou won %(my_prize)s") % {'num_tourney' : tourney_serial, 'your_rank' : rank, 'num_players' :  players, 'my_prize' : PokerChips.tostring(money) }
        self.showMessage(msg, None)

    def showYesNoBox(self, message):
        self.factory.interface.yesnoBox(message)
        self.render(PacketPokerInterfaceCommand(window = "yesno_window", command = "show"))

    def hideYesNoBox(self):
        self.render(PacketPokerInterfaceCommand(window = "yesno_window", command = "hide"))
        interface = self.factory.interface
        if interface.callbacks.has_key(pokerinterface.INTERFACE_YESNO):
            del interface.callbacks[pokerinterface.INTERFACE_YESNO]
        return True

    def showMuckBox(self):
        self.factory.interface.muckShow()
        self.render(PacketPokerInterfaceCommand(window = "muck_window", command = "show"))

    def hideMuckBox(self):
        self.render(PacketPokerInterfaceCommand(window = "muck_window", command = "hide"))
        self.factory.interface.muckHide()
        interface = self.factory.interface
        if interface.callbacks.has_key(pokerinterface.INTERFACE_MUCK):
            del interface.callbacks[pokerinterface.INTERFACE_MUCK]
        return True

    def showCheckWarningBox(self):
        self.factory.interface.checkWarningBox()
        self.render(PacketPokerInterfaceCommand(window = "check_warning_window", command = "show"))
        
    def hideCheckWarningBox(self):
        self.render(PacketPokerInterfaceCommand(window = "check_warning_window", command = "hide"))
        interface = self.factory.interface
        if interface.callbacks.has_key(pokerinterface.INTERFACE_CHECK_WARNING):
            del interface.callbacks[pokerinterface.INTERFACE_CHECK_WARNING]
        return True

    def quit(self, dummy = None):
        interface = self.factory.interface
        if interface:
            if not interface.callbacks.has_key(pokerinterface.INTERFACE_YESNO):
                self.showYesNoBox( _("Do you really want to quit ?") )
                interface.registerHandler(pokerinterface.INTERFACE_YESNO, self.confirmQuit)
                # restore state if don't confirm quit
                state = self.state
                self.quit_state = state
                self.changeState(QUIT)
        else:
            self.changeState(QUIT)
            self.confirmQuit(True)


    def confirmQuit(self, response = False):
        self.hideYesNoBox()
        if response:
            self.changeState(QUIT_DONE)
            if self.protocol:
                self.sendPacket(PacketQuit())
            self.interactors.destroy()
            self.factory.quit()
        else:
            if self.quit_state is not None:
                self.changeState(self.quit_state)
        
    def autoBlind(self, auto):
        game_id = self.protocol.getCurrentGameId()
        serial = self.protocol.getSerial()
        if auto:
            self.protocol.sendPacket(PacketPokerAutoBlindAnte(game_id = game_id,
                                                              serial = serial))
        else:
            self.protocol.sendPacket(PacketPokerNoautoBlindAnte(game_id = game_id,
                                                                serial = serial))
        
    def sitOut(self, yesno):
        serial = self.protocol.getSerial()
        game_id = self.protocol.getCurrentGameId()
        game = self.factory.getGame(game_id)
        if not game:
            print "WARNING sitOut() when no current game active"
            return
        if not game.getPlayer(serial):
            print "WARNING sitOut() for a non existing me-serial %d" % serial
            return
        if yesno:
            self.protocol.sendPacket(PacketPokerSitOut(game_id = game_id,
                                                       serial = serial))
        else:
            if game.isBroke(serial):
                self.changeState(USER_INFO, REBUY, game)
            else:
                self.protocol.sendPacket(PacketPokerSit(serial = serial,
                                                        game_id = game_id))
        
    def payAnte(self, game, amount):
        interface = self.factory.interface
        if interface and not interface.callbacks.has_key(pokerinterface.INTERFACE_POST_BLIND):
            message = _("Pay the ante (%d) ?") % amount
            self.showBlind(message,"no")
            interface.registerHandler(pokerinterface.INTERFACE_POST_BLIND, lambda *args: self.changeState(PAY_BLIND_ANTE_SEND, 'ante', *args))
            
    def confirmPayAnte(self, response):
        serial = self.protocol.getSerial()
        game_id = self.protocol.getCurrentGameId()
        if response == "yes":
            self.protocol.sendPacket(PacketPokerAnte(game_id = game_id,
                                                     serial = serial))
        else:
            self.protocol.sendPacket(PacketPokerSitOut(game_id = game_id,
                                                       serial = serial))
        self.hideBlind()
        self.factory.interface.clearCallbacks(pokerinterface.INTERFACE_POST_BLIND)
        return response == "yes"

    def hideBlind(self):
        interface = self.factory.interface
        if interface and interface.callbacks.has_key(pokerinterface.INTERFACE_POST_BLIND):
            interface.blindHide()
            interface.clearCallbacks(pokerinterface.INTERFACE_POST_BLIND)
        self.render(PacketPokerInterfaceCommand(window = "blind_window", command = "hide"))

    def showBlind(self, message, what):
        self.factory.interface.blindMessage(message, what)
        self.render(PacketPokerInterfaceCommand(window = "blind_window", command = "show"))
        
    def payBlind(self, game, amount, dead, state):
        interface = self.factory.interface
        if interface and not interface.callbacks.has_key(pokerinterface.INTERFACE_POST_BLIND):
            message = _("Pay the ")
            if dead > 0:
                message += _("big blind (%(bblind_)s) + dead (%(dead_)s)") % { 'bblind_' : PokerChips.tostring(amount), 'dead_' : PokerChips.tostring(dead) }
            elif state == "big" or state == "late":
                message += _("big blind (%s)") % PokerChips.tostring(amount)
            else:
                message += _("small blind (%s)") % PokerChips.tostring(amount)
            message += " ?"
            wait_blind = ( state == "late" or state == "big_and_dead" ) and "yes" or "no"
            self.showBlind(message, wait_blind)
            interface.registerHandler(pokerinterface.INTERFACE_POST_BLIND, lambda *args: self.changeState(PAY_BLIND_ANTE_SEND, 'blind', *args))

    def confirmPayBlind(self, response):
        serial = self.protocol.getSerial()
        game_id = self.protocol.getCurrentGameId()
        if response == "yes":
            self.protocol.sendPacket(PacketPokerBlind(game_id = game_id,
                                                      serial = serial))
        elif response == "wait":
            self.protocol.sendPacket(PacketPokerWaitBigBlind(game_id = game_id,
                                                             serial = serial))
        else:
            self.protocol.sendPacket(PacketPokerSitOut(game_id = game_id,
                                                       serial = serial))
        self.hideBlind()
        self.factory.interface.clearCallbacks(pokerinterface.INTERFACE_POST_BLIND)
        return response == "yes"
            
    def requestLogin(self):
        interface = self.factory.interface
        remember = self.factory.remember
        if remember:
            name = self.factory.name
            password = self.factory.password
        else:
            name = ""
            password = ""
        if name == "username":
            name = ""
            password = ""
        interface.requestLogin(name, password, remember)
        interface.registerHandler(pokerinterface.INTERFACE_LOGIN, self.interfaceCallbackLogin)

    def interfaceReady(self, interface):
        interface.registerHandler(pokerinterface.INTERFACE_CASHIER, self.handleCashier)
        interface.registerHandler(pokerinterface.INTERFACE_LOBBY, self.handleLobby)
        interface.registerHandler(pokerinterface.INTERFACE_TOURNAMENTS, self.handleTournaments)
        interface.registerHandler(pokerinterface.INTERFACE_CHAT_HISTORY, self.chatHistory)
        interface.registerHandler(pokerinterface.INTERFACE_CHAT_LINE, self.chatLine)
        interface.registerHandler(pokerinterface.INTERFACE_MENU, self.handleMenu)
        interface.registerHandler(pokerinterface.INTERFACE_HANDS, self.handleHands)
        interface.showMenu()
        interface.updateMenu(self.factory.settings)
        if self.factory.remember:
            if self.protocol:
                if self.verbose: print "connection ready, ask for password"
                self.changeState(LOGIN, lambda success: self.changeState(LOBBY))
            else:
                if self.verbose: print "connection not established, will ask password later"


    # ripped from fancy_getopt.py
    # usage
    # print wrap_text("salut les aminchessssssssssss salut les aminches", 10, '@')
    # ['salut les', 'aminchesss@', 'sssssssss', 'salut les', 'aminches']
    def wrap_text (self, text, width, hyphen = '-'):
        """wrap_text(text : string, width : int) -> [string]
    
        Split 'text' into multiple lines of no more than 'width' characters
        each, and return the list of strings that results.
        """
        import string
        import re
        WS_TRANS = string.maketrans(string.whitespace, ' ' * len(string.whitespace))

        if text is None:
            return []
        if len(text) <= width:
            return [text]

        text = string.expandtabs(text)
        text = string.translate(text, WS_TRANS)
        chunks = re.split(r'( +|-+)', text)
        chunks = filter(None, chunks)      # ' - ' results in empty strings
        lines = []

        while chunks:

            cur_line = []                   # list of chunks (to-be-joined)
            cur_len = 0                     # length of current line

            while chunks:
                l = len(chunks[0])
                if cur_len + l <= width:    # can squeeze (at least) this chunk in
                    cur_line.append(chunks[0])
                    del chunks[0]
                    cur_len = cur_len + l
                else:                       # this line is full
                    # drop last chunk if all space
                    if cur_line and cur_line[-1][0] == ' ':
                        del cur_line[-1]
                    break

            if chunks:                      # any chunks left to process?

                # if the current line is still empty, then we had a single
                # chunk that's too big too fit on a line -- so we break
                # down and break it up at the line width
                if cur_len == 0:
                    cur_line.append(chunks[0][0:width])
                    cur_line.append(hyphen)
                    chunks[0] = chunks[0][width:]

                # all-whitespace chunks at the end of a line can be discarded
                # (and we know from the re.split above that if a chunk has
                # *any* whitespace, it is *all* whitespace)
                if chunks[0][0] == ' ':
                    del chunks[0]

            # and store this line in the list-of-all-lines -- as a single
            # string, of course!
            lines.append(string.join(cur_line, ''))

        # while chunks

        return lines

    def chatFormatMessage(self, packet):
        message = packet.message        
        from pprint import pprint
	import string
        if self.factory.verbose: pprint(self.chat_words)
	
        for word in self.chat_words:
	    words = message.split()
	    def matchChatWord(current):
		if current == word["in"]:
		    serial = packet.serial
		    game_id = packet.game_id
		    if self.factory.verbose: print "chat word (%s) found => sending (%s) event" % (word["in"], word["event"])
		    self.schedulePacket(PacketPokerChatWord(word = word["event"], game_id = game_id, serial = serial))
		    return word["out"]
		else:
		    if self.factory.verbose > 3: print "chat word (%s) not found" % word["in"]
		    return current
	    words = map(matchChatWord, words)
	    message = string.join(words)

        #
        # This is crude but is only meant to cope with a server that
        # would insist on sending more chars than the client wants.
        #

        config = self.factory.chat_config
        message = message[:config['max_chars']] 
        line_length = config['line_length']
        message = string.join(self.wrap_text(message, line_length), '\n')
        #format = DumbWriter(StringIO(), config['line_length'])
        #format.send_flowing_data(message)
        #message = format.file.getvalue()
        
        return message
        
    def chatHide(self):
        interface = self.factory.interface
        if interface:
            interface.chatHide()
        self.render(PacketPokerInterfaceCommand(window = "chat_history_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "chat_entry_window", command = "hide"))

    def chatShow(self):
        interface = self.factory.interface
        if interface:
            interface.chatShow()
            #self.render(PacketPokerChatHistory(show = "no"))
            # it does not hide chat history because the window is not created (not send yet by xwnc to c++)
            # so wa can't hide it. we need to fix that
        self.render(PacketPokerInterfaceCommand(window = "chat_entry_window", command = "show"))

    def chatHistoryHide(self):
        self.factory.interface.chatHistoryHide()
        self.render(PacketPokerInterfaceCommand(window = "chat_history_window", command = "hide"))
        
    def chatHistoryShow(self):
        self.factory.interface.chatHistoryShow()
        self.render(PacketPokerInterfaceCommand(window = "chat_history_window", command = "show"))
        
    def chatHistory(self, yesno):
        game_id = self.protocol.getCurrentGameId()
        game = self.factory.getGame(game_id)        
        self.render(PacketPokerChatHistory(show = yesno))
        if yesno == "yes":
            self.chatHistoryShow()
        elif yesno == "no":
            self.chatHistoryHide()
            

    def chatLine(self, line):
        serial = self.protocol.getSerial()
        game_id = self.protocol.getCurrentGameId()
        if game_id == None:
            print "WARNING chatLine() while no current game active"
        else:
            self.protocol.sendPacket(PacketPokerChat(game_id = game_id,
                                                     serial = serial,
                                                     message = line))
    
    def interfaceCallbackLogin(self, ok_or_cancel, name, password, remember):
        if ok_or_cancel == "create" :
            if self.factory.settings.headerGet("/settings/web"):
                self.factory.browseWeb("create_account.php?name=%s" % name)
            else:
                ok_or_cancel = "ok"

        if ok_or_cancel != "ok":
            self.changeState(LOGIN_DONE, False)
            return
        
        interface = self.factory.interface
        (ok, code, reason) = checkNameAndPassword(name, password)
        if ok:
            self.protocol.sendPacket(PacketLogin(name = name,
                                                 password = password))
            self.protocol.user.name = name
            self.protocol.user.password = password
            self.factory.saveAuthToFile(name, password, remember)
        else:
            self.showMessage(reason, self.requestLogin)

    def showMessage(self, message, callback):
        interface = self.factory.interface
        if interface:
            interface.messageBox(message)
            if callback:
                interface.registerHandler(pokerinterface.INTERFACE_MESSAGE_BOX, callback)
        if self.verbose: print message

    def handleCashier(self, yesno = "yes"):
        if yesno == "yes":
            self.changeState(CASHIER)
        else:
            self.changeState(LOBBY)

    def showCashier(self):
        interface = self.factory.interface
        if interface:
            interface.showCashier(self.state_cashier['exit_label'],self.money['money_one']['name'], self.money['money_two']['name'])
#        self.showBackgroundLobbyCashier()
#        self.showClockWindow()
        self.render(PacketPokerInterfaceCommand(window = "personal_information_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "account_status_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "exit_cashier_window", command = "show"))

    def hideCashier(self):
        interface = self.factory.interface
        if interface:
            interface.hideCashier()
        self.render(PacketPokerInterfaceCommand(window = "personal_information_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "account_status_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "exit_cashier_window", command = "hide"))

    def updateCashier(self, packet):
        if self.verbose > 1: print "updateCashier"
        interface = self.factory.interface
        if interface:
            money_one = packet.money.get(self.money['money_one']['serial'], (0, 0))
            money_two = packet.money.get(self.money['money_two']['serial'], (0, 0))
            cashier = PacketPokerUserInfo.cashier
            in_game = PacketPokerUserInfo.in_game
            interface.updateCashier(self.protocol.getName(),
                                    packet.email,
                                    "%s %s\n%s\n%s\n%s %s %s\n%s" % ( packet.firstname, packet.lastname, packet.addr_street, packet.addr_street2, packet.addr_zip, packet.addr_town, packet.addr_state, packet.addr_country ),
                                    PokerChips.tostring(money_one[cashier]) + self.money['money_one']['unit'],
                                    PokerChips.tostring(money_one[in_game]) + self.money['money_one']['unit'],
                                    PokerChips.tostring(money_one[cashier] + money_one[in_game]) + self.money['money_one']['unit'],
                                    PokerChips.tostring(money_two[cashier]) + self.money['money_two']['unit'],
                                    PokerChips.tostring(money_two[in_game]) + self.money['money_two']['unit'],
                                    PokerChips.tostring(money_two[cashier] + money_two[in_game]) + self.money['money_two']['unit'],
                                    )

    def showMuck(self, game):
        interface = self.factory.interface
        if interface:        
            if interface.callbacks.has_key(pokerinterface.INTERFACE_MUCK):
                self.hideMuckBox()
            self.state_muck = game
            self.showMuckBox()
            interface.registerHandler(pokerinterface.INTERFACE_MUCK, self.confimMuck)
            return
        self.postMuck(True)
    
    def confimMuck(self, want_to_muck):
        self.hideMuckBox()        
        self.postMuck(want_to_muck)
        self.changeState(IDLE)
    
    def hideMuck(self):
        self.hideMuckBox()        

    def postMuck(self, want_to_muck):
        game = self.state_muck
        if game and self.protocol:
            if (want_to_muck == "show"):
                self.protocol.postMuck(game, False)
            elif (want_to_muck == "hide"):
                self.protocol.postMuck(game, True)
            elif (want_to_muck == "always"):
                packet = []
                packet.extend(("menu", "set", "muck", "yes"))
                interface = self.factory.interface
                if interface:        
                    interface.command(*packet)
                self.protocol.postMuck(game, True)
            self.state_muck = None

    def broadcastAutoMuckChange(self, auto_muck):
        if self.protocol:
            serial = self.protocol.user.serial
            game_ids = self.factory.getGameIds()
            for game_id in game_ids:
                game = self.factory.getGame(game_id)
                if game and game.serial2player.has_key(serial):
                    self.protocol.sendPacket(PacketPokerAutoMuck(game_id = game_id,
                                                                 serial = serial,
                                                                 auto_muck = auto_muck))

    def handleSerial(self, packet):
        if self.verbose: print "handleSerial: we now have serial %d" % packet.serial
        self.protocol.user.serial = packet.serial
        display = self.factory.display
        display.render(packet)

    def restoreGameSate(self, game):
        serial = self.protocol.getSerial()
        if game.getPlayer(serial):
            if game.isRunning():
                self.sendPacket(PacketPokerProcessingHand(game_id = game.id,
                                                          serial = serial))
            else:
                self.readyToPlay(game.id)
        requested = game.getRequestedAction(serial)
        if requested == "blind_ante":
            ( amount, dead, state ) = game.blindAmount(serial)
            self.changeState(PAY_BLIND_ANTE, 'blind', game, amount, dead, state)
        elif requested == "rebuy":
            self.changeState(USER_INFO, REBUY, game)
            
    
    def _handleConnection(self, protocol, packet):
        game = self.factory.packet2game(packet)

        if ( packet.type == PACKET_POKER_BEST_CARDS or
             packet.type == PACKET_POKER_PLAYER_NO_CARDS or
             packet.type == PACKET_POKER_CHIPS_PLAYER2BET or
             packet.type == PACKET_POKER_CHIPS_BET2POT or
             packet.type == PACKET_POKER_CHIPS_POT2PLAYER or
             packet.type == PACKET_POKER_CHIPS_POT_MERGE or
             packet.type == PACKET_POKER_CHIPS_POT_RESET or
             (packet.type == PACKET_POKER_DEAL_CARDS and self.stream_mode) ):
            self.render(packet)

        elif packet.type == PACKET_POKER_USER_INFO:
            self.changeState(USER_INFO_DONE)

        elif packet.type == PACKET_POKER_STREAM_MODE:
            if self.stream_mode == True: raise UserWarning, "STREAM_MODE while in STREAM_MODE"
            self.stream_mode = True
            self.render(packet)
            self.restoreGameSate(game)
            
        elif packet.type == PACKET_POKER_BATCH_MODE:
            self.stream_mode = False
            self.render(packet)

        elif packet.type == PACKET_POKER_BET_LIMIT:
            self.bet_step = packet.step
            self.render(packet)
            
        elif packet.type == PACKET_POKER_HAND_LIST:
            if self.state == HAND_LIST:
                self.showHands(packet.hands, packet.total)
            else:
                print "*CRITICAL* handleGame: unexpected state for POKER_HAND_LIST " + self.state

        elif packet.type == PACKET_POKER_HAND_HISTORY:
            if self.state == HAND_LIST:
                self.showHandHistory(packet.game_id, eval(packet.history), eval(packet.serial2name))
            else:
                print "*CRITICAL* handleGame: unexpected state for POKER_HAND_HISTORY " + self.state

        elif packet.type == PACKET_BOOTSTRAP:
            self.bootstrap()
            
        elif packet.type == PACKET_PROTOCOL_ERROR:
            self.showMessage(packet.message, lambda: self.confirmQuit(True))
            self.factory.reconnect = False
            
        elif packet.type == PACKET_POKER_TABLE_LIST:
            if self.state == LOBBY:
                self.updateLobby(packet)
            elif self.state == SEARCHING_MY:
                self.choseTable(packet.packets)
            else:
                print "*CRITICAL* handleGame: unexpected state for TABLE_LIST: " + self.state

        elif packet.type == PACKET_POKER_PLAYERS_LIST:
            self.updateLobbyPlayersList(packet)
        
        elif packet.type == PACKET_POKER_TOURNEY_REGISTER:
            self.changeState(TOURNAMENTS_REGISTER_DONE)
            
        elif packet.type == PACKET_POKER_TOURNEY_UNREGISTER:
            self.changeState(TOURNAMENTS_UNREGISTER_DONE)
            
        elif packet.type == PACKET_ERROR:
            if packet.other_type == PACKET_POKER_TOURNEY_REGISTER:
                self.changeState(TOURNAMENTS_REGISTER_DONE)
                self.showMessage(packet.message, None)
            elif packet.other_type == PACKET_POKER_PLAYER_LEAVE:
                self.changeState(LEAVING_CANCEL)
                self.showMessage(packet.message, None)
            else:
                print "*CRITICAL*: unexpected error"
            
        elif packet.type == PACKET_POKER_TOURNEY_PLAYERS_LIST:
            self.updateTournamentsPlayersList(packet)
        
        elif packet.type == PACKET_POKER_TOURNEY_LIST:
            self.updateTournaments(packet)

        elif packet.type == PACKET_POKER_TOURNEY_RANK:
            self.showYourRank(packet.serial, packet.rank, packet.players, packet.money)
                
        elif packet.type == PACKET_POKER_TABLE_DESTROY:
            if self.replayGameId == packet.serial:
                self.protocol._lagmax = self.factory.delays.get("lag", 15)
                self.replayGameId = 0
                self.changeState(SEARCHING_MY)
            game_id = self.protocol.getCurrentGameId()
            if game_id == packet.serial:
                display = self.factory.display
                display.render(packet)
                self.chatHide()
                self.sitActionsHide()
            
        elif packet.type == PACKET_POKER_TABLE:
            game = self.factory.getGame(packet.id)
#            self.scheduledAction[game.id] = False
#            self.futureAction[game.id] = {}
            if not game:
                self.showMessage("server refused our request", None)
            else:
                if game.name == "*REPLAY*":
                    self.protocol._lagmax = 0
                    self.replayGameId = game.id
                packet.seats_all = game.seats_all
                self.render(packet)
                self.factory.interface.chatHistoryReset()
            self.changeState(JOINING_DONE)

        elif packet.type == PACKET_POKER_CURRENT_GAMES:
            self.render(packet)

        elif packet.type == PACKET_POKER_TABLE_QUIT:
            self.state = LEAVING
            self.changeState(LEAVING_DONE)
            self.deleteGame(game.id)
            self.protocol.setCurrentGameId(None)
            
        elif packet.type == PACKET_AUTH_REFUSED:
            self.showMessage(packet.message, lambda: self.changeState(LOGIN_DONE, False))

        elif packet.type == PACKET_AUTH_OK:
            if self.verbose: print "login accepted"

        elif packet.type == PACKET_MESSAGE:
            print "PACKET_MESSAGE : " + packet.string
            self.showMessage(packet.string, None)

        elif packet.type == PACKET_SERIAL:
            self.handleSerial(packet)
            self.changeState(SEARCHING_MY)

        elif packet.type == PACKET_POKER_PERSONAL_INFO:
            self.updateCashier(packet)
            if self.state == CASHIER:
                self.showCashier()

        if not game:
            return
            
        if packet.type == PACKET_POKER_START:
            self.resetLagmax()
            if self.stream_mode:
                self.sendPacket(PacketPokerProcessingHand(game_id = packet.game_id,
                                                          serial = self.protocol.getSerial()))
            self.render(packet)

        elif packet.type in ( PACKET_POKER_MESSAGE, PACKET_POKER_GAME_MESSAGE ):
            self.showMessage(packet.string, None)

        elif packet.type == PACKET_POKER_AUTO_BLIND_ANTE:
            self.sitActionsUpdate()

        elif packet.type == PACKET_POKER_NOAUTO_BLIND_ANTE:
            self.sitActionsUpdate()

        elif packet.type == PACKET_POKER_CANCELED:
            self.changeState(CANCELED)
            self.readyToPlay(packet.game_id)

        elif packet.type == PACKET_POKER_PLAYER_ARRIVE:
            if packet.serial == self.protocol.getSerial():
                if packet.url != self.factory.getUrl():
                    print "*CRITICAL*: PACKET_POKER_PLAYER_ARRIVE: server url is %s, local url is %s " % ( packet.url, self.factory.getUrl() )
                if packet.outfit != self.factory.getOutfit():
                    print "*CRITICAL*: PACKET_POKER_PLAYER_ARRIVE: server outfit is %s, local outfit is %s " % ( packet.url, self.factory.getUrl() )
                self.sitActionsUpdate()
            ( packet.url, packet.outfit ) = self.factory.getSkin().interpret(packet.url, packet.outfit)
            self.render(packet)

            if packet.serial == self.protocol.getSerial():
                self.sitActionsShow()

        elif ( packet.type == PACKET_POKER_PLAYER_LEAVE or
               packet.type == PACKET_POKER_TABLE_MOVE ) :
            self.render(packet)

        elif packet.type == PACKET_POKER_END_ROUND:
            self.render(packet)
            self.delay(game, "end_round")

        elif packet.type == PACKET_POKER_END_ROUND_LAST:
            self.render(packet)
            self.delay(game, "end_round_last")

        elif packet.type == PACKET_POKER_BEGIN_ROUND:
            self.render(packet)
            self.delay(game, "begin_round")
            
        elif packet.type == PACKET_POKER_SELF_IN_POSITION:
            self.resetLagmax()
            self.render(packet)

        elif packet.type == PACKET_POKER_SELF_LOST_POSITION:
            self.render(packet)

        elif packet.type == PACKET_POKER_HIGHEST_BET_INCREASE:
            self.render(packet)
               
        elif packet.type == PACKET_POKER_POSITION:
            self.render(packet)
            if packet.serial != 0:
                self.delay(game, game.isBlindAnteRound() and "blind_ante_position" or "position")

        elif packet.type == PACKET_POKER_CHAT:
            interface = self.factory.interface
            if interface:
                name = ""
                indexColor = 0
                if packet.serial != 0:
                    if game != None:
                        if game.serial2player.has_key(packet.serial):
                            seats = game.seats()
                            for i in range(len(seats)):
                                if seats[i] == packet.serial:
                                    indexColor = i+1
                                    break
                            name = game.serial2player[packet.serial].name + ": "
                msg = str(indexColor) + ":" + name + packet.message
                interface.chatHistory(msg)
            # duplicate PacketPokerChat
            # in order to preseve integrity of original packet
            message = self.chatFormatMessage(packet)
            #message = PokerChat.filterChatTrigger(message)
            chatPacket = PacketPokerChat(game_id = packet.game_id,
                                         serial = packet.serial,
                                         message = message)
            if chatPacket.message.strip() != "":
                self.render(chatPacket)

        elif packet.type == PACKET_POKER_MUCK_REQUEST:
            self.render(packet)
            if self.protocol.getSerial() in packet.muckable_serials:
                self.changeState(MUCK, game)                

        elif packet.type == PACKET_POKER_BLIND_REQUEST:
            if ( game.getSerialInPosition() == self.protocol.getSerial() ):
                self.changeState(PAY_BLIND_ANTE, 'blind', game, packet.amount, packet.dead, packet.state)
                self.sitActionsUpdate()
                           
        elif packet.type == PACKET_POKER_ANTE_REQUEST:
            if ( game.getSerialInPosition() == self.protocol.getSerial() ):
                self.changeState(PAY_BLIND_ANTE, 'ante', game, packet.amount)
                self.sitActionsUpdate()
                
        elif packet.type == PACKET_POKER_SEAT:
            if packet.seat == 255:
                self.showMessage( _("This seat is busy"), None)
                self.changeState(IDLE)
            else:
                if not game.isTournament():
                    self.changeState(USER_INFO, BUY_IN, game)
            
        elif packet.type == PACKET_POKER_SEATS:
            self.render(packet)
            
        elif packet.type == PACKET_POKER_PLAYER_CARDS:
            if game.variant == "7stud":
                packet.visibles = "best"
            else:
                packet.visibles = ""
            self.render(packet)

        elif packet.type == PACKET_POKER_BOARD_CARDS:
            self.render(packet)

        elif packet.type == PACKET_POKER_DEALER:
            self.render(packet)
            self.delay(game,"dealer")
            
        elif ( packet.type == PACKET_POKER_SIT_OUT or
               packet.type == PACKET_POKER_SIT_OUT_NEXT_TURN ):
            self.render(packet)
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()
                self.changeState(SIT_OUT)

        elif packet.type == PACKET_POKER_AUTO_FOLD:
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()

        elif ( packet.type == PACKET_POKER_SIT or
               packet.type == PACKET_POKER_SIT_REQUEST ):
            self.render(packet)
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()
            
        elif packet.type == PACKET_POKER_TIMEOUT_WARNING:
            self.render(packet)
            
        elif packet.type == PACKET_POKER_TIMEOUT_NOTICE:
            self.render(packet)
            self.changeState(CANCELED)
            
        elif packet.type == PACKET_POKER_WAIT_FOR:
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()
            
        elif packet.type == PACKET_POKER_IN_GAME:
            self.render(packet)
            
        elif packet.type == PACKET_POKER_WIN:
            self.render(packet)
            delay = self.delay(game, "showdown")
            reactor.callLater(delay, lambda: self.readyToPlay(packet.game_id))

        elif packet.type == PACKET_POKER_PLAYER_CHIPS:
            self.render(packet)
            self.render(PacketPokerClientPlayerChips(game_id = packet.game_id,
                                                     serial = packet.serial,
                                                     bet = self.protocol.normalizeChips(game, packet.bet),
                                                     money = self.protocol.normalizeChips(game, packet.money)))

        elif packet.type == PACKET_POKER_POT_CHIPS:
            self.render(packet)

        elif packet.type == PACKET_POKER_FOLD:
            self.handleFold(game, packet)
            self.render(packet)
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()
            
        elif packet.type == PACKET_POKER_CALL:
	    packet_copy = PacketPokerCall(game_id = packet.game_id,
					  serial = packet.serial)
	    packet_copy.amount = game.last_bet
            self.render(packet_copy)

        elif packet.type == PACKET_POKER_RAISE:
            self.render(packet)

        elif packet.type == PACKET_POKER_CHECK:
            self.render(packet)

        elif packet.type == PACKET_POKER_BLIND:
            self.render(packet)
            if packet.serial == self.protocol.getSerial():
                self.changeState(PAY_BLIND_ANTE_DONE)

        elif packet.type == PACKET_POKER_ANTE:
            self.render(packet)
            if packet.serial == self.protocol.getSerial():
                self.changeState(PAY_BLIND_ANTE_DONE)

        elif packet.type == PACKET_POKER_STATE:
            if self.state == MUCK and packet.string == "end":
                self.changeState(IDLE)


    def readyToPlay(self, game_id):
        if self.factory.getGame(game_id):
            self.sendPacket(PacketPokerReadyToPlay(game_id = game_id,
                                                   serial = self.protocol.getSerial()))

    def interactorSelected(self, packet):
        self.interactors.interactorSelected(packet)

    def interactorPreRaise(self, packet):
        self.interactors.cancelAllInteractors(packet.game_id)

    def sitActionsShow(self):
        interface = self.factory.interface
        if interface:
            interface.sitActionsShow()
            if not interface.callbacks.has_key(pokerinterface.INTERFACE_AUTO_BLIND):
                interface.registerHandler(pokerinterface.INTERFACE_AUTO_BLIND, self.autoBlind)
                interface.registerHandler(pokerinterface.INTERFACE_SIT_OUT, self.sitOut)
        self.render(PacketPokerInterfaceCommand(window = "sit_actions_window", command = "show"))

    def sitActionsHide(self):
        interface = self.factory.interface
        if interface:
            interface.sitActionsHide()
        self.render(PacketPokerInterfaceCommand(window = "sit_actions_window", command = "hide"))

    def sitActionsUpdate(self):
        interface = self.factory.interface
        if interface:
            game = self.factory.getGame(self.protocol.getCurrentGameId())
            player = game.getPlayer(self.protocol.getSerial())

            if self.verbose > 2: print "sitActionsUpdate: " + str(player)
                
            if player.wait_for == "big":
                interface.sitActionsSitOut("yes", _("wait for big blind"))
            elif player.wait_for:
                interface.sitActionsSitOut("yes", _("wait for %s blind") % player.wait_for, "insensitive")
            elif player.sit_out_next_turn:
                if game.isInGame(player.serial):
                    interface.sitActionsSitOut("yes", _("sit out next turn"))
                else:
                    interface.sitActionsSitOut("yes", _("sit out"))
            elif player.sit_requested:
                if game.isInGame(player.serial):
                    interface.sitActionsSitOut("no", _("sit out next turn"))
                else:
                    interface.sitActionsSitOut("no", _("sit out"))
            elif player.auto:
                interface.sitActionsSitOut("yes", _("sit out"))
            elif player.sit_out:
                interface.sitActionsSitOut("yes", _("sit out"))
            else:
                interface.sitActionsSitOut("no", _("sit out next turn"))

            if game.isTournament():
                interface.sitActionsAuto(None)
            elif player.auto_blind_ante:
                interface.sitActionsAuto("yes")
            else:
                interface.sitActionsAuto("no")

    def requestBuyIn(self, game):
        player = game.getPlayer(self.protocol.getSerial())

        #
        # We may enter this function while not seated at the table
        # if the seat was denied by the server (either wrong seat number
        # or race condition).
        #
        if not player:
            return False

        min_amount = max(0, game.buyIn() - player.money)
        max_amount = game.maxBuyIn() - player.money

        if max_amount <= 0:
            self.showMessage( _("You can't bring more money\nto the table"), None)
            return False

        money_cashier = 0
       
        if self.protocol.user_info.money.has_key(game.currency_serial):
            money_cashier = self.protocol.user_info.money[game.currency_serial][0]

        if player.isBuyInPayed():
            if money_cashier <= 0:
                self.showMessage( _("You have no money left"), None)
                self.sitActionsUpdate()
                return False

            legend = _("How much do you want to rebuy?")
        else:

            if min_amount > money_cashier:
                self.showMessage( _("You don't have enough money to play on this table.\nTo get money go in menu 'Lobby' and click 'Cash in'.\n(if you are in play money you might need to win more\nmoney to sit at this table)"), None)
                return False

            legend = _("Which amount do you want to bring at the table?")
        
        interface = self.factory.interface

        if max_amount >= money_cashier:
            label = _("All your bankroll")
        else:
            label = _("Maximum buy in")
        max_amount = min(max_amount, money_cashier)
        interface.buyInParams(min_amount, max_amount, legend, label)
        self.showBuyIn()
        if player.isBuyInPayed():
            callback = lambda value: self.rebuy(game, value)
        else:
            callback = lambda value: self.buyIn(game, value)
        interface.registerHandler(pokerinterface.INTERFACE_BUY_IN, callback)
        return True

    def showBuyIn(self):
        interface = self.factory.interface
        if interface: interface.buyInShow()
        self.render(PacketPokerInterfaceCommand(window = "buy_in_window", command = "show"))

    def hideBuyIn(self):
        interface = self.factory.interface
        if interface: interface.buyInHide()
        self.render(PacketPokerInterfaceCommand(window = "buy_in_window", command = "hide"))

    def buyIn(self, game, value, *args):
        interface = self.factory.interface
        interface.clearCallbacks(pokerinterface.INTERFACE_BUY_IN)
        self.protocol.sendPacket(PacketPokerBuyIn(serial = self.protocol.getSerial(),
                                                  game_id = game.id,
                                                  amount = value))
        self.protocol.sendPacket(PacketPokerSit(serial = self.protocol.getSerial(),
                                                game_id = game.id))
        self.changeState(BUY_IN_DONE)

    def rebuy(self, game, value):
        interface = self.factory.interface
        interface.clearCallbacks(pokerinterface.INTERFACE_BUY_IN)
        self.protocol.sendPacket(PacketPokerRebuy(serial = self.protocol.getSerial(),
                                                  game_id = game.id,
                                                  amount = value))
        self.changeState(REBUY_DONE, game)

    def resetLagmax(self):
        if self.verbose > 2: print "resetLagmax: %d" % ABSOLUTE_LAGMAX
        self.protocol._lagmax = ABSOLUTE_LAGMAX

    def updateLagmax(self, packet):
        if self.factory.packet2game(packet):
            if ( packet.type == PACKET_POKER_START or
                 ( packet.type == PACKET_POKER_POSITION and
                   packet.serial == self.protocol.getSerial() ) ):
                if self.verbose > 2: print "updateLagmax: %d" % self.protocol.lag
                self.protocol._lagmax = self.protocol.lag

    def hold(self, delay, id = None):
        if delay > 0 and not self.stream_mode:
            return
        self.protocol.hold(delay, id)
        
    def delay(self, game, event):

        if ( game.id == self.replayGameId and
             self.replayStepping ):
            self.hold(120, game.id)
            return

        delay = self.factory.delays.get(event, 1)
        self.hold(delay, game.id)
        return delay

    def handleFold(self, game, packet):
        pass

    def render(self, packet):
        display = self.factory.display
        if display: display.render(packet)
        
    def scheduleAction(self, packet):
        game = self.factory.packet2game(packet)
        if game.isRunning():
            action = False
            if packet.type == PACKET_POKER_RAISE:
                action = PacketPokerRaise(game_id = game.id,
                                          serial = self.protocol.getSerial(),
                                          amount = packet.amount[0] * self.bet_step)
            elif packet.action == "raise":
                action = PacketPokerRaise(game_id = game.id,
                                          serial = self.protocol.getSerial(),
                                          amount = 0)
            elif packet.action == "fold":
                action = PacketPokerFold(game_id = game.id,
                                         serial = self.protocol.getSerial())
            elif packet.action == "call":
                action = PacketPokerCall(game_id = game.id,
                                         serial = self.protocol.getSerial())
            elif packet.action == "check":
                action = PacketPokerCheck(game_id = game.id,
                                          serial = self.protocol.getSerial())

            if self.protocol.getSerial() != game.getSerialInPosition():
                if type(self.scheduledAction[game.id]) == type(action):
                    self.scheduledAction[game.id] = None
                else:
                    self.scheduledAction[game.id] = action
            else:                
                self.protocol.sendPacket(action)

    def wantToLeave(self):
        self.hold(0)
        
        if ( self.protocol.getCurrentGameId() and
             self.protocol.getCurrentGameId() == self.replayGameId ):
            self.protocol.sendPacket(PacketPokerTableDestroy(game_id = self.replayGameId))
            return True

        game_id = self.protocol.getCurrentGameId()
        game = self.factory.getGame(game_id)
        serial = self.protocol.getSerial()

        self.changeState(LEAVING_CONFIRM, game, serial)
        return True

    def maybeStartLookCards(self):
        current_gameid = self.protocol.getCurrentGameId()
        game = self.factory.getGame(current_gameid)
        if game.isRunning() is False:
            if self.verbose: print "ignoring look card the game is not running"
            return
        packet = PacketPokerPlayerMeLookCards(game_id = current_gameid, state = "start")
        self.schedulePacket(packet)

    def scheduleLookCardsAfterInteractionAnimation(self):
        current_gameid = self.protocol.getCurrentGameId()
        game = self.factory.getGame(current_gameid)
        if game.isRunning() is False:
            if self.verbose: print "ignoring look card the game is not running"
            return
        packet = PacketPokerPlayerMeLookCards(game_id = current_gameid, state = "start", when = "scheduled" )
        self.schedulePacket(packet)

    def maybeStopLookCards(self):
        current_gameid = self.protocol.getCurrentGameId()
        packet = PacketPokerPlayerMeLookCards(game_id = current_gameid, state = "stop")
        self.schedulePacket(packet)

    def setPlayerInFirstPerson(self):
        current_gameid = self.protocol.getCurrentGameId()
        packet = PacketPokerPlayerMeInFirstPerson(game_id = current_gameid, state = "true")
        self.schedulePacket(packet)

    def setPlayerNotInFirstPerson(self):
        current_gameid = self.protocol.getCurrentGameId()
        packet = PacketPokerPlayerMeInFirstPerson(game_id = current_gameid, state = "false")
        self.schedulePacket(packet)

    def clickSitOut(self):
        if self.factory.verbose: print "clickSitOut python"
        interface = self.factory.interface
        interface.sitActionsToggleSitOut()
        return True

    def state2hide(self):
        interface = self.factory.interface
        if not interface:
            return
        status = True
        if self.state == LOBBY:
            self.hideLobby()
        elif self.state == HAND_LIST:
            self.hideHands()
        elif self.state == TOURNAMENTS:
            self.hideTournaments()
        elif self.state == CASHIER:
            self.hideCashier()
        elif self.state == MUCK:                
            self.hideMuck()
        elif self.state == IDLE:
            pass
        elif self.state == SEARCHING_MY:
            pass
        elif self.state == QUIT:
            pass
        else:
            status = False
        return status

    def canHideInterface(self):
        return ( self.state == LOBBY or
                 self.state == HAND_LIST or
                 self.state == TOURNAMENTS or
                 self.state == CASHIER or
                 self.state == IDLE )

    def displayCredits(self):
        interface = self.factory.interface
        if interface:
            interface.credits(self.factory.config.headerGet("/sequence/credits"))
        
    def handleMenu(self, name, value):
        settings = self.factory.settings
        if name == "login":
            if self.canHideInterface():
                current_state = self.state
                self.changeState(LOGIN, lambda success: self.changeState(current_state))
        elif name == "help":
            self.factory.browseWeb("")
        elif name == "credits":
            self.displayCredits()
        elif name == "license":
            config = self.factory.config
            url = config.headerGet("/sequence/licenses/" + str(value)) or config.headerGet("/sequence/licenses/@list")
            PokerChildBrowser(config, settings, url)
        elif name == "cashier":
            self.changeState(CASHIER)
        elif name == "cash_in" or name == "cash_out":
            self.factory.browseWeb(name + ".php?serial=%d&name=%s" % ( self.protocol.getSerial(), self.protocol.getName() ))
        elif name == "outfits":
            self.changeState(OUTFIT)
        elif name == "edit_account":
            self.factory.browseWeb("edit_account.php?serial=%d&name=%s" % ( self.protocol.getSerial(), self.protocol.getName() ))
        elif name == "hand_history":
            self.changeState(HAND_LIST)
        elif name == "quit":
            self.pythonEvent("QUIT")
        elif name == "tables_list":
            self.changeState(LOBBY)
        elif name == "tournaments":
            self.changeState(TOURNAMENTS)
        elif name == "resolution":
            if value == "resolution_auto":
                value = "0x0"
            (width, height) = value.split("x")
            settings.headerSet("/settings/screen/@width", width)
            settings.headerSet("/settings/screen/@height", height)
            settings.save()
            self.queryRestart(_("Screen resolution changed"))
        elif name == "display":
            settings.headerSet("/settings/@display2d", value == "2d" and "yes" or "no")
            settings.headerSet("/settings/@display3d", value == "3d" and "yes" or "no")
            settings.save()
            self.queryRestart(_("Display changed to ") + value)
        elif name == "fullscreen":
            settings.headerSet("/settings/screen/@fullscreen", value)
            settings.save()
            self.queryRestart(_("Screen resolution changed"))
        elif name == "graphics":
            settings.headerSet("/settings/shadow", value)
            settings.headerSet("/settings/vprogram", value)
            settings.headerSet("/settings/glow", value)
            settings.save()
            self.queryRestart(_("Graphics quality changed"))
        elif name == "sound":
            display = self.factory.display
            value = display.setSoundEnabled(value=="yes")
            if value is not 0:
                value = "yes"
            else:
                value = "no"
            settings.headerSet("/settings/sound", value)
            settings.save()
        elif name == "auto_post":
            settings.headerSet("/settings/auto_post", value)
            settings.save()
        elif name == "remember_me":
            settings.headerSet("/settings/remember", value)
            settings.save()
        elif name == "muck":
            settings.headerSet("/settings/muck", value)
            settings.save()
            auto_muck = pokergame.AUTO_MUCK_ALWAYS
            if value == "no":
                auto_muck = pokergame.AUTO_MUCK_NEVER
            self.broadcastAutoMuckChange(auto_muck)
        else:
            print "*CRITICAL* handleMenu unknown name %s" % name

    def wantToRestart(self, status):
        self.hideYesNoBox()
        if status:
            self.factory.restart()

    def queryRestart(self, message):
        interface = self.factory.interface
        self.showYesNoBox(message + "\n" +
                          _("The game must be restarted for this change to take effect\n") +
                          _("Do you want to restart the game now ?"))
        interface.registerHandler(pokerinterface.INTERFACE_YESNO, self.wantToRestart)

        
    def isSeated(self):
        game_id = self.protocol.getCurrentGameId()
        game = self.factory.getGame(game_id)
        serial = self.protocol.getSerial()
        return game and game.isSeated(serial)
        
    def selectOutfit(self, url, outfit):
        if self.state == OUTFIT:
            skin = self.factory.getSkin()
            skin.setUrl(url)
            skin.setOutfit(outfit)
            if outfit != None:
                self.protocol.sendPacket(PacketPokerPlayerInfo(serial = self.protocol.getSerial(),
                                                               name = self.protocol.user.name,
                                                               url = url,
                                                               outfit = outfit
                                                               ))
            self.changeState(OUTFIT_DONE)

    def handleLobby(self, args):
        if self.verbose > 2: print "handleLobby: " + str(args)
        if not self.protocol: return

        (action, value) = args
        if action == "details":
            game_id = int(value)
            self.state_lobby["current"] = game_id
            self.protocol.sendPacket(PacketPokerTableRequestPlayersList(game_id = game_id))

        elif action == "join":
            self.connectTable(int(value))

        elif action == "refresh":
            if value == "money_one" or value == "money_two":
                self.state_lobby['currency_serial'] = self.money[value]['serial']
            elif value == "all":
                self.state_lobby['currency_serial'] = 0
            else:
                self.state_lobby['type'] = value
            self.queryLobby()

        elif action == "quit":
            if value == "cashier":
                self.changeState(CASHIER)
            else:
                self.changeState(TOURNAMENTS, value)
        else:
            print "*CRITICAL*: handleLobby: unknown action " + action

    def queryLobby(self):
        if self.state == LOBBY and self.protocol:
            currency_serial = self.state_lobby['currency_serial'] or ''
            criterion = str(currency_serial) + "\t" + self.state_lobby['type']
            self.protocol.sendPacket(PacketPokerTableSelect(string = criterion))
            timer = self.state_lobby.get('timer', None)
            if not timer or not timer.active():
                self.state_lobby['timer'] = reactor.callLater(30, self.queryLobby)
        
    def saveLobbyState(self):
        settings = self.factory.settings
        state = self.state_lobby
        settings.headerSet("/settings/lobby/@currency_serial", str(state['currency_serial']))
        settings.headerSet("/settings/lobby/@type", state['type'])
        settings.headerSet("/settings/lobby/@sort", state['sort'])
        settings.save()
        
    def updateLobbyPlayersList(self, packet):
        if self.state != LOBBY:
            return
        interface = self.factory.interface
        if not interface:
            return
        interface.updateLobbyPlayersList(packet.players)
        
    def updateLobby(self, packet):
        if self.state != LOBBY:
            return
        interface = self.factory.interface
        tables = packet.packets
        tables_map = dict(zip(map(lambda table: table.id, tables), tables))
        self.state_lobby["tables"] = tables_map
        game_id = self.state_lobby["current"]
        if not tables_map.has_key(game_id):
            game_id = 0
        if interface:
            interface.updateLobby(packet.players, packet.tables, game_id, self.factory.translateFile2Name, self.factory.getGameIds(), packet.packets)

    def currencySerial2Name(self, currency_serial):
        if self.verbose > 2:
            print "currencySerial2Name " + str(currency_serial)
        if type(currency_serial) is StringType:
            raise UserWarning
        if currency_serial == 0:
            return ''
        elif self.money_serial2name.has_key(currency_serial):
            return self.money_serial2name[currency_serial]
        else:
            raise UserWarning, "currencySerial2Name unknown serial " + str(currency_serial)
        
    def showLobby(self, type = None):
        interface = self.factory.interface
        if interface:
            if type:
                self.state_lobby['type'] = type
            else:
                type = self.state_lobby['type']
            interface.showLobby(self.state_lobby['cashier_label'], type, self.currencySerial2Name(self.state_lobby['currency_serial']), self.money['money_one']['name'], self.money['money_two']['name'])
        self.render(PacketPokerInterfaceCommand(window = "tournaments_lobby_tabs_window", command = "hide")) # TODO remove reference to tournaments_lobby_tabs_window
        self.render(PacketPokerInterfaceCommand(window = "lobby_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "table_info_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "cashier_button_window", command = "show"))

    def hideLobby(self):
        interface = self.factory.interface
        if interface:
            interface.hideLobby()
        self.render(PacketPokerInterfaceCommand(window = "lobby_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "table_info_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "cashier_button_window", command = "hide"))

    def showClockWindow(self):
        self.render(PacketPokerInterfaceCommand(window = "clock_window", command = "show"))

    def hideClockWindow(self):
        self.render(PacketPokerInterfaceCommand(window = "clock_window", command = "hide"))

    def showBackgroundLobbyCashier(self):
        self.render(PacketPokerInterfaceCommand(window = "background_lobby_cashier_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "background_window", command = "show"))

    def hideBackgroundLobbyCashier(self):
        self.render(PacketPokerInterfaceCommand(window = "background_lobby_cashier_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "background_window", command = "hide"))
        

    def showOutfit(self):
        self.factory.getSkin().showOutfitEditor(self.selectOutfit)
        self.render(PacketPokerInterfaceCommand(window = "outfit_sex_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_ok_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_random_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_params", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_slots_male_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_slots_female_window", command = "show"))
        
    def hideOutfit(self):
        self.factory.getSkin().hideOutfitEditor()
        self.render(PacketPokerInterfaceCommand(window = "outfit_sex_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_ok_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_random_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_params", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_slots_male_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "outfit_slots_female_window", command = "hide"))
        
    def handleTournaments(self, args):
        if self.verbose > 2: print "handleTournaments: " + str(args)
        (action, value) = args
        if action == "details":
            tourney_id = int(value)
            self.state_tournaments["current"] = tourney_id
            self.protocol.sendPacket(PacketPokerTourneyRequestPlayersList(game_id = tourney_id))

        elif action == "register":
            self.changeState(TOURNAMENTS_REGISTER, int(value))

        elif action == "unregister":
            self.changeState(TOURNAMENTS_UNREGISTER, int(value))

        elif action == "refresh":
            if value == "money_one" or value == "money_two":
                self.state_tournaments['currency_serial'] = self.money[value]['serial']
            elif value == "all":
                self.state_tournaments['currency_serial'] = 0
            else:
                self.state_tournaments['type'] = value
            self.queryTournaments()
        elif action == "quit":
            if value == "cashier":
                self.changeState(CASHIER)
            else:
                self.changeState(LOBBY, value)
        else:
            print "*CRITICAL* : handleTournaments: unknown action " + action

    def queryTournaments(self):
        if self.state == TOURNAMENTS:
            currency_serial = self.state_tournaments['currency_serial'] or ''
            criterion = str(currency_serial) + "\t" + self.state_tournaments['type']
            self.protocol.sendPacket(PacketPokerTourneySelect(string = criterion))
            timer = self.state_tournaments.get('timer', None)
            if not timer or not timer.active():
                self.state_tournaments['timer'] = reactor.callLater(30, self.queryTournaments)
        
    def saveTournamentsState(self):
        settings = self.factory.settings
        state = self.state_tournaments
        settings.headerSet("/settings/tournaments/@currency_serial", str(state['currency_serial']))
        settings.headerSet("/settings/tournaments/@type", state['type'])
        settings.headerSet("/settings/tournaments/@sort", state['sort'])
        settings.save()
        
    def updateTournamentsPlayersList(self, packet):
        if self.state != TOURNAMENTS:
            return
        interface = self.factory.interface
        if not interface:
            return

        # discard the update if we are not the current tournament
        if not self.state_tournaments["tournaments"].has_key(packet.serial):
            return

        tournament = self.state_tournaments["tournaments"][packet.serial]
        can_register = None
        if tournament.state == "registering":
            can_register = self.protocol.getName() not in map(lambda player: player[0], packet.players)
        interface.updateTournamentsPlayersList(can_register, packet.players)
        
    def updateTournaments(self, packet):
        if self.state != TOURNAMENTS:
            return
        tournaments = packet.packets
        tournaments_map = dict(zip(map(lambda tournament: tournament.serial, tournaments), tournaments))
        self.state_tournaments["tournaments"] = tournaments_map
        tournament_id = self.state_tournaments["current"]
        if not tournaments_map.has_key(tournament_id):
            tournament_id = 0
        interface = self.factory.interface
        if interface:
            interface.updateTournaments(packet.players, packet.tourneys, tournament_id, tournaments)

    def showTournaments(self, type = None):
        interface = self.factory.interface
        if interface:
            if type:
                self.state_tournaments['type'] = type
            else:
                type = self.state_tournaments['type']
            interface.showTournaments(self.state_tournaments['cashier_label'], type, self.currencySerial2Name(self.state_tournaments['currency_serial']), self.money['money_one']['name'], self.money['money_two']['name'])
        self.render(PacketPokerInterfaceCommand(window = "tournaments_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "tournament_info_window", command = "show"))
        self.render(PacketPokerInterfaceCommand(window = "tournaments_cashier_button_window", command = "show"))
        
    def hideTournaments(self):
        interface = self.factory.interface
        if interface:
            interface.hideTournaments()
        self.saveTournamentsState()
        self.render(PacketPokerInterfaceCommand(window = "tournaments_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "tournament_info_window", command = "hide"))
        self.render(PacketPokerInterfaceCommand(window = "tournaments_cashier_button_window", command = "hide"))
        
    def handReplay(self, hand):
        self.protocol.sendPacket(PacketPokerHandReplay(serial = hand))

    def replayStep(self):
        self.hold(0)
    
    def handleHands(self, *args):
        interface = self.factory.interface
        action = args[0]
        if action == "replay":
            if self.state == HAND_LIST and value != None:
                self.handReplay(value)
            elif hand != None:
                print "*CRITICAL* selectHand: ignored because not in HAND_LIST state"
        elif action == "show":
            ( action, game_id ) = args
            self.protocol.sendPacket(PacketPokerHandHistory(game_id = game_id,
                                                            serial = self.protocol.getSerial()))
        elif action == "next":
            state = self.state_hands
            if state["start"] + state["count"] < state["total"]:
                state["start"] += state["count"]
                self.queryHands()
        elif action == "previous":
            state = self.state_hands
            if state["start"] - state["count"] >= 0:
                state["start"] -= state["count"]
                self.queryHands()
        elif action == "quit":
            previous_state = self.state_hands.get("previous_state", LOBBY)
            self.changeState(previous_state)
        else:
            print "*CRITICAL*: selectHands unexpected action " + action
    
    def showHands(self, hands, total):
        interface = self.factory.interface
        if interface:
            state = self.state_hands
            state["total"] = total
            if hands:
                interface.showHands(hands, state["start"], state["count"], state["total"])
            else:
                self.showMessage(_("Your hand history is empty"), None)
                self.changeState(IDLE)

    def showHandHistory(self, hand_serial, history, serial2name):
        interface = self.factory.interface
        if interface:
            (type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips) = history[0]
            game = PokerGameClient("poker.%s.xml", self.factory.dirs)
            game.name = "*REPLAY*"
            game.setVariant(variant)
            game.setBettingStructure(betting_structure)
            messages = history2messages(game, history, serial2name = lambda serial: serial2name.get(serial, "Unknown"), pocket_messages = True)
            interface.showHandMessages(hand_serial, messages)

    def hideHands(self):
        interface = self.factory.interface
        if interface:
            interface.hideHands()
        
    def queryHands(self):
        self.protocol.sendPacket(PacketPokerHandSelect(string = "",
                                                       start = self.state_hands["start"],
                                                       count = self.state_hands["count"],
                                                       ))
        
    def queryAllHands(self):
        self.state = HAND_LIST
        self.protocol.sendPacket(PacketPokerHandSelectAll(string = "hands.name is not null"))
        
    def choseTable(self, tables):
        if not tables:
            self.changeState(SEARCHING_MY_CANCEL)
        else:
            self.changeState(JOINING_MY, *tables)

    def rotateTable(self, dummy = None):
        if not self.factory.games:
            return
        game_ids = self.factory.games.keys()
        if self.protocol.getCurrentGameId() and len(game_ids) > 1:
            current = game_ids.index(self.protocol.getCurrentGameId())
            game_ids = game_ids[current:] + game_ids[:current]
            if self.verbose > 1: print "rotateTable: %d => %d" % ( self.protocol.getCurrentGameId(), game_ids[1])
            self.connectTable(game_ids[1])
        else:
            self.connectTable(game_ids[0])
        
    def connectTable(self, game_id):
        serial = self.protocol.getSerial()
        current_game_id = self.protocol.getCurrentGameId()
        done = False
        if current_game_id == game_id:
            self.changeState(IDLE)
        else:
            current_game = self.factory.getGame(current_game_id)
            if current_game:
                #
                # Do not hold a game we do not display
                #
                self.readyToPlay(current_game_id)
                if not current_game.isSeated(serial):
                    #
                    # Forget about tables where we do not sit
                    #
                    self.protocol.sendPacket(PacketPokerTableQuit(game_id = current_game_id,
                                                                  serial = serial))
                    
            game = self.factory.getGame(game_id)
            
            if not game:
                #
                # Join the table we've not joined yet
                #
                self.changeState(JOINING, game_id, serial)
            else:
                #
                # Restore the display of a table for which we already
                # know everything.
                #
                reactor.callLater(0.01, self.protocol.resendPackets, game_id)
                self.hold(0)
                self.changeState(JOINING_DONE)

    def deleteGames(self):
        for game_id in self.factory.games.keys():
            self.deleteGame(game_id)
        
    def deleteGame(self, game_id):
        display = self.factory.display
        display.render(PacketPokerTableDestroy(game_id = game_id))
        self.protocol.deleteGame(game_id)
        self.interactors.deleteInteractorSet(game_id)

    def sendPacketSitOut(self, packet):
        self.sendPacket(packet)
        self.factory.interface.sitActionsSitOut("yes", "sit out next hand")
        
    def sendPacketSit(self, packet):
        self.sendPacket(packet)
        self.factory.interface.sitActionsSitOut("no", "sit out")
        
    def sendPacket(self, packet):
        if self.verbose > 2: print "render sendPacket %s" % packet
        return self.protocol.sendPacket(packet)
        
    def schedulePacket(self, packet):
        if self.verbose > 2: print "render schedulePacket %s" % packet
        return self.protocol.schedulePacket(packet)
        
    def getSeat(self, packet):
        if self.verbose > 2: print "getSeat %s" % packet
        self.changeState(SEATING, packet)

    def bootstrap(self):
        self.sendPacket(PacketPokerSetRole(roles = PacketPokerRoles.PLAY))
        if not self.factory.first_time:
            if self.factory.interface:
                if self.verbose: print "interface ready, ask for password"
                self.changeState(LOGIN, lambda success: self.changeState(LOBBY))
            else:
                if self.verbose: print "interface not ready, will ask password later"
        else:
            self.changeState(LOBBY)
        self.factory.display.setRenderer(self)

    def reload(self):
        self.factory.reload()

    def enterStates(self, previous_state, next_state, states):
        return previous_state not in states and next_state in states
    
    def exitStates(self, previous_state, next_state, states):
        return previous_state in states and next_state not in states
    
    def updateInterfaceWindows(self, previous_state, next_state):
        if self.exitStates(previous_state, next_state, (LOBBY, CASHIER, TOURNAMENTS)) and not self.enterStates(previous_state, next_state, (QUIT)):
            self.hideBackgroundLobbyCashier()
            self.hideClockWindow()
        elif self.enterStates(previous_state, next_state, (LOBBY, CASHIER, TOURNAMENTS)) and not self.exitStates(previous_state, next_state, (QUIT)):
            self.showBackgroundLobbyCashier()
            self.showClockWindow()
        if self.exitStates(previous_state, next_state, (LOBBY, TOURNAMENTS)) and not self.enterStates(previous_state, next_state, (QUIT)):
            self.render(PacketPokerInterfaceCommand(window = "lobby_tabs_window", command = "hide"))
        elif self.enterStates(previous_state, next_state, (LOBBY, TOURNAMENTS)) and not self.exitStates(previous_state, next_state, (QUIT)):
            self.render(PacketPokerInterfaceCommand(window = "lobby_tabs_window", command = "show"))

    def changeState(self, state, *args, **kwargs):
        if self.state == state:
            return

        if not self.stream_mode:
            return

        if self.verbose > 2: print "changeState %s => %s (args = %s, kwargs = %s)" % ( self.state, state, str(args), str(kwargs) )
        current_state = self.state

        if current_state == QUIT and state != QUIT_DONE:
            # restore state before quit state and recall changeState so the transition is
            # as we didn't have a quit request
            self.state = self.quit_state
            self.quit_state = None
            self.hideYesNoBox()
            self.changeState(state, *args, **kwargs)

        elif state == LOBBY and ( self.state2hide() or self.state == SEARCHING_MY ):
            self.state = state
            self.showLobby(*args)
            self.factory.interface.showMenu()
            self.queryLobby()

        elif state == SEARCHING_MY and ( self.state2hide() or self.state == LOGIN ):
            self.protocol.sendPacket(PacketPokerTableSelect(string = "my"))
            self.state = state

        elif state == PAY_BLIND_ANTE:
            if not self.state2hide():
                if ( self.state == USER_INFO or
                     self.state == REBUY ):
                    self.hideBuyIn()
                else:
                    print "*CRITICAL*  unexpected state " + self.state
                    return
            what = args[0]
            args = args[1:]
            if what == 'ante':
                self.payAnte(*args)
            elif what == 'blind':
                self.payBlind(*args)
            else:
                print "*CRITICAL*  unknow what " + what
            self.state = state

        elif state == PAY_BLIND_ANTE_SEND and self.state == PAY_BLIND_ANTE:
            what = args[0]
            args = args[1:]
            if what == 'ante':
                status = self.confirmPayAnte(*args)
            elif what == 'blind':
                status = self.confirmPayBlind(*args)
            else:
                status = False
                print "*CRITICAL*  unknow what " + what
            self.state = status and state or IDLE

        elif state == PAY_BLIND_ANTE_DONE:
            if self.state == PAY_BLIND_ANTE_SEND:
                self.hideBlind()
            
            self.changeState(IDLE)

        elif state == LOGIN:
            if self.protocol.user.isLogged():
                self.showMessage(_("Already logged in"), None)
            else:
                self.state2hide()
                self.factory.interface.showMenu()
                self.state_login = args[0]
                self.requestLogin()
                self.state = state

        elif state == LOGIN_DONE:
            self.factory.interface.hideLogin()
            previous_state = self.state
            self.state = IDLE
            if previous_state != JOINING_DONE:
                self.state_login(args[0])

        elif state == CASHIER:
            if self.protocol.user.isLogged():
                if self.state2hide():
                    self.protocol.sendPacket(PacketPokerGetPersonalInfo(serial = self.protocol.getSerial()))
                    self.state = state

            elif self.canHideInterface():
                state = self.state
                def login_callback(success):
                    if success:
                        self.changeState(CASHIER, *args, **kwargs)
                    else:
                        self.changeState(state)
                self.changeState(LOGIN, login_callback)

            else:
                print "*CRITICAL*; should not be here"
                self.showMessage(_("You cannot do that now"), None)

        elif state == USER_INFO:
            self.state2hide()
            self.state_buy_in = args
            self.protocol.sendPacket(PacketPokerGetUserInfo(serial = self.protocol.getSerial()))
            self.state = state

        elif state == USER_INFO_DONE and self.state == USER_INFO:
            self.changeState(*self.state_buy_in)

        elif state == BUY_IN and self.state == USER_INFO:
            if self.requestBuyIn(args[0]):
                self.state = state
            else:
                self.state = IDLE

        elif state == BUY_IN_DONE:
            self.hideBuyIn()
            self.changeState(IDLE)
            
        elif state == REBUY and self.state == USER_INFO:
            if self.requestBuyIn(*args):
                self.state = state
            else:
                self.state = IDLE
            
        elif state == REBUY_DONE:
            self.hideBuyIn()
            game = args[0]
            serial = self.protocol.getSerial()
            if not game.isSit(serial):
                self.sendPacket(PacketPokerSit(game_id = game.id,
                                               serial = serial))
            self.changeState(IDLE)
            
        elif state == JOINING and self.state == LOBBY:
            ( game_id, serial ) = args
            self.protocol.sendPacket(PacketPokerTableJoin(game_id = game_id,
                                                          serial = serial))
            self.state = state
            
        elif state == JOINING_MY and self.state == SEARCHING_MY:
            for table in args:
                self.protocol.sendPacket(PacketPokerTableJoin(game_id = table.id,
                                                              serial = self.protocol.getSerial()))
            self.state_joining_my = len(args)
            self.state = state

        elif state == SEARCHING_MY_CANCEL:
            if self.factory.first_time:
                self.factory.first_time = False
                self.state_outfit = lambda: self.changeState(LOGIN_DONE, True)
                self.changeState(OUTFIT)
            else:
                self.changeState(LOGIN_DONE, True)
            
        elif state == TOURNAMENTS and self.state2hide():
            self.state = state
            self.showTournaments(*args)
            self.queryTournaments()

        elif state == TOURNAMENTS_REGISTER and self.state == TOURNAMENTS:
            if self.protocol.user.isLogged():
                game_id = args[0]
                serial = self.protocol.getSerial()
                self.protocol.sendPacket(PacketPokerTourneyRegister(game_id = game_id,
                                                                    serial = serial))
                self.state = TOURNAMENTS_REGISTER
            else:
                def login_callback(success):
                    if success:
                        self.state = TOURNAMENTS
                        self.changeState(TOURNAMENTS_REGISTER, *args, **kwargs)
                    else:
                        self.changeState(TOURNAMENTS)
                self.changeState(LOGIN, login_callback)
            
        elif state == TOURNAMENTS_REGISTER_DONE and self.state == TOURNAMENTS_REGISTER:
            self.state = IDLE
            self.changeState(TOURNAMENTS)

        elif state == TOURNAMENTS_UNREGISTER and self.state == TOURNAMENTS:
            game_id = args[0]
            serial = self.protocol.getSerial()
            self.protocol.sendPacket(PacketPokerTourneyUnregister(game_id = game_id,
                                                                  serial = serial))
            self.state = TOURNAMENTS_UNREGISTER
            
        elif state == TOURNAMENTS_UNREGISTER_DONE and self.state == TOURNAMENTS_UNREGISTER:
            self.state = IDLE
            self.changeState(TOURNAMENTS)

        elif state == SEATING:
            if self.protocol.user.isLogged():
                if self.state2hide():
                    packet = args[0]
                    packet.serial = self.protocol.getSerial()
                    self.state_buy_in = self.factory.getGame(packet.game_id)
                    self.protocol.sendPacket(packet)
                    if self.factory.settings.headerGet("/settings/auto_post") == "yes":
                        self.protocol.sendPacket(PacketPokerAutoBlindAnte(game_id = packet.game_id,
                                                                          serial = packet.serial))
                                                                          
                    if self.factory.settings.headerGet("/settings/muck") == "no":
                        self.protocol.sendPacket(PacketPokerAutoMuck(game_id = packet.game_id,
                                                                     serial = packet.serial,
                                                                     auto_muck = pokergame.AUTO_MUCK_NEVER))
                    self.state = state
                else:
                    self.showMessage(_("You cannot do that now"), None)
                    
            elif self.canHideInterface():
                def login_callback(success):
                    if success:
                        self.changeState(SEATING, *args, **kwargs)
                    else:
                        self.showMessage(_("You must be logged in to get a seat"), None)
                self.changeState(LOGIN, login_callback)

            else:
                print "*CRITICAL*; should not be here"
                self.showMessage(_("You cannot do that now"), None)

        elif state == LEAVING_DONE and self.state == LEAVING:
            self.hideBlind()
            self.hideBuyIn()
            self.sitActionsHide()
            self.state = IDLE
            if self.factory.display and self.factory.interface:
                self.changeState(LOBBY)
            
        elif state == LEAVING_CANCEL:
            self.state = IDLE
            
        elif state == JOINING_DONE:
            self.hideBlind()
            self.hideBuyIn()
            self.sitActionsHide()
            self.hideCashier()
            self.hideLobby()
            self.hideTournaments()

            if self.state == JOINING_MY:
                self.state_joining_my -= 1
                if self.state_joining_my <= 0:
                    self.state = state
                    self.changeState(LOGIN_DONE, True)
            else:
                self.state = IDLE
            
        elif state == LEAVING:
            ( game, serial ) = args

            self.state = state
            if ( game and game.isSeated(serial) ):
                packet = PacketPokerPlayerLeave(game_id = game.id,
                                                serial = serial)
                self.protocol.sendPacket(packet)
            self.changeState(LEAVING_DONE)

        elif state == LEAVING_CONFIRM:
            ( game, serial ) = args

            def confirm(response):
                self.hideYesNoBox()
                if response:
                    self.changeState(LEAVING, *args)
                else:
                    self.state = IDLE

            interface = self.factory.interface
            if game and game.getPlayer(serial):
                if game.isInGame(serial):
                    self.showYesNoBox(_("Do you really want to fold your hand\nand leave the table ?"))
                    interface.registerHandler(pokerinterface.INTERFACE_YESNO, confirm)
                else:
                    self.showYesNoBox(_("Do you really want to leave the table ?"))
                    interface.registerHandler(pokerinterface.INTERFACE_YESNO, confirm)
            else:
                self.changeState(LEAVING, *args)

        elif state == CANCELED:
            if self.state == PAY_BLIND_ANTE:
                self.hideBlind()
                self.state = IDLE
            if self.interactorSelectedData != None:
                self.interactorSelectedData = None
                self.interactorSelectedDataPacket = None
                self.hideCheckWarningBox()                

        elif state == SIT_OUT:
            if self.state == PAY_BLIND_ANTE:
                self.hideBlind()
                self.state = IDLE

        elif state == OUTFIT:
            if self.protocol and self.protocol.user.isLogged():
                if self.isSeated():
                    self.showMessage(_("You must leave the table to change your outfit"), None)
                else:
                    if self.state2hide():
                        self.showOutfit()
                        self.factory.interface.hideMenu()
                        self.state = state

            elif self.canHideInterface():
                state = self.state
                def login_callback(success):
                    if success:
                        self.changeState(OUTFIT, *args, **kwargs)
                    else:
                        self.changeState(state)
                self.changeState(LOGIN, login_callback)

            else:
                print "*CRITICAL*; should not be here"
                self.showMessage(_("You cannot do that now"), None)

        elif state == OUTFIT_DONE and self.state == OUTFIT:
            self.hideOutfit()
            self.factory.interface.showMenu()
            self.state = IDLE
            if self.state_outfit != None:
                state_outfit = self.state_outfit
                self.state_outfit = None
                state_outfit()
            else:
                self.changeState(LOBBY)
            
        elif state == HAND_LIST:
            self.state_hands["previous_state"] = self.state
            if self.protocol.user.isLogged():
                if self.state2hide():
                    self.state = state
                    self.state_hands["start"] = 0
                    self.queryHands()
                else:
                    self.showMessage(_("You cannot do that now"), None)

            elif self.canHideInterface():
                state = self.state
                def login_callback(success):
                    if success:
                        self.changeState(HAND_LIST, *args, **kwargs)
                    else:
                        self.changeState(state)
                self.changeState(LOGIN, login_callback)

            else:
                print "*CRITICAL*; should not be here"
                self.showMessage(_("You cannot do that now"), None)

        elif state == QUIT:
            self.state = state

        elif state == QUIT_DONE:
            self.state = state

        elif state == IDLE:
            self.state2hide()
            self.state = state

        elif state == MUCK:
            game = args[0]
            if self.state == IDLE:
                self.showMuck(game)
                self.state = state
            else:
                self.postMuck(True)
            
        if self.state == IDLE:
            self.chatShow()
        else:
            self.chatHide()
        if current_state != self.state:
            self.render(PacketPokerRendererState(state = self.state))
            self.updateInterfaceWindows(current_state, self.state)

            
