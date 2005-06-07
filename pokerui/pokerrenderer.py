#
# Copyright (C) 2004 Mekensleep
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#

from twisted.internet import reactor

from string import join
from time import sleep
from formatter import DumbWriter
from StringIO import StringIO
from random import choice

from pokereval import PokerEval
from pokerengine.pokergame import PokerGameClient, PokerPlayer, history2messages
from pokerengine.pokercards import PokerCards
from pokerengine.pokerchips import PokerChips
from pokernetwork.pokerpackets import *
from pokerui import pokerinterface
from pokerui.pokerinteractor import PokerInteractor, PokerInteractorSet
from pokerui.pokerchat import PokerChat

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
LOGOUT = "logout"
JOINING = "joining"
JOINING_MY = "joining_my"
JOINING_DONE = "joining_done"
LEAVING = "leaving"
LEAVING_DONE = "leaving_done"
LEAVING_CANCEL = "leaving_cancel"
CANCELED = "canceled"
SIT_OUT = "sit_out"
    
class PokerRenderer:

    def __init__(self, factory):
        self.replayStepping = True
        self.replayGameId = None
#        self.scheduledAction = {}
#        self.futureAction = {}
        self.state = IDLE
        self.state_buy_in = ()
        self.state_login = ()
        self.state_tournaments = factory.settings.headerGetProperties("/settings/tournaments")
        if not self.state_tournaments:
            print "CRITICAL: missing /settings/tournaments"
        else:
            self.state_tournaments = self.state_tournaments[0]
        self.state_tournaments["current"] = 0
        self.state_lobby = factory.settings.headerGetProperties("/settings/lobby")
        if not self.state_lobby:
            print "CRITICAL: missing /settings/lobby"
        else:
            self.state_lobby = self.state_lobby[0]
        self.state_lobby["current"] = 0
        self.state_joining_my = 0
        self.factory = factory
        self.protocol = None
        self.stream_mode = True
        self.bet_step = 1 # else if a human is already here we don't receive a packet POKER_BET_LIMIT and if we don't receive this packet bet_step is not defined
        self.interactors_evaluate = False
        self.interactors_map = { }
        self.interactors = { }

    def deleteInteractorSet(self, game_id):
        if self.interactors_map.has_key(game_id):
            del self.interactors_map[game_id]
            
    def getOrCreateInteractorSet(self, game_id):
        if self.interactors_map.has_key(game_id) == False:
            display = self.factory.settings.headerGet("/settings/@display3d") == "yes" and "3d" or "2d"
            self.interactors_map[game_id] = PokerInteractorSet(check = PokerInteractor("check",
                                                                                       self.interactorAction,
                                                                                       self.interactorDisplayNode,
                                                                                       self.interactorSelectedCallback,
                                                                                       self.factory.config.headerGetProperties("/sequence/interactors"+display+"/check/map")[0],
                                                                                       game_id,
                                                                                       self.factory.verbose),
                                                               fold = PokerInteractor("fold",
                                                                                      self.interactorAction,
                                                                                      self.interactorDisplayNode,
                                                                                      self.interactorSelectedCallback,
                                                                                      self.factory.config.headerGetProperties("/sequence/interactors"+display+"/fold/map")[0],
                                                                                      game_id,
                                                                                      self.factory.verbose),
                                                               shadowstacks = PokerInteractor("shadowstacks",
                                                                                              self.interactorAction,
                                                                                              self.interactorDisplayShadowStacks,
                                                                                              self.interactorSelectedCallback,
                                                                                              self.factory.config.headerGetProperties("/sequence/interactors"+display+"/shadowstacks/map")[0],
                                                                                              game_id,
                                                                                              self.factory.verbose))
        return self.interactors_map[game_id]        

    def setProtocol(self, protocol):
        self.protocol = protocol
        if protocol:
            self.protocol.play_money = -1
            protocol.registerHandler("current", None, self._handleConnection)
            protocol.registerHandler("outbound", None, self._handleConnection)
            
    def logout(self):
        self.changeState(LOGOUT)

    def quit(self):
        self.factory.quit()

    def confirmQuit(self):
        if self.protocol:
            self.sendPacket(PacketQuit())
        
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
        if yesno:
            self.protocol.sendPacket(PacketPokerSitOut(game_id = game_id,
                                                       serial = serial))
        else:
            game = self.factory.getGame(game_id)
            if game.isBroke(serial):
                self.changeState(USER_INFO, REBUY, game)
            else:
                self.protocol.sendPacket(PacketPokerSit(serial = serial,
                                                        game_id = game_id))
        
    def payAnte(self, game, amount):
        interface = self.factory.interface
        if interface and not interface.callbacks.has_key(pokerinterface.INTERFACE_POST_BLIND):
            message = "Pay the ante (%d) ?" % amount
            interface.blindMessage(message, "no")
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
        self.factory.interface.blindHide()
        self.factory.interface.clearCallbacks(pokerinterface.INTERFACE_POST_BLIND)
        return response == "yes"

    def hideBlind(self):
        interface = self.factory.interface
        if interface and interface.callbacks.has_key(pokerinterface.INTERFACE_POST_BLIND):
            interface.blindHide()
            interface.clearCallbacks(pokerinterface.INTERFACE_POST_BLIND)
                    
    def payBlind(self, game, amount, dead, state):
        interface = self.factory.interface
        if interface and not interface.callbacks.has_key(pokerinterface.INTERFACE_POST_BLIND):
            message = "Pay the "
            if dead > 0:
                message += "big blind (%d) + dead (%d)" % ( amount, dead )
            elif state == "big" or state == "late":
                message += "big blind (%d)" % amount
            else:
                message += "small blind (%d)" % amount
            message += "?"
            wait_blind = ( state == "late" or state == "big_and_dead" ) and "yes" or "no"
            interface.blindMessage(message, wait_blind)
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
        self.factory.interface.blindHide()
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
                if self.factory.verbose:
                    print "connection ready, ask for password"
                self.changeState(LOGIN)
            else:
                if self.factory.verbose:
                    print "connection not established, will ask password later"

    def chatFormatMessage(self, message):
        config = self.factory.chat_config
        #
        # This is crude but is only meant to cope with a server that
        # would insist on sending more chars than the client wants.
        #
        message = message[:config['max_chars']] 
        format = DumbWriter(StringIO(), config['line_length'])
        format.send_flowing_data(message)
        return format.file.getvalue()
        
    def chatHide(self):
        interface = self.factory.interface
        if interface:
            interface.chatHide()
            
    def chatHistory(self, yesno):
        game_id = self.protocol.getCurrentGameId()
        game = self.factory.getGame(game_id)        
        self.render(game, PacketPokerChatHistory(show = yesno))

    def chatLine(self, line):
        serial = self.protocol.getSerial()
        game_id = self.protocol.getCurrentGameId()
        self.protocol.sendPacket(PacketPokerChat(game_id = game_id,
                                                 serial = serial,
                                                 message = line))
    
    def interfaceCallbackLogin(self, ok_or_cancel, name, password, remember):
        if ok_or_cancel != "ok":
            self.changeState(LOGIN_DONE, False)
            return
        
        interface = self.factory.interface
        (ok, reason) = self.protocol.user.checkNameAndPassword(name, password)
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
        if self.factory.verbose:
            print message

    def handleCashier(self, yesno = "yes"):
        if yesno == "yes":
            self.changeState(CASHIER)
        else:
            self.changeState(LOBBY)

    def showCashier(self):
        interface = self.factory.interface
        if interface:
            interface.showCashier()

    def hideCashier(self):
        interface = self.factory.interface
        if interface:
            interface.hideCashier()

    def updateCashier(self, packet):
        print "updateCashier"
        interface = self.factory.interface
        if interface:
            interface.updateCashier(self.protocol.getName(),
                                    packet.email,
                                    "%s\n%s %s %s\n%s" % ( packet.addr_street, packet.addr_zip, packet.addr_town, packet.addr_state, packet.addr_country ),
                                    str(packet.play_money),
                                    str(packet.play_money_in_game),
                                    str(packet.play_money + packet.play_money_in_game),
                                    str(packet.real_money) + "$",
                                    str(packet.real_money_in_game) + "$",
                                    str(packet.real_money + packet.real_money_in_game) + "$",
                                    )

    def handleSerial(self, packet):
        if self.factory.verbose:
            print "handleSerial: we now have serial %d" % packet.serial
        self.protocol.user.serial = packet.serial
        display = self.factory.display
        display.render(packet)

    def restoreGameSate(self, game):
        serial = self.protocol.getSerial()
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
            self.render(game, packet)

        elif packet.type == PACKET_POKER_USER_INFO:
            self.changeState(USER_INFO_DONE)

        elif packet.type == PACKET_POKER_STREAM_MODE:
            self.stream_mode = True
            self.render(game, packet)
            self.restoreGameSate(game)
            self.handleInteractors(game)
            self.interactorsSyncDisplay(game.id)
            
        elif packet.type == PACKET_POKER_BATCH_MODE:
            self.stream_mode = False
            self.render(game, packet)

        elif packet.type == PACKET_POKER_BET_LIMIT:
            self.bet_step = packet.step
            self.render(game, packet)
            
        elif packet.type == PACKET_POKER_HAND_LIST:
            if self.state == HAND_LIST:
                self.showHands(packet.hands, packet.total)
            else:
                print "handleGame: unexpected state for POKER_HAND_LIST " + self.state

        elif packet.type == PACKET_POKER_HAND_HISTORY:
            if self.state == HAND_LIST:
                self.showHandHistory(packet.game_id, eval(packet.history), eval(packet.serial2name))
            else:
                print "handleGame: unexpected state for POKER_HAND_HISTORY " + self.state

        elif packet.type == PACKET_BOOTSTRAP:
            self.bootstrap()
            
        elif packet.type == PACKET_PROTOCOL_ERROR:
            self.showMessage(packet.message, lambda: self.factory.confirmQuit(True))
            self.factory.reconnect = False
            
        elif packet.type == PACKET_POKER_TABLE_LIST:
            if self.state == LOBBY:
                self.updateLobby(packet)
            elif self.state == SEARCHING_MY:
                self.choseTable(packet.packets)
            else:
                print "handleGame: unexpected state for TABLE_LIST: " + self.state

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
                print "ERROR: unexpected error"
            
        elif packet.type == PACKET_POKER_TOURNEY_PLAYERS_LIST:
            self.updateTournamentsPlayersList(packet)
        
        elif packet.type == PACKET_POKER_TOURNEY_LIST:
            self.updateTournaments(packet)
                
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
                self.render(game, packet)
                self.factory.interface.chatShow()
            self.changeState(JOINING_DONE)

        elif packet.type == PACKET_POKER_CURRENT_GAMES:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_TABLE_QUIT:
            self.deleteGame(game.id)
            self.protocol.setCurrentGameId(None)
            
        elif packet.type == PACKET_AUTH_REQUEST:
            if self.factory.interface:
                self.changeState(LOGIN)
            else:
                self.protocol.sendPacket(PacketLogin(name = self.factory.name,
                                                     password = self.factory.password))

        elif packet.type == PACKET_AUTH_EXPIRES:
            print "server timeout waiting for our login packet"
            self.showMessage("Server timed out waiting for login", lambda: self.changeState(LOGIN_DONE, False))

        elif packet.type == PACKET_AUTH_REFUSED:
            self.showMessage("Invalid login or passwd", lambda: self.changeState(LOGIN_DONE, False))

        elif packet.type == PACKET_AUTH_OK:
            if self.factory.verbose:
                print "login accepted"

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
            self.render(game, packet)

        elif packet.type == PACKET_POKER_CANCELED:
            self.changeState(CANCELED)

        elif packet.type == PACKET_POKER_PLAYER_INFO:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_PLAYER_ARRIVE:
            if packet.serial == self.protocol.getSerial():
                packet.url = self.factory.getUrl()
                packet.outfit = self.factory.getOutfit()
                self.sitActionsUpdate()
            else:
                ( packet.url, packet.outfit ) = self.factory.getSkin().interpret(packet.url, packet.outfit)
            self.render(game, packet)

            if packet.serial == self.protocol.getSerial():
                self.sitActionsShow()

        elif ( packet.type == PACKET_POKER_PLAYER_LEAVE or
               packet.type == PACKET_POKER_TABLE_MOVE ) :
            self.render(game, PacketPokerPlayerLeave(game_id = packet.game_id,
                                                     serial = packet.serial,
                                                     seat = packet.seat))
            if packet.serial == self.protocol.getSerial():
                self.changeState(LEAVING_DONE)

        elif packet.type == PACKET_POKER_END_ROUND:
            self.render(game, packet)
            self.cancelAllInteractors(game.id)
            self.handleInteractors(game)
            self.delay(game, "end_round")

        elif packet.type == PACKET_POKER_END_ROUND_LAST:
            self.render(game, packet)
            self.handleInteractors(game)
            self.delay(game, "end_round_last")

        elif packet.type == PACKET_POKER_BEGIN_ROUND:
            self.render(game, packet)
            self.handleInteractors(game)
            self.delay(game, "begin_round")
            
        elif packet.type == PACKET_POKER_SELF_IN_POSITION:
            self.render(game, packet)
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_SELF_LOST_POSITION:
            self.render(game, packet)
            self.handleInteractors(game)

        elif packet.type == PACKET_POKER_HIGHEST_BET_INCREASE:
            self.render(game, packet)
            self.cancelAllInteractors(game.id)
            self.handleInteractors(game)
               
        elif packet.type == PACKET_POKER_POSITION:
            self.render(game, packet)
            if packet.serial != 0:
                self.delay(game, "position")

        elif packet.type == PACKET_POKER_CHAT:
            interface = self.factory.interface
            if interface:
                interface.chatHistory(packet.message)
            # duplicate PacketPokerChat
            # in order to preseve integrity of original packet
            message = packet.message
            #self.chatFormatMessage(packet.message)
            #message = PokerChat.filterChatTrigger(message)
            chatPacket = PacketPokerChat(game_id = packet.game_id,
                                         serial = packet.serial,
                                         message = message)
            if chatPacket.message.strip() != "":
                self.render(game, chatPacket)

        elif packet.type == PACKET_POKER_BLIND_REQUEST:
            if ( game.getSerialInPosition() == self.protocol.getSerial() ):
                self.changeState(PAY_BLIND_ANTE, 'blind', game, packet.amount, packet.dead, packet.state)
                
        elif packet.type == PACKET_POKER_ANTE_REQUEST:
            if ( game.getSerialInPosition() == self.protocol.getSerial() ):
                self.changeState(PAY_BLIND_ANTE, 'ante', game, packet.amount)
                
        elif packet.type == PACKET_POKER_SEAT:
            if packet.seat == 255:
                self.showMessage("This seat is busy", None)
                self.changeState(IDLE)
            else:
                if not game.isTournament():
                    self.changeState(USER_INFO, BUY_IN, game)
            
        elif packet.type == PACKET_POKER_SEATS:
            self.render(game, packet)
            
        elif packet.type == PACKET_POKER_PLAYER_CARDS:
            if game.variant == "7stud":
                packet.visibles = "best"
            else:
                packet.visibles = "hole"
            self.render(game, packet)

        elif packet.type == PACKET_POKER_BOARD_CARDS:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_DEALER:
            self.render(game, packet)
            self.delay(game,"dealer")
            
        elif packet.type == PACKET_POKER_SIT_OUT:
            self.render(game, packet)
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()
                self.changeState(SIT_OUT)

        elif packet.type == PACKET_POKER_AUTO_FOLD:
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()

        elif packet.type == PACKET_POKER_SIT:
            self.render(game, packet)
            if packet.serial == self.protocol.getSerial():
                self.sitActionsUpdate()
            
        elif packet.type == PACKET_POKER_TIMEOUT_WARNING:
            self.render(game, packet)
            
        elif packet.type == PACKET_POKER_TIMEOUT_NOTICE:
            self.render(game, packet)
            self.changeState(CANCELED)
            
        elif packet.type == PACKET_POKER_WAIT_FOR:
            if self.factory.interface:
                if packet.serial == self.protocol.getSerial():
                    self.factory.interface.sitActionsSitOut("yes", "wait for %s blind" % packet.reason)
            
        elif packet.type == PACKET_POKER_IN_GAME:
            self.render(game, packet)
            
        elif packet.type == PACKET_POKER_WIN:
            self.render(game, packet)
            self.delay(game, "showdown")
            
        elif packet.type == PACKET_POKER_PLAYER_CHIPS:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_POT_CHIPS:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_FOLD:
            self.handleFold(game, packet)
            self.render(game, packet)
            
        elif packet.type == PACKET_POKER_CALL:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_RAISE:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_CHECK:
            self.render(game, packet)

        elif packet.type == PACKET_POKER_BLIND:
            self.render(game, packet)
            if packet.serial == self.protocol.getSerial():
                self.changeState(PAY_BLIND_ANTE_DONE)

        elif packet.type == PACKET_POKER_ANTE:
            self.render(game, packet)
            if packet.serial == self.protocol.getSerial():
                self.changeState(PAY_BLIND_ANTE_DONE)

        elif packet.type == PACKET_POKER_STATE:
            pass

    def sitActionsShow(self):
        interface = self.factory.interface
        if interface:
            interface.sitActionsShow()
            if not interface.callbacks.has_key(pokerinterface.INTERFACE_AUTO_BLIND):
                interface.registerHandler(pokerinterface.INTERFACE_AUTO_BLIND, self.autoBlind)
                interface.registerHandler(pokerinterface.INTERFACE_SIT_OUT, self.sitOut)

    def sitActionsHide(self):
        interface = self.factory.interface
        if interface:
            interface.sitActionsHide()

    def sitActionsUpdate(self):
        interface = self.factory.interface
        if interface:
            game = self.factory.getGame(self.protocol.getCurrentGameId())
            player = game.getPlayer(self.protocol.getSerial())

            if player.wait_for:
                interface.sitActionsSitOut("yes", "wait for %s blind" % player.wait_for)
            elif player.auto:
                interface.sitActionsSitOut("yes", "sit out")
            elif player.sit_out:
                interface.sitActionsSitOut("yes", "sit out")
            else:
                interface.sitActionsSitOut("no", "sit out next hand")

            if game.isTournament():
                interface.sitActionsAuto(None)
            elif player.auto_blind_ante:
                interface.sitActionsAuto("yes")
            else:
                interface.sitActionsAuto("no")
                
    def requestBuyIn(self, game):
        player = game.getPlayer(self.protocol.getSerial())

        min_amount = max(0, game.buyIn() - player.money.toint())
        max_amount = game.maxBuyIn() - player.money.toint()

        if max_amount <= 0:
            self.showMessage("You can't bring more money\nto the table", None)
            return False

        if player.isBuyInPayed():
            if self.protocol.play_money <= 0:
                self.showMessage("You have no money left", None)
                return False

            legend = "How much do you want to rebuy ?"
        else:
            if min_amount > self.protocol.play_money:
                self.showMessage("You don't have enough money to\nparticipate in the game", None)
                return False

            legend = "Which amount do you want to bring at the table ?"
        
        interface = self.factory.interface

        if max_amount >= self.protocol.play_money:
            label = "All your bankroll"
        else:
            label = "Maximum buy in"
        interface.buyInParams(min_amount, min(max_amount, self.protocol.play_money), legend, label)
        interface.buyInShow()
        if player.isBuyInPayed():
            callback = lambda value: self.rebuy(game, value)
        else:
            callback = lambda value: self.buyIn(game, value)
        interface.registerHandler(pokerinterface.INTERFACE_BUY_IN, callback)
        return True
        
    def buyIn(self, game, value):
        interface = self.factory.interface
        interface.clearCallbacks(pokerinterface.INTERFACE_BUY_IN)
        self.protocol.sendPacket(PacketPokerBuyIn(serial = self.protocol.getSerial(),
                                                  game_id = game.id,
                                                  amount = int(float(value))))
        self.protocol.sendPacket(PacketPokerSit(serial = self.protocol.getSerial(),
                                                game_id = game.id))
        self.changeState(BUY_IN_DONE)

    def rebuy(self, game, value):
        interface = self.factory.interface
        interface.clearCallbacks(pokerinterface.INTERFACE_BUY_IN)
        self.protocol.sendPacket(PacketPokerRebuy(serial = self.protocol.getSerial(),
                                                  game_id = game.id,
                                                  amount = int(float(value))))
        self.changeState(REBUY_DONE)

    def hold(self, delay, id = None):
        if delay > 0 and not self.stream_mode:
            return
        self.protocol.hold(delay, id)
        
    def delay(self, game, event):

        if self.state != IDLE:
            return
        
        if ( game.id == self.replayGameId and
             self.replayStepping ):
            self.hold(120, game.id)
            return

        self.hold(self.factory.delays.get(event, 1), game.id)

    def handleFold(self, game, packet):
        pass
#        if packet.serial == self.protocol.getSerial():
#            self.scheduledAction[game.id] = None

    def handleInPosition(self, game, packets, index, value):
        if index == 2:
            chips = PokerChips(game.chips_values, value)
            packets[index].amount = chips.chips
        self.protocol.sendPacket(packets[index])
        
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
                    interactor.cancel()
                    interactor.disable()
                interactor.update()
                return enabled

            isInPosition = game.getSerialInPosition() == serial
            player = game.getPlayer(serial)
            updateInteractor(interactors["check"], game.canCheck(serial), isInPosition, None)
            updateInteractor(interactors["fold"], True, isInPosition, None)
            updateInteractor(interactors["shadowstacks"], game.canCall(serial) or game.canRaise(serial), isInPosition, [ player.money.toint(), game.highestBetNotFold() ])
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
                self.render(game, PacketPokerDisplayNode(name = interactor.name, state = "default", style = interactor.getDefault(), selection = interactor.selected_value))
                self.render(game, PacketPokerDisplayNode(name = interactor.name, state = "clicked", style = interactor.getClicked(), selection = interactor.selected_value))
        
    def interactorDisplayShadowStacks(self, interactor):
        if interactor.game_id == self.protocol.getCurrentGameId():
            game = self.factory.getGame(interactor.game_id)
            if game and interactor.hasChanged():
                print "interactorDisplayShadowStacks"
                self.render(game, PacketPokerDisplayNode(name = interactor.name, state = "default", style = interactor.getDefault(), selection = interactor.selected_value))

    def interactorsSyncDisplay(self, game_id):
        print "interactorsSyncDisplay"
        
        game = self.factory.getGame(game_id)
        interactor_set = self.getOrCreateInteractorSet(game_id)
        interactors = interactor_set.items
        for (name, interactor) in interactors.iteritems():
            print "interactor:" + interactor.name + " default=" + interactor.getDefault() + " clicked=" + interactor.getClicked()
            self.render(game, PacketPokerDisplayNode(name = interactor.name, state = "default", style = interactor.getDefault(), selection = interactor.selected_value))
            if interactor.name != "shadowstacks":
                self.render(game, PacketPokerDisplayNode(name = interactor.name, state = "clicked", style = interactor.getClicked(), selection = interactor.selected_value))
                
    def interactorAction(self, interactor):
        self.cancelAllInteractorButThisOne(interactor)
        game = self.factory.getGame(interactor.game_id)
        packet = interactor.getSelectedValue()
        if packet.type == PACKET_POKER_RAISE:
            value = packet.amount
            chips = PokerChips(game.chips_values, value)
            packet.amount = chips.chips
        self.protocol.sendPacket(packet)

    def interactorSelectedCallback(self, interactor):
        self.cancelAllInteractorButThisOne(interactor)

    def interactorSelected(self, packet):
        if self.protocol.getCurrentGameId() == packet.game_id:
            if packet.type == PACKET_POKER_CALL:
                name = "shadowstacks"
            elif packet.type == PACKET_POKER_RAISE:
                name = "shadowstacks"
            elif packet.type == PACKET_POKER_FOLD:
                name = "fold"
            elif packet.type == PACKET_POKER_CHECK:
                name = "check"
            else:
                print "*CRITICAL* unexpected event %s " % event
                return

#           interactor = self.interactors[name]
#           interactor.select(packet)
#           interactor.update()

            interactor = self.getOrCreateInteractorSet(packet.game_id).items[name]
            interactor.select(packet)
            interactor.update()
            
    def render(self, game, packet):
        display = self.factory.display
        display.render(packet)
        
    def scheduleAction(self, packet):
        game = self.factory.packet2game(packet)
        if game.isRunning():
            action = False
            if packet.type == PACKET_POKER_RAISE:
                amount = PokerChips(game.chips_values,
                                    packet.amount[0] * self.bet_step)
                action = PacketPokerRaise(game_id = game.id,
                                          serial = self.protocol.getSerial(),
                                          amount = amount.chips)
            elif packet.action == "raise":
                amount = PokerChips(game.chips_values)
                action = PacketPokerRaise(game_id = game.id,
                                          serial = self.protocol.getSerial(),
                                          amount = amount.chips)
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
            return

        game_id = self.protocol.getCurrentGameId()
        game = self.factory.getGame(game_id)
        serial = self.protocol.getSerial()

        self.changeState(LEAVING, game, serial)

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
        elif self.state == IDLE:
            pass
        else:
            status = False
        return status

    def handleMenu(self, name, value):
        settings = self.factory.settings
        if name == "login":
            self.changeState(LOGIN)
        elif name == "cashier":
            self.changeState(CASHIER)
        elif name == "outfits":
            self.changeState(OUTFIT)
        elif name == "hand_history":
            self.changeState(HAND_LIST)
        elif name == "quit":
            self.quit()
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
            self.queryRestart("Screen resolution changed")
        elif name == "display":
            settings.headerSet("/settings/@display2d", value == "2d" and "yes" or "no")
            settings.headerSet("/settings/@display3d", value == "3d" and "yes" or "no")
            settings.save()
            self.queryRestart("Display changed to " + value)
        elif name == "fullscreen":
            settings.headerSet("/settings/screen/@fullscreen", value)
            settings.save()
            self.queryRestart("Screen resolution changed")
        elif name == "graphics":
            settings.headerSet("/settings/shadow", value)
            settings.headerSet("/settings/vprogram", value)
            settings.save()
            self.queryRestart("Graphics quality changed")
        elif name == "sound":
            settings.headerSet("/settings/sound", value)
            settings.save()
            self.queryRestart("Sound effects changed")
        elif name == "auto_post":
            settings.headerSet("/settings/auto_post", value)
            settings.save()
        elif name == "remember_me":
            settings.headerSet("/settings/remember", value)
            settings.save()
        elif name == "muck":
            settings.headerSet("/settings/muck", value)
            settings.save()
        else:
            print "*CRITICAL* handleMenu unknown name %s" % name

    def queryRestart(self, message):
        interface = self.factory.interface
        interface.yesnoBox(message + "\n" +
                           "The game must be restarted for this change to take effect\n" +
                           "Do you want to restart the game now ?")
        interface.registerHandler(pokerinterface.INTERFACE_YESNO, lambda status: status and self.factory.restart())
        
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
        if self.factory.verbose > 2: print "handleLobby: " + str(args)
        (action, value) = args
        if action == "details":
            game_id = int(value)
            self.state_lobby["current"] = game_id
            self.protocol.sendPacket(PacketPokerTableRequestPlayersList(game_id = game_id))

        elif action == "join":
            self.protocol.publishDelay(2)
            self.connectTable(int(value))
        elif action == "refresh":
            if value == "play":
                self.state_lobby['real_money'] = 'n'
            elif value == "real":
                self.state_lobby['real_money'] = 'y'
            elif value == "all":
                self.state_lobby['real_money'] = ''
            else:
                self.state_lobby['type'] = value
            self.queryLobby()
        elif action == "quit":
            if value == "cashier":
                self.changeState(CASHIER)
            else:
                self.changeState(TOURNAMENTS, value)
        else:
            print "ERROR: handleLobby: unknown action " + action

    def queryLobby(self):
        if self.state == LOBBY:
            criterion = self.state_lobby['real_money'] + "\t" + self.state_lobby['type']
            self.protocol.sendPacket(PacketPokerTableSelect(string = criterion))
            timer = self.state_lobby.get('timer', None)
            if not timer or not timer.active():
                self.state_lobby['timer'] = reactor.callLater(30, self.queryLobby)
        
    def saveLobbyState(self):
        settings = self.factory.settings
        state = self.state_lobby
        settings.headerSet("/settings/lobby/@real_money", state['real_money'])
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
        tables_map = dict(zip(map(lambda tournament: tournament.id, tables), tables))
        self.state_lobby["tables"] = tables_map
        game_id = self.state_lobby["current"]
        if not tables_map.has_key(game_id):
            game_id = 0
        if interface:
            interface.updateLobby(packet.players, packet.tables, game_id, self.factory.translateFile2Name, packet.packets)

    def showLobby(self, type = None):
        interface = self.factory.interface
        if interface:
            type = type or self.state_lobby['type']
            interface.showLobby(type, self.state_lobby['real_money'])
        
    def hideLobby(self):
        interface = self.factory.interface
        if interface:
            interface.hideLobby()
        self.saveLobbyState()

    def handleTournaments(self, args):
        if self.factory.verbose > 2: print "handleTournaments: " + str(args)
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
            if value == "play":
                self.state_tournaments['real_money'] = 'n'
            elif value == "real":
                self.state_tournaments['real_money'] = 'y'
            elif value == "all":
                self.state_tournaments['real_money'] = ''
            else:
                self.state_tournaments['type'] = value
            self.queryTournaments()
        elif action == "quit":
            if value == "cashier":
                self.changeState(CASHIER)
            else:
                self.changeState(LOBBY, value)
        else:
            print "ERROR: handleTournaments: unknown action " + action

    def queryTournaments(self):
        if self.state == TOURNAMENTS:
            criterion = self.state_tournaments['real_money'] + "\t" + self.state_tournaments['type']
            self.protocol.sendPacket(PacketPokerTourneySelect(string = criterion))
            timer = self.state_tournaments.get('timer', None)
            if not timer or not timer.active():
                self.state_tournaments['timer'] = reactor.callLater(30, self.queryTournaments)
        
    def saveTournamentsState(self):
        settings = self.factory.settings
        state = self.state_tournaments
        settings.headerSet("/settings/tournaments/@real_money", state['real_money'])
        settings.headerSet("/settings/tournaments/@type", state['type'])
        settings.headerSet("/settings/tournaments/@sort", state['sort'])
        settings.save()
        
    def updateTournamentsPlayersList(self, packet):
        if self.state != TOURNAMENTS:
            return
        interface = self.factory.interface
        if not interface:
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
            type = type or self.state_tournaments['type']
            interface.showTournaments(type, self.state_tournaments['real_money'])
        
    def hideTournaments(self):
        interface = self.factory.interface
        if interface:
            interface.hideTournaments()
        self.saveTournamentsState()
        
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
                print "selectHand: ignored because not in HAND_LIST state"
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
            self.changeState(LOBBY)
        else:
            print "CRITICAL: selectHands unexpected action " + action
    
    def showHands(self, hands, total):
        interface = self.factory.interface
        if interface:
            state = self.state_hands
            state["total"] = total
            if hands:
                interface.showHands(hands, state["start"], state["count"], state["total"])
            else:
                self.showMessage("Your hand history is empty", None)
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
        game_ids = self.factory.games.keys()
        current = game_ids.index(self.protocol.getCurrentGameId())
        game_ids = game_ids[current:] + game_ids[:current]
        print "rotateTable: %d => %d" % ( self.protocol.getCurrentGameId(), game_ids[1])
        self.connectTable(game_ids[1])
        
    def connectTable(self, game_id):
        serial = self.protocol.getSerial()
        current_game_id = self.protocol.getCurrentGameId()
        done = False
        if current_game_id != game_id:
            current_game = self.factory.getGame(current_game_id)
            if current_game and not current_game.isSeated(serial):
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
        self.deleteInteractorSet(game_id)

    def sendPacketSitOut(self, packet):
        self.sendPacket(packet)
        self.factory.interface.sitActionsSitOut("yes", "sit out next hand")
        
    def sendPacketSit(self, packet):
        self.sendPacket(packet)
        self.factory.interface.sitActionsSitOut("no", "sit out")
        
    def sendPacket(self, packet):
        print "render sendPacket %s" % packet
        return self.protocol.sendPacket(packet)
        
    def getSeat(self, packet):
        print "getSeat %s" % packet
        self.changeState(SEATING, packet)

    def bootstrap(self):
        if self.factory.remember:
            if self.factory.interface:
                if self.factory.verbose:
                    print "interface ready, ask for password"
                self.changeState(LOGIN)
            else:
                if self.factory.verbose:
                    print "interface not ready, will ask password later"
        else:
            self.changeState(LOBBY)
        self.factory.display.setRenderer(self)

    def reload(self):
        self.factory.reload()

    def changeState(self, state, *args, **kwargs):
        if self.state == state:
            return

        if not self.stream_mode:
            return
        
        if self.factory.verbose > 2: print "changeState %s => %s (args = %s, kwargs = %s)" % ( self.state, state, str(args), str(kwargs) )
        
        if state == LOGOUT:
            if ( self.state == IDLE or self.state == SEARCHING ) and self.protocol.user.isLogged():
                self.deleteGames()
                self.protocol.logout()
                self.changeState(SEARCHING, "all")

        elif state == LOBBY and ( self.state2hide() or self.state == SEARCHING_MY ):
            self.state = state
            self.showLobby(*args)
            self.queryLobby()

        elif state == SEARCHING_MY and ( self.state2hide() or self.state == LOGIN ):
            self.protocol.sendPacket(PacketPokerTableSelect(string = "my"))
            self.state = state

        elif state == PAY_BLIND_ANTE:
            if not self.state2hide():
                if ( self.state == USER_INFO or
                     self.state == REBUY ):
                    self.factory.interface.buyInHide()
                else:
                    print "ERROR unexpected state " + self.state
                    return
            what = args[0]
            args = args[1:]
            if what == 'ante':
                self.payAnte(*args)
            elif what == 'blind':
                self.payBlind(*args)
            else:
                print "ERROR unknow what " + what
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
                print "ERROR unknow what " + what
            self.state = status and state or IDLE

        elif state == PAY_BLIND_ANTE_DONE:
            if self.state == PAY_BLIND_ANTE_SEND:
                self.hideBlind()
            
            self.changeState(IDLE)

        elif state == LOGIN:
            if self.protocol.user.isLogged():
                self.showMessage("Already logged in", None)
            else:
                if kwargs.has_key("restore_state"):
                    self.state_login = kwargs
                else:
                    self.state_login = None
                    self.state2hide()
                self.requestLogin()
                self.state = state

        elif state == LOGIN_DONE:
            self.factory.interface.hideLogin()
            success = args[0]
            if success and self.state_login:
                self.state = self.state_login['done_state']
                args = self.state_login.get('restore_args', ())
                self.changeState(self.state_login['restore_state'], *args)
            elif success and self.state == JOINING_DONE:
                self.state = IDLE
            elif success:
                self.changeState(LOBBY)
            else:
                self.state = IDLE

        elif state == CASHIER and self.state2hide():
            if self.protocol.user.isLogged():
                self.protocol.sendPacket(PacketPokerGetPersonalInfo(serial = self.protocol.getSerial()))
                self.state = state
            else:
                self.changeState(LOGIN,
                                 done_state = IDLE,
                                 restore_state = CASHIER)

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
            self.factory.interface.buyInHide()
            self.changeState(IDLE)
            
        elif state == REBUY and self.state == USER_INFO:
            if self.requestBuyIn(args[0]):
                self.state = state
            else:
                self.state = IDLE
            
        elif state == REBUY_DONE:
            self.factory.interface.buyInHide()
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
                self.changeState(LOGIN,
                                 done_state = TOURNAMENTS,
                                 restore_state = TOURNAMENTS_REGISTER,
                                 restore_args = args)
            
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

        elif state == SEATING and self.state2hide():
            if self.protocol.user.isLogged():
                packet = args[0]
                packet.serial = self.protocol.getSerial()
                self.state_buy_in = self.factory.getGame(packet.game_id)
                self.protocol.sendPacket(packet)
                if self.factory.settings.headerGet("/settings/auto_post") == "yes":
                    self.protocol.sendPacket(PacketPokerAutoBlindAnte(game_id = packet.game_id,
                                                                      serial = packet.serial))
                self.state = state
            else:
                self.changeState(LOGIN,
                                 done_state = IDLE,
                                 restore_state = SEATING,
                                 restore_args = args)

        elif state == LEAVING_DONE and self.state == LEAVING:
            self.hideBlind()
            self.factory.interface.buyInHide()
            self.sitActionsHide()
            self.state = IDLE
            self.changeState(LOBBY)
            
        elif state == LEAVING_CANCEL:
            self.state = IDLE
            
        elif state == JOINING_DONE:
            self.hideBlind()
            self.factory.interface.buyInHide()
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
            else:
                self.changeState(LEAVING_DONE)

        elif state == CANCELED:
            self.hideBlind()
            self.state = IDLE

        elif state == SIT_OUT:
            if self.state == PAY_BLIND_ANTE:
                self.hideBlind()
                self.state = IDLE

        elif state == OUTFIT:
            if self.isSeated():
                self.showMessage("You must leave the table to change your outfit", None)
            else:
                if self.state2hide():
                    self.factory.getSkin().showOutfitEditor(self.selectOutfit)
                    self.factory.interface.hideMenu()
                    self.state = state

        elif state == OUTFIT_DONE and self.state == OUTFIT:
            self.factory.getSkin().hideOutfitEditor()
            self.factory.interface.showMenu()
            self.state = IDLE
            
        elif state == HAND_LIST:
            if self.protocol.user.isLogged():
                if self.state2hide():
                    self.state = state
                    self.state_hands = { "start": 0, "count": 100 }
                    self.queryHands()
            else:
                self.changeState(LOGIN,
                                 done_state = IDLE,
                                 restore_state = HAND_LIST)

        elif state == IDLE:
            self.state2hide()
            self.state = state
