#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2004, 2005 Mekensleep
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
#  Loic Dachary <loic@gnu.org>
#  Henry Precheur <henry@precheur.org>
#
#

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")

from os.path import exists
from re import match
from types import *
from string import split, lower, join
from pprint import pprint, pformat
import time
import os
import operator
import re
from traceback import print_exc, print_stack

from MySQLdb.cursors import DictCursor

from OpenSSL import SSL

from twisted.application import internet, service, app
from twisted.internet import pollreactor
import sys
if not sys.modules.has_key('twisted.internet.reactor'):
    print "installing poll reactor"
    pollreactor.install()
else:
    print "poll reactor already installed"
from twisted.internet import protocol, reactor, defer
try:
    # twisted-2.0
    from zope.interface import Interface, implements
except ImportError:
    # twisted-1.3 forwards compatibility
    def implements(interface):
        frame = sys._getframe(1)
        locals = frame.f_locals

        # Try to make sure we were called from a class def
        if (locals is frame.f_globals) or ('__module__' not in locals):
            raise TypeError(" can be used only from a class definition.")

        if '__implements__' in locals:
            raise TypeError(" can be used only once in a class definition.")

        locals['__implements__'] = interface

    from twisted.python.components import Interface

from twisted.python import components

from pokerengine.pokergame import PokerGameServer, PokerPlayer, history2messages
from pokerengine.pokercards import PokerCards
from pokerengine.pokerchips import PokerChips
from pokerengine.pokertournament import *

from pokernetwork.server import PokerServerProtocol
from pokernetwork.user import User, checkNameAndPassword, checkName, checkPassword
from pokernetwork.config import Config
from pokernetwork.pokerdatabase import PokerDatabase
from pokernetwork.pokerpackets import *
from pokernetwork.user import User

class PokerAvatar:
    """Poker server"""

    def __init__(self, service):
        self.protocol = None
        self.service = service
        self.tables = {}
        self.user = User()
        self._packets_queue = []
        self.noqueuePackets()

    def setProtocol(self, protocol):
        self.protocol = protocol
        
#    def __del__(self):
#	print "PokerAvatar instance deleted"

    def error(self, string):
        self.message("ERROR " + string)
        
    def message(self, string):
        print string
        
    def isAuthorized(self, type):
        return self.user.hasPrivilege(self.service.poker_auth.GetLevel(type))

    def login(self, info):
        (serial, name, privilege) = info
        self.user.serial = serial
        self.user.name = name
        self.user.privilege = privilege
        self.sendPacketVerbose(PacketSerial(serial = self.user.serial))
        self.service.serial2client[serial] = self
        if self.service.verbose:
            print "user %s/%d logged in" % ( self.user.name, self.user.serial )
	#
	# Send player updates if it turns out that the player was already
	# seated at a known table.
	#
	for table in self.tables.values():
	    if table.possibleObserverLoggedIn(self, serial):
                game = table.game
                self.sendPacketVerbose(PacketPokerPlayerCards(game_id = game.id,
                                                              serial = serial,
                                                              cards = game.getPlayer(serial).hand.toRawList()))
                self.sendPacketVerbose(PacketPokerPlayerSelf(game_id = game.id,
                                                             serial = serial))
                pending_blind_request = game.isBlindRequested(serial)
                pending_ante_request = game.isAnteRequested(serial)
                if pending_blind_request or pending_ante_request:
                    if pending_blind_request:
                        (amount, dead, state) = game.blindAmount(serial)
                        self.sendPacketVerbose(PacketPokerBlindRequest(game_id = game.id,
                                                                       serial = serial,
                                                                       amount = amount,
                                                                       dead = dead,
                                                                       state = state))
                    if pending_ante_request:
                        self.sendPacketVerbose(PacketPokerAnteRequest(game_id = game.id,
                                                                      serial = serial,
                                                                      amount = game.ante_info["value"]))

    def logout(self):
        if self.user.serial:
            del self.service.serial2client[self.user.serial]
            self.user.logout()
        
    def auth(self, packet):
        status = checkNameAndPassword(packet.name, packet.password)
        if status[0]:
            ( info, reason ) = self.service.auth(packet.name, packet.password)
        else:
            print "PokerAvatar::auth: failure " + str(status)
            info = False
        if info:
            self.sendPacketVerbose(PacketAuthOk())
            self.login(info)
        else:
            self.sendPacketVerbose(PacketAuthRefused(string = reason))

    def getSerial(self):
        return self.user.serial

    def getName(self):
        return self.user.name

    def getUrl(self):
        return self.user.url

    def getOutfit(self):
        return self.user.outfit
    
    def isLogged(self):
        return self.user.isLogged()

    def queuePackets(self):
        self._queue_packets = True

    def noqueuePackets(self):
        self._queue_packets = False

    def resetPacketsQueue(self):
        queue = self._packets_queue
        self._packets_queue = []
        return queue
    
    def sendPacket(self, packet):
        if self._queue_packets:
            self._packets_queue.append(packet)
        else:
            self.protocol.sendPacket(packet)

    def sendPacketVerbose(self, packet):
        if self.service.verbose > 1:
            print "sendPacket: %s" % str(packet)
        self.sendPacket(packet)
        
    def packet2table(self, packet):
        if hasattr(packet, "game_id") and self.tables.has_key(packet.game_id):
            return self.tables[packet.game_id]
        else:
            return False

    def handlePacket(self, packet):
        self.queuePackets()
        self.handlePacketLogic(packet)
        self.noqueuePackets()
        return self.resetPacketsQueue()
        
    def handlePacketLogic(self, packet):
        if self.service.verbose > 2: print "handleConnection: " + str(packet) 
        if not self.isAuthorized(packet.type):
            self.sendPacketVerbose(PacketAuthRequest())
            return

        if packet.type == PACKET_LOGIN:
            self.auth(packet)
            return

        if packet.type == PACKET_POKER_GET_USER_INFO:
            if self.getSerial() == packet.serial:
                self.getUserInfo(packet.serial)
            else:
                print "attempt to get user info for user %d by user %d" % ( packet.serial, self.getSerial() )
            return

        elif packet.type == PACKET_POKER_GET_PERSONAL_INFO:
            if self.getSerial() == packet.serial:
                self.getPersonalInfo(packet.serial)
            else:
                print "attempt to get personal info for user %d by user %d" % ( packet.serial, self.getSerial() )
            return

        elif packet.type == PACKET_POKER_PLAYER_INFO:
            if self.getSerial() == packet.serial:
                if self.setPlayerInfo(packet):
                    self.sendPacketVerbose(packet)
                else:
                    self.sendPacketVerbose(PacketError(other_type = PACKET_POKER_PLAYER_INFO,
                                                       code = PACKET_POKER_PLAYER_INFO,
                                                       message = "Failed to save set player information"))
            else:
                print "attempt to set player info for player %d by player %d" % ( packet.serial, self.getSerial() )
            return
                
        elif packet.type == PACKET_POKER_PERSONAL_INFO:
            if self.getSerial() == packet.serial:
                self.setPersonalInfo(packet)
            else:
                print "attempt to set player info for player %d by player %d" % ( packet.serial, self.getSerial() )
            return

        elif ( packet.type == PACKET_POKER_SET_ACCOUNT or
               packet.type == PACKET_POKER_CREATE_ACCOUNT ):
            if self.getSerial() != packet.serial:
                packet.serial = 0
            self.sendPacketVerbose(self.service.setAccount(packet))
            return

        if packet.type == PACKET_POKER_TOURNEY_SELECT:
            ( players, tourneys ) = self.service.tourneyStats()
            tourneys = PacketPokerTourneyList(players = players,
                                              tourneys = tourneys)
            for tourney in self.service.tourneySelect(packet.string):
                tourneys.packets.append(PacketPokerTourney(**tourney))
            self.sendPacketVerbose(tourneys)
            return
        
        elif packet.type == PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST:
            self.sendPacketVerbose(self.service.tourneyPlayersList(packet.game_id))
            return

        elif packet.type == PACKET_POKER_TOURNEY_REGISTER:
            if self.getSerial() == packet.serial:
                self.service.tourneyRegister(packet)
            else:
                print "attempt to register in tournament %d for player %d by player %d" % ( packet.game_id, packet.serial, self.getSerial() )
            return
            
        elif packet.type == PACKET_POKER_TOURNEY_UNREGISTER:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.service.tourneyUnregister(packet))
            else:
                print "attempt to unregister from tournament %d for player %d by player %d" % ( packet.game_id, packet.serial, self.getSerial() )
            return
            
        elif packet.type == PACKET_POKER_TABLE_REQUEST_PLAYERS_LIST:
            self.listPlayers(packet)
            return

        elif packet.type == PACKET_POKER_TABLE_SELECT:
            self.listTables(packet)
            return

        elif packet.type == PACKET_POKER_HAND_SELECT:
            self.listHands(packet, self.getSerial())
            return

        elif packet.type == PACKET_POKER_HAND_HISTORY:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.service.getHandHistory(packet.game_id, packet.serial))
            else:
                print "attempt to get history of player %d by player %d" % ( packet.serial, self.getSerial() )
            return

        elif packet.type == PACKET_POKER_HAND_SELECT_ALL:
            self.listHands(packet, None)
            return

        table = self.packet2table(packet)
            
        if table:
            game = table.game

            if packet.type == PACKET_POKER_START:
                if game.isRunning():
                    print "player %d tried to start a new game while in game " % self.getSerial()
                    self.sendPacketVerbose(PacketPokerStart(game_id = game.id))
                elif self.service.shutting_down:
                    print "server shutting down"
                elif table.owner != 0:
                    if self.getSerial() != table.owner:
                        print "player %d tried to start a new game but is not the owner of the table" % self.getSerial()
                        self.sendPacketVerbose(PacketPokerStart(game_id = game.id))
                    else:
                        hand_serial = table.beginTurn()
                else:
                    print "player %d tried to start a new game but is not the owner of the table" % self.getSerial()

            elif packet.type == PACKET_POKER_SEAT:
                if ( self.getSerial() == packet.serial or
                     self.getSerial() == table.owner ):
                    if not table.seatPlayer(self, packet.serial, packet.seat):
                        packet.seat = -1
                    else:
                        packet.seat = game.getPlayer(packet.serial).seat
                    self.getUserInfo(packet.serial)
                    self.sendPacketVerbose(packet)
                else:
                    print "attempt to get seat for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )
                
            elif packet.type == PACKET_POKER_BUY_IN:
                if self.getSerial() == packet.serial:
                    if not table.buyInPlayer(self, packet.amount):
                        self.sendPacketVerbose(PacketPokerError(game_id = game.id,
                                                                serial = packet.serial,
                                                                other_type = PACKET_POKER_BUY_IN))
                else:
                    print "attempt to bring money for player %d by player %d" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_REBUY:
                if self.getSerial() == packet.serial:
                    if not table.rebuyPlayerRequest(self, packet.amount):
                        self.sendPacketVerbose(PacketPokerError(game_id = game.id,
                                                                serial = packet.serial,
                                                                other_type = PACKET_POKER_REBUY))
                else:
                    print "attempt to rebuy for player %d by player %d" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_CHAT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.chatPlayer(self, packet.serial, packet.message[:128])
                else:
                    print "attempt chat for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_PLAYER_LEAVE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.leavePlayer(self, packet.serial)
                else:
                    print "attempt to leave for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_SIT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.sitPlayer(self, packet.serial)
                else:
                    print "attempt to sit back for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )
                
            elif packet.type == PACKET_POKER_SIT_OUT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:

                    table.sitOutPlayer(self, packet.serial)
                else:
                    print "attempt to sit out for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )
                
            elif packet.type == PACKET_POKER_AUTO_BLIND_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.autoBlindAnte(self, packet.serial, True)
                else:
                    print "attempt to set auto blind/ante for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )
                
            elif packet.type == PACKET_POKER_NOAUTO_BLIND_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.autoBlindAnte(self, packet.serial, False)
                else:
                    print "attempt to set auto blind/ante for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )
                
            elif packet.type == PACKET_POKER_BLIND:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.blind(packet.serial)
                else:
                    print "attempt to pay the blind of player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_WAIT_BIG_BLIND:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.waitBigBlind(packet.serial)
                else:
                    print "attempt to wait for big blind of player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.ante(packet.serial)
                else:
                    print "attempt to pay the ante of player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_LOOK_CARDS:
                table.broadcast(packet)
                
            elif packet.type == PACKET_POKER_FOLD:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.fold(packet.serial)
                else:
                    print "attempt to fold player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_CALL:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.call(packet.serial)
                else:
                    print "attempt to call for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_RAISE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.callNraise(packet.serial, packet.amount)
                else:
                    print "attempt to raise for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_CHECK:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.check(packet.serial)
                else:
                    print "attempt to check for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )

            elif packet.type == PACKET_POKER_TABLE_QUIT:
                table.quitPlayer(self, self.getSerial())

            elif packet.type == PACKET_POKER_HAND_REPLAY:
                table.handReplay(self, packet.serial)

            table.update()

#         if packet.type == PACKET_POKER_TABLE_GROUP:
#             serial = self.service.setTableGroup(self.getSerial(), packet.game_ids)
#             self.sendPacketVerbose(PacketPokerTableGroupSerial(serial = serial))

#         elif packet.type == PACKET_POKER_TABLE_UNGROUP:
#             serial = self.service.unsetTableGroup(self.getSerial(), packet.serial)
#             self.sendPacketVerbose(PacketPokerTableUngroup(serial = serial))
            
#         elif packet.type == PACKET_POKER_TABLE_GROUP_BALANCE:
#             result = self.service.balance(self.getSerial(), packet.serial)
#             self.sendPacketVerbose(PacketPokerTableGroupBalance(serial = result))
            
        elif packet.type == PACKET_POKER_TABLE_JOIN:
            table = self.service.getTable(packet.game_id)
            if table:
                if not table.joinPlayer(self, self.getSerial()):
                    self.sendPacketVerbose(PacketPokerTable())

        elif not table and packet.type == PACKET_POKER_HAND_REPLAY:
            table = self.createTable(PacketPokerTable())
            if table:
                table.handReplay(self, packet.serial)

        elif packet.type == PACKET_POKER_TABLE:
            table = self.createTable(packet)
            if table:
                table.joinPlayer(self, self.getSerial())
            
        elif packet.type == PACKET_QUIT:
            for table in self.tables.values():
                table.quitPlayer(self, self.getSerial())

        elif packet.type == PACKET_LOGOUT:
            if self.isLogged():
                for table in self.tables.values():
                    table.quitPlayer(self, self.getSerial())
                self.logout()
            else:
                self.sendPacketVerbose(PacketError(code = PacketLogout.NOT_LOGGED_IN,
                                                   message = "Not logged in",
                                                   other_type = PACKET_LOGOUT))
            
    def setPlayerInfo(self, packet):
        self.user.url = packet.url
        self.user.outfit = packet.outfit
        return self.service.setPlayerInfo(packet)

    def setPersonalInfo(self, packet):
        self.personal_info = packet
        self.service.setPersonalInfo(packet)

    def getPlayerInfo(self):
        return PacketPokerPlayerInfo(serial = self.getSerial(),
                                     name = self.getName(),
                                     url = self.user.url,
                                     outfit = self.user.outfit)
    
    def listPlayers(self, packet):
        table = self.service.getTable(packet.game_id)
        if table:
            players = table.listPlayers()
            self.sendPacketVerbose(PacketPokerPlayersList(game_id = packet.game_id,
                                                          players = players))
        
    def listTables(self, packet):
        packets = []
        for table in self.service.listTables(packet.string, self.getSerial()):
            game = table.game
            packet = PacketPokerTable(id = game.id,
                                      name = game.name,
                                      variant = game.variant,
                                      betting_structure = game.betting_structure,
                                      seats = game.max_players,
                                      players = game.allCount(),
                                      hands_per_hour = game.stats["hands_per_hour"],
                                      average_pot = game.stats["average_pot"],
                                      percent_flop = game.stats["percent_flop"],
                                      timeout = table.playerTimeout,
                                      observers = len(table.observers),
                                      waiting = len(table.waiting))
            packets.append(packet)
        ( players, tables ) = self.service.statsTables()
        self.sendPacketVerbose(PacketPokerTableList(players = players,
                                                    tables = tables,
                                                    packets = packets))

    def listHands(self, packet, serial):
        start = packet.start
        count = min(packet.count, 200)
        if serial != None:
            select_list = "select distinct hands.serial from hands,user2hand "
            select_total = "select count(distinct hands.serial) from hands,user2hand "
            where  = " where user2hand.hand_serial = hands.serial "
            where += " and user2hand.user_serial = %d " % serial
            if packet.string:
                where += " and " + packet.string
        else:
            select_list = "select serial from hands "
            select_total = "select count(serial) from hands "
            where = ""
            if packet.string:
                where = "where " + packet.string
        where += " order by hands.serial desc"
        limit = " limit %d,%d " % ( start, count )
        (total, hands) = self.service.listHands(select_list + where + limit, select_total + where)
        self.sendPacketVerbose(PacketPokerHandList(string = packet.string,
                                                   start = packet.start,
                                                   count = packet.count,
                                                   hands = hands,
                                                   total = total))

    def createTable(self, packet):
        table = self.service.createTable(self.getSerial(), {
            "seats": packet.seats,
            "name": packet.name,
            "variant": packet.variant,
            "betting_structure": packet.betting_structure,
            "timeout": packet.timeout,
            "custom_money": packet.custom_money,
            "transient": True })
        if not table:
            self.sendPacket(PacketPokerTable())
        return table            

    def join(self, table):
        game = table.game
        
        self.tables[game.id] = table

        self.sendPacketVerbose(PacketPokerTable(id = game.id,
                                                name = game.name,
                                                variant = game.variant,
                                                seats = game.max_players,
                                                betting_structure = game.betting_structure,
                                                players = game.allCount(),
                                                hands_per_hour = game.stats["hands_per_hour"],
                                                average_pot = game.stats["average_pot"],
                                                percent_flop = game.stats["percent_flop"],
                                                timeout = table.playerTimeout,
                                                observers = len(table.observers),
                                                waiting = len(table.waiting)))
        self.sendPacketVerbose(PacketPokerBatchMode(game_id = game.id))
        nochips = PokerChips(game.chips_values).chips
        for player in game.serial2player.values():
            player_info = table.getPlayerInfo(player.serial)
            self.sendPacketVerbose(PacketPokerPlayerArrive(game_id = game.id,
                                                           serial = player.serial,
                                                           name = player_info.name,
                                                           url = player_info.url,
                                                           outfit = player_info.outfit,
                                                           blind = player.blind,
                                                           remove_next_turn = player.remove_next_turn,
                                                           sit_out = player.sit_out,
                                                           sit_out_next_turn = player.sit_out_next_turn,
                                                           auto = player.auto,
                                                           auto_blind_ante = player.auto_blind_ante,
                                                           wait_for = player.wait_for,
                                                           seat = player.seat))
            if not game.isPlaying(player.serial):
                self.sendPacketVerbose(PacketPokerPlayerChips(game_id = game.id,
                                                              serial = player.serial,
                                                              bet = nochips,
                                                              money = player.money.chips))
                if game.isSit(player.serial):
                    self.sendPacketVerbose(PacketPokerSit(game_id = game.id,
                                                          serial = player.serial))

        self.sendPacketVerbose(PacketPokerSeats(game_id = game.id,
                                                seats = game.seats()))
        if game.isRunning():
            #
            # If a game is running, replay it.
            #
            # If a player reconnects, his serial number will match
            # the serial of some packets, for instance the cards
            # of his hand. We rely on private2public to turn the
            # packet containing cards custom cards into placeholders
            # in this case.
            #
            for past_packet in table.history2packets(game.historyGet(), game.id, table.createCache()):
                self.sendPacketVerbose(table.private2public(past_packet, self.getSerial()))
        self.sendPacketVerbose(PacketPokerStreamMode(game_id = game.id))

    def addPlayer(self, table, seat):
        serial = self.getSerial()
        table.game.addPlayer(serial, seat)
        table.sendNewPlayerInformation(serial)
        
    def connectionLost(self, reason):
        if self.service.verbose:
            print "Connection lost for %s/%d" % ( self.getName(), self.getSerial() )
        for table in self.tables.values():
            table.disconnectPlayer(self, self.getSerial())
        self.logout()

    def getUserInfo(self, serial):
        self.sendPacketVerbose(self.service.getUserInfo(serial))

    def getPersonalInfo(self, serial):
        self.sendPacketVerbose(self.service.getPersonalInfo(serial))

    def removePlayer(self, table, serial):
        game = table.game
        player = game.getPlayer(serial)
        seat = player and player.seat
        if game.removePlayer(serial):
            #
            # If the player is not in a game, the removal will be effective
            # immediately and can be announced to all players, including
            # the one that will be removed.
            #
            packet = PacketPokerPlayerLeave(game_id = game.id, serial = serial, seat = seat)
            self.sendPacketVerbose(packet)
            table.broadcast(packet)
            return True
        else:
            return False

    def sitPlayer(self, table, serial):
        game = table.game
        #
        # It does not harm to sit if already sit and it
        # resets the autoPlayer/wait_for flag.
        #
        if game.sit(serial):
            table.broadcast(PacketPokerSit(game_id = game.id,
                                           serial = serial))

    def sitOutPlayer(self, table, serial):
        game = table.game
        if table.isOpen():
            if game.sitOutNextTurn(serial):
                table.broadcast(PacketPokerSitOut(game_id = game.id,
                                                  serial = serial))
        else:
            game.autoPlayer(serial)
            table.broadcast(PacketPokerAutoFold(game_id = game.id,
                                                serial = serial))

    def autoBlindAnte(self, table, serial, auto):
        game = table.game
        if game.isTournament():
            return
        game.getPlayer(serial).auto_blind_ante = auto
        if auto:
            self.sendPacketVerbose(PacketPokerAutoBlindAnte(game_id = game.id,
                                                            serial = serial))
        else:
            self.sendPacketVerbose(PacketPokerNoautoBlindAnte(game_id = game.id,
                                                              serial = serial))
        
    def setMoney(self, table, amount):
        game = table.game

        if game.payBuyIn(self.getSerial(), amount):
            player = game.getPlayer(self.getSerial())
            nochips = PokerChips(game.chips_values).chips
            table.broadcast(PacketPokerPlayerChips(game_id = game.id,
                                                   serial = self.getSerial(),
                                                   bet = nochips,
                                                   money = player.money.chips))
            return True
        else:
            return False
        
class PokerPredefinedDecks:
    def __init__(self, decks):
        self.decks = decks
        self.index = 0
        
    def shuffle(self, deck):
        deck[:] = self.decks[self.index][:]
        self.index += 1
        if self.index >= len(self.decks):
            self.index = 0
        
class PokerTable:
    def __init__(self, factory, id = 0, description = None):
        self.factory = factory
        settings = self.factory.settings
        self.game = PokerGameServer("poker.%s.xml", factory.dirs)
        self.game.verbose = factory.verbose
        self.history_index = 0
        predefined_decks = settings.headerGetList("/server/decks/deck")
        if predefined_decks:
            self.game.shuffler = PokerPredefinedDecks(map(lambda deck: self.game.eval.string2card(split(deck)), predefined_decks))
        self.observers = []
        self.waiting = []
        game = self.game
        game.id = id
        game.name = description["name"]
        game.setVariant(description["variant"])
        game.setBettingStructure(description["betting_structure"])
        game.setMaxPlayers(int(description["seats"]))
        self.custom_money = int(description.get("custom_money", 0))
        self.playerTimeout = int(description["timeout"])
        self.transient = description.has_key("transient")
        self.tourney = description.get("tourney", None)
        self.delays = settings.headerGetProperties("/server/delays")[0]
        self.autodeal = settings.headerGet("/server/@autodeal") == "yes"
        self.temporaryPlayersPattern = settings.headerGet("/server/users/@temporary")
        self.cache = self.createCache()
        self.owner = 0
        self.serial2client = {}
        self.timer_info = {
            "playerTimeout": None,
            "playerTimeoutSerial": 0
            }
        self.timeout_policy = "sitOut"
        self.previous_dealer = -1
        self.game_delay = {
            "start": 0,
            "delay": 0
            }

    def isValid(self):
        return hasattr(self, "factory")

    def destroy(self):
        if self.transient:
            self.factory.destroyTable(self.game.id)
            
        self.broadcast(PacketPokerTableDestroy(game_id = self.game.id))
        for client in self.serial2client.values() + self.observers:
            del client.tables[self.game.id]
            
        self.factory.deleteTable(self)
        del self.factory

    def getName(self, serial):
        if self.serial2client.has_key(serial):
            name = self.serial2client[serial].getName()
        else:
            name = self.factory.getName(serial)
        return name

    def getPlayerInfo(self, serial):
        if self.serial2client.has_key(serial):
            info = self.serial2client[serial].getPlayerInfo()
        else:
            info = self.factory.getPlayerInfo(serial)
        return info
        
    def listPlayers(self):
        players = []
        game = self.game
        for serial in game.serialsAll():
            players.append((self.getName(serial), game.getPlayerMoney(serial), 0))
        return players
        
    def createCache(self):
        return { "board": PokerCards(), "pockets": {} }
    
    def beginTurn(self):
        info = self.timer_info
        if info.has_key("dealTimeout"):
            if info["dealTimeout"].active():
                info["dealTimeout"].cancel()
            del info["dealTimeout"]

        if not self.isRunning():
            self.historyReset()
            hand_serial = self.factory.getHandSerial()
            game = self.game
            print "Dealing hand %s/%d" % ( game.name, hand_serial )
            game.setTime(time.time())
            game.beginTurn(hand_serial)
        
    def historyReset(self):
        self.history_index = 0
        self.cache = self.createCache()

    def cards2packets(self, game_id, board, pockets, cache):
        packets = []
        #
        # If no pockets or board specified (different from empty pockets),
        # ignore and keep the cached values
        #
        if board != None:
            if board != cache["board"]:
                packets.append(PacketPokerBoardCards(game_id = game_id,
                                                     cards = board.tolist(False)))
                cache["board"] = board.copy()

        if pockets != None:
            #
            # Send new pockets or pockets that changed
            #
            for (serial, pocket) in pockets.iteritems():
                if not cache["pockets"].has_key(serial) or cache["pockets"][serial] != pocket:
                    packets.append(PacketPokerPlayerCards(game_id = game_id,
                                                          serial = serial,
                                                          cards = pocket.toRawList()))
                if not cache["pockets"].has_key(serial):
                    cache["pockets"][serial] = pocket.copy()
        return packets

    def broadcast(self, packets):
        game = self.game

        if not type(packets) is ListType:
            packets = ( packets, )
            
        for packet in packets:
            if self.factory.verbose > 1:
                print "broadcast %s " % packet
            for serial in game.serial2player.keys():
                #
                # Player may be in game but disconnected.
                #
                if self.serial2client.has_key(serial):
                    client = self.serial2client[serial]
                    client.sendPacket(self.private2public(packet, serial))
            for client in self.observers:
                client.sendPacket(self.private2public(packet, 0))

    def private2public(self, packet, serial):
        game = self.game
        #
        # Cards private to each player are shown only to the player
        #
        if packet.type == PACKET_POKER_PLAYER_CARDS and packet.serial != serial:
            private = PacketPokerPlayerCards(game_id = packet.game_id,
                                             serial = packet.serial,
                                             cards = PokerCards(packet.cards).tolist(False))
            return private
        else:
            return packet
        
    def history2packets(self, history, game_id, cache):
        game_index = 0
        player_list_index = 7
        packets = []
        for event in history:
            type = event[0]
            if type == "game":
                (type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips) = event
                if len(serial2chips) > 1:
                    chips_values = serial2chips['values']
                    nochips = PokerChips(chips_values).chips
                    for (serial, chips) in serial2chips.iteritems():
                        if serial == 'values':
                            continue
                        packets.append(PacketPokerPlayerChips(game_id = game_id,
                                                              serial = serial,
                                                              bet = nochips,
                                                              money = chips))
                packets.append(PacketPokerInGame(game_id = game_id,
                                                 players = player_list))
                #
                # This may happen, for instance, if a turn is canceled
                #
                if self.previous_dealer == dealer:
                    previous_dealer = -1
                else:
                    previous_dealer = self.previous_dealer
                packets.append(PacketPokerDealer(game_id = game_id,
                                                 dealer = dealer,
                                                 previous_dealer = previous_dealer))
                self.previous_dealer = dealer
                packets.append(PacketPokerStart(game_id = game_id,
                                                hand_serial = hand_serial,
                                                hands_count = hands_count,
                                                time = time,
                                                level = level))
                
            elif type == "wait_for":
                (type, serial, reason) = event
                packets.append(PacketPokerWaitFor(game_id = game_id,
                                                  serial = serial,
                                                  reason = reason))
                
            elif type == "player_list":
                (type, player_list) = event
                packets.append(PacketPokerInGame(game_id = game_id,
                                                 players = player_list))

            elif type == "round":
                (type, name, board, pockets) = event
                packets.extend(self.cards2packets(game_id, board, pockets, cache))
                packets.append(PacketPokerState(game_id = game_id,
                                                string = name))

            elif type == "position":
                (type, position) = event
                packets.append(PacketPokerPosition(game_id = game_id,
                                                   position = position))
                
            elif type == "showdown":
                (type, board, pockets) = event
                packets.extend(self.cards2packets(game_id, board, pockets, cache))
                
            elif type == "blind_request":
                (type, serial, amount, dead, state) = event
                packets.append(PacketPokerBlindRequest(game_id = game_id,
                                                       serial = serial,
                                                       amount = amount,
                                                       dead = dead,
                                                       state = state))

            elif type == "wait_blind":
                (type, serial) = event
                pass
                    
            elif type == "blind":
                (type, serial, amount, dead) = event
                packets.append(PacketPokerBlind(game_id = game_id,
                                                serial = serial,
                                                amount = amount,
                                                dead = dead))

            elif type == "ante_request":
                (type, serial, amount) = event
                packets.append(PacketPokerAnteRequest(game_id = game_id,
                                                      serial = serial,
                                                      amount = amount))

            elif type == "ante":
                (type, serial, amount) = event
                packets.append(PacketPokerAnte(game_id = game_id,
                                               serial = serial,
                                               amount = amount))

            elif type == "all-in":
                pass
            
            elif type == "call":
                (type, serial, amount) = event
                packets.append(PacketPokerCall(game_id = game_id,
                                               serial = serial))
                
            elif type == "check":
                (type, serial) = event
                packets.append(PacketPokerCheck(game_id = game_id,
                                                serial = serial))
                
            elif type == "fold":
                (type, serial) = event
                packets.append(PacketPokerFold(game_id = game_id,
                                               serial = serial))

            elif type == "raise":
                (type, serial, amount) = event
                packets.append(PacketPokerRaise(game_id = game_id,
                                                serial = serial,
                                                amount = amount))

            elif type == "canceled":
                (type, serial, amount) = event
                packets.append(PacketPokerCanceled(game_id = game_id,
                                                   serial = serial,
                                                   amount = amount))
                
            elif type == "end":
                (type, winners, showdown_stack) = event
                packets.append(PacketPokerState(game_id = game_id,
                                                string = "end"))
                packets.append(PacketPokerWin(game_id = game_id,
                                              serials = winners))

            elif type == "sitOut":
                (type, serial) = event
                packets.append(PacketPokerSitOut(game_id = game_id,
                                                 serial = serial))
                    
            elif type == "rebuy":
                (type, serial, amount) = event
                packets.append(PacketPokerRebuy(game_id = game_id,
                                                serial = serial,
                                                amount = amount))
                    
            elif type == "leave":
                (type, quitters) = event
                for (serial, seat) in quitters:
                    packets.append(PacketPokerPlayerLeave(game_id = game_id,
                                                          serial = serial,
                                                          seat = seat))
                
            elif type == "finish":
                pass
            
            else:
                print "*ERROR* unknown history type %s " % type
        return packets

    def syncDatabase(self):
        game = self.game
        updates = {}
        reset_bet = False
        for event in game.historyGet()[self.history_index:]:
            type = event[0]
            if type == "game":
                pass
            
            elif type == "wait_for":
                pass
            
            elif type == "player_list":
                pass
            
            elif type == "round":
                pass
            
            elif type == "showdown":
                pass
                
            elif type == "position":
                pass
                
            elif type == "blind_request":
                pass
            
            elif type == "wait_blind":
                pass
            
            elif type == "blind":
                (type, serial, amount, dead) = event
                if not updates.has_key(serial):
                    updates[serial] = 0
                updates[serial] -= amount + dead

            elif type == "ante_request":
                pass
            
            elif type == "ante":
                (type, serial, amount) = event
                if not updates.has_key(serial):
                    updates[serial] = 0
                updates[serial] -= amount

            elif type == "all-in":
                pass
            
            elif type == "call":
                (type, serial, amount) = event
                if not updates.has_key(serial):
                    updates[serial] = 0
                updates[serial] -= amount
                
            elif type == "check":
                pass
                
            elif type == "fold":
                pass
            
            elif type == "raise":
                (type, serial, amount) = event
                amount = PokerChips(game.chips_values, amount).toint()
                if not updates.has_key(serial):
                    updates[serial] = 0
                updates[serial] -= amount

            elif type == "canceled":
                (type, serial, amount) = event
                if serial > 0 and amount > 0:
                    if not updates.has_key(serial):
                        updates[serial] = 0
                    updates[serial] += amount
                
            elif type == "end":
                (type, winners, showdown_stack) = event
                game_state = showdown_stack[0]
                for (serial, share) in game_state['serial2share'].iteritems():
                    if not updates.has_key(serial):
                        updates[serial] = 0
                    updates[serial] += share
                reset_bet = True

            elif type == "sitOut":
                pass

            elif type == "leave":
                pass
            
            elif type == "finish":
                (type, hand_serial) = event
                self.factory.saveHand(self.compressedHistory(game.historyGet()), hand_serial)
            
            else:
                print "*ERROR* unknown history type %s " % type

        for (serial, amount) in updates.iteritems():
            self.factory.updatePlayerMoney(serial, game.id, amount)

        if reset_bet:
            self.factory.resetBet(game.id)
        elif hasattr(self, "factory") and self.factory.verbose > 2:
            (money, bet) = self.factory.tableMoneyAndBet(game.id)
            if bet and game.potAndBetsAmount() != bet:
                print " *ERROR* table %d bet mismatch %d in memory versus %d in database" % ( game.id, game.potAndBetsAmount(), bet)

    def historyReduce(self):
        game = self.game
        if self.history_index < len(game.historyGet()):
            game.historyReduce()
            self.history_index = len(game.historyGet())
            
    def compressedHistory(self, history):
        new_history = []
        cached_pockets = None
        cached_board = None
        for event in history:
            type = event[0]
            if ( type == "all-in" or
                 type == "wait_for" ) :
                pass
            
            elif type == "game":
                new_history.append(event)
                
            elif type == "round":
                (type, name, board, pockets) = event

                if pockets != cached_pockets:
                    cached_pockets = pockets
                else:
                    pockets = None

                if board != cached_board:
                    cached_board = board
                else:
                    board = None

                new_history.append((type, name, board, pockets))

            elif type == "showdown":
                (type, board, pockets) = event
                if pockets != cached_pockets:
                    cached_pockets = pockets
                else:
                    pockets = None

                if board != cached_board:
                    cached_board = board
                else:
                    board = None

                new_history.append((type, board, pockets))
            
            elif ( type == "call" or
                   type == "check" or
                   type == "fold" or
                   type == "raise" or
                   type == "canceled" or
                   type == "position" or
                   type == "blind" or
                   type == "ante" or
                   type == "player_list" ):
                new_history.append(event)

            elif type == "end":
                (type, winners, showdown_stack) = event
                new_history.append(event)

            elif type == "sitOut":
                new_history.append(event)
                    
            elif type == "leave":
                pass
                
            elif type == "finish":
                pass
            
            else:
                print "*ERROR* unknown history type %s " % type

        return new_history

    def syncChat(self):
        (subject, messages) = history2messages(self.game, self.game.historyGet()[self.history_index:], serial2name = self.getName)
        if messages or subject:
            if self.factory.chat:
                if messages:
                    message = "".join(map(lambda line: "Dealer: " + line + "\n", messages))
                    self.broadcast(PacketPokerChat(game_id = self.game.id,
                                                   serial = 0,
                                                   message = message))

    def delayedActions(self):
        game = self.game
        for event in game.historyGet()[self.history_index:]:
            type = event[0]
            if type == "game":
                self.game_delay = {
                    "start": time.time(),
                    "delay": float(self.delays["autodeal"])
                    }
            elif ( type == "round" or
                   type == "position" or
                   type == "showdown" or
                   type == "finish" ):
                self.game_delay["delay"] += float(self.delays[type])
                if self.factory.verbose > 2:
                    print "delayedActions: game minimum duration is now " + str(self.game_delay["delay"])

            elif type == "leave":
                (type, quitters) = event
                for (serial, seat) in quitters:
                    self.factory.leavePlayer(serial, game.id, self.custom_money)
                    if self.serial2client.has_key(serial):
                        self.seated2observer(self.serial2client[serial])

    def tourneyEndTurn(self):
        if not self.tourney:
            return
        game = self.game
        for event in game.historyGet()[self.history_index:]:
            type = event[0]
            if type == "end":
                self.factory.tourneyEndTurn(self.tourney, game.id)
        
    def autoDeal(self):
        self.beginTurn()
        self.update()
        
    def scheduleAutoDeal(self):
        info = self.timer_info
        if info.has_key("dealTimeout") and info["dealTimeout"].active():
            info["dealTimeout"].cancel()
        if self.factory.shutting_down:
            if self.factory.verbose > 2:
                print "Not autodealing because server is shutting down"
            return
        if not self.autodeal:
            if self.factory.verbose > 3:
                print "No autodeal"
            return
        if self.isRunning():
            if self.factory.verbose > 3:
                print "Not autodealing %d because game is running" % self.game.id
            return
        game = self.game
        if game.sitCount() < 2:
            if self.factory.verbose > 2:
                print "Not autodealing %d because less than 2 players willing to play" % self.game.id
            return
        if not game.isTournament():
            #
            # Do not auto deal a table where there are only temporary
            # users (i.e. bots)
            #
            onlyTemporaryPlayers = True
            for serial in game.serialsSit():
                if not match("^" + self.temporaryPlayersPattern, self.getName(serial)):
                    onlyTemporaryPlayers = False
                    break
            if onlyTemporaryPlayers:
                if self.factory.verbose > 2:
                    print "Not autodealing because player names sit in match %s" % self.temporaryPlayersPattern
                return
        delay = self.game_delay["delay"]
        if delay > 0:
            delta = ( self.game_delay["start"] + delay ) - time.time()
            if delta < 0: delta = 0
        else:
            delta = 0
        if self.factory.verbose > 2:
            print "Autodeal scheduled in %f seconds" % delta
        info["dealTimeout"] = reactor.callLater(delta, self.autoDeal)
        
    def update(self):
        if not self.isValid():
            return

        self.updateTimers()
        game = self.game
        packets = self.history2packets(game.historyGet()[self.history_index:], game.id, self.cache);
        self.syncDatabase()
        self.syncChat()
        self.delayedActions()
        if len(packets) > 0:
            self.broadcast(packets)
        self.tourneyEndTurn()
        if self.isValid():
            self.historyReduce()
            self.scheduleAutoDeal()

    def handReplay(self, client, hand):
        history = self.factory.loadHand(hand)
        if not history:
            return
        #print "handReplay"
        #pprint(history)
        (type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips) = history[0]
        game = self.game
        for player in game.playersAll():
            client.sendPacketVerbose(PacketPokerPlayerLeave(game_id = game.id,
                                                            serial = player.serial,
                                                            seat = player.seat))
        game.reset()
        game.name = "*REPLAY*"
        game.setVariant(variant)
        game.setBettingStructure(betting_structure)
        game.setTime(time)
        game.setHandsCount(hands_count)
        game.setLevel(level)
        game.hand_serial = hand
        for serial in player_list:
            game.addPlayer(serial)
            game.getPlayer(serial).money.chips = serial2chips[serial]
            game.sit(serial)
        if self.isJoined(client):
            client.join(self)
        else:
            self.joinPlayer(client, client.getSerial())
        serial = client.getSerial()
        cache = self.createCache()
        for packet in self.history2packets(history, game.id, cache):
            if packet.type == PACKET_POKER_PLAYER_CARDS and packet.serial == serial:
                packet.cards = cache["pockets"][serial].toRawList()
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                continue
            client.sendPacketVerbose(packet)

    def isJoined(self, client):
        return client in self.observers or self.serial2client.has_key(client.getSerial())

    def isSeated(self, client):
        return self.isJoined(client) and self.game.isSeated(client.getSerial())

    def isSit(self, client):
        return self.isSeated(client) and self.game.isSit(client.getSerial())

    def isSerialObserver(self, serial):
        return serial in [ client.getSerial() for client in self.observers ]
    
    def isOpen(self):
        return self.game.is_open

    def isRunning(self):
        return self.game.isRunning()

    def seated2observer(self, client):
        del self.serial2client[client.getSerial()]
        self.observers.append(client)

    def observer2seated(self, client):
        self.observers.remove(client)
        self.serial2client[client.getSerial()] = client
        
    def quitPlayer(self, client, serial):
        game = self.game
        if self.isSit(client):
            if self.isOpen():
                game.sitOutNextTurn(serial)
            game.autoPlayer(serial)
        self.update()
        if self.isSeated(client):
            #
            # If not on a closed table, stand up
            #
            if self.isOpen():
                if client.removePlayer(self, serial):
                    self.seated2observer(client)
                    self.factory.leavePlayer(serial, game.id, self.custom_money)
                else:
                    self.update()
            else:
                client.message("cannot quit a closed table, request ignored")
                return False

        if self.isJoined(client):
            #
            # The player is no longer connected to the table
            #
            self.destroyPlayer(client, serial)

        return True

    def kickPlayer(self, serial):
        game = self.game

        player = game.getPlayer(serial)
        seat = player and player.seat
        
        if not game.removePlayer(serial):
            print " *ERROR* kickPlayer did not succeed in removing player %d from game %d" % ( serial, game.id )
            return

        self.factory.leavePlayer(serial, game.id, self.custom_money)

        if self.serial2client.has_key(serial):
            self.seated2observer(self.serial2client[serial])

        self.broadcast(PacketPokerPlayerLeave(game_id = game.id,
                                              serial = serial,
                                              seat = seat))

    def disconnectPlayer(self, client, serial):
        game = self.game

        if self.isSeated(client):
            if self.isOpen():
                #
                # If not on a closed table, stand up.
                #
                if client.removePlayer(self, serial):
                    self.seated2observer(client)
                    self.factory.leavePlayer(serial, game.id, self.custom_money)
                else:
                    self.update()
            else:
                #
                # If on a closed table, the player
                # will stay at the table, he does not
                # have the option to leave.
                #
                pass
                
        if self.isJoined(client):
            #
            # The player is no longer connected to the table
            #
            self.destroyPlayer(client, serial)

        return True

    def leavePlayer(self, client, serial):
        game = self.game
        if self.isSit(client):
            if self.isOpen():
                game.sitOutNextTurn(serial)
            game.autoPlayer(serial)
        self.update()
        if self.isSeated(client):
            #
            # If not on a closed table, stand up
            #
            if self.isOpen():
                if client.removePlayer(self, serial):
                    self.seated2observer(client)
                    self.factory.leavePlayer(serial, game.id, self.custom_money)
                else:
                    self.update()
            else:
                client.error("cannot leave a closed table")
                client.PacketPokerError(game_id = game.id,
                                        serial = serial,
                                        other_type = PACKET_POKER_PLAYER_LEAVE,
                                        code = PacketPokerPlayerLeave.TOURNEY,
                                        message = "Cannot leave tournament table")
                return False

        return True
        
    def movePlayer(self, client, serial, to_game_id):
        game = self.game
        #
        # We are safe because called from within the server under
        # controlled circumstances.
        #

        money = game.serial2player[serial].money

        sit_out = self.movePlayerFrom(serial, to_game_id)
        if client:
            self.destroyPlayer(client, serial)

        other_table = self.factory.getTable(to_game_id)
        if client:
            other_table.serial2client[serial] = client

        money_check = self.factory.movePlayer(serial, game.id, to_game_id)
        if money_check != money.toint():
            print " *ERROR* movePlayer: player %d money %d in database, %d in memory" % ( serial, money_check, money.toint() )

        if client:
            client.join(other_table)
        other_table.movePlayerTo(serial, money, sit_out)
        other_table.sendNewPlayerInformation(serial)
        if self.factory.verbose:
            print "player %d moved from table %d to table %d" % ( serial, game.id, to_game_id )

    def sendNewPlayerInformation(self, serial):
        packets = self.newPlayerInformation(serial)
        self.broadcast(packets)

    def newPlayerInformation(self, serial):
        player_info = self.getPlayerInfo(serial)
        game = self.game
        player = game.getPlayer(serial)
        if self.factory.verbose > 1:
            print "about player %d" % serial
        nochips = PokerChips(game.chips_values).chips
        packets = [
            PacketPokerPlayerArrive(game_id = game.id,
                                    serial = serial,
                                    name = player_info.name,
                                    url = player_info.url,
                                    outfit = player_info.outfit,
                                    blind = player.blind,
                                    remove_next_turn = player.remove_next_turn,
                                    sit_out = player.sit_out,
                                    sit_out_next_turn = player.sit_out_next_turn,
                                    auto = player.auto,
                                    auto_blind_ante = player.auto_blind_ante,
                                    wait_for = player.wait_for,
                                    seat = player.seat),
            PacketPokerSeats(game_id = game.id, seats = game.seats()),
            PacketPokerPlayerChips(game_id = game.id,
                                   serial = serial,
                                   bet = nochips,
                                   money = game.getPlayer(serial).money.chips),
            ]
        return packets

    def movePlayerTo(self, serial, money, sit_out):
        game = self.game
        game.open()
        game.addPlayer(serial)
        player = game.getPlayer(serial)
        player.money.set(money)
        player.buy_in_payed = True
        game.sit(serial)
        game.autoBlindAnte(serial)
        if sit_out: game.sitOut(serial)
        game.close()

    def movePlayerFrom(self, serial, to_game_id):
        game = self.game
        player = game.getPlayer(serial)
        self.broadcast(PacketPokerTableMove(game_id = game.id,
                                            serial = serial,
                                            to_game_id = to_game_id,
                                            seat = player.seat))
        sit_out = game.isSitOut(serial)
        game.removePlayer(serial)
        return sit_out

    def possibleObserverLoggedIn(self, client, serial):
        game = self.game
        if not game.getPlayer(serial):
            return False
        self.observer2seated(client)
        game.comeBack(serial)
        return True
            
    def joinPlayer(self, client, serial):
        game = self.game
        #
        # Silently do nothing if already joined
        #
        if self.isJoined(client):
            return True

        if len(client.tables) >= self.factory.simultaneous:
            if self.factory.verbose:
                print " *ERROR* joinPlayer: %d seated at %d tables (max %d)" % ( serial, len(client.tables), self.factory.simultaneous )
            return False
        
        #
        # Player is now an observer, unless he is seated
        # at the table.
        #
        client.join(self)
        if not self.game.isSeated(client.getSerial()):
            self.observers.append(client)
        else:
            self.serial2client[serial] = client
        #
        # If it turns out that the player is seated
        # at the table already, presumably because he
        # was previously disconnected from a tournament
        # or an ongoing game.
        #
        if self.isSeated(client):
            #
            # Sit back immediately, as if we just seated
            #
            game.comeBack(serial)
            
        return True

    def seatPlayer(self, client, serial, seat):
        game = self.game
        if not self.isJoined(client):
            client.error("player %d can't seat before joining" % serial)
            return False
        #
        # Do nothing if already seated
        #
        if self.isSeated(client):
            print "player %d is already seated" % serial
            return False

        if not game.canAddPlayer(serial):
            client.error("table refuses to seat player %d" % serial)
            return False

        amount = 0
        if self.transient:
            amount = game.buyIn()
            
        if not self.factory.seatPlayer(serial, game.id, self.custom_money, amount):
            return False

        self.observer2seated(client)

        client.addPlayer(self, seat)
        if amount > 0:
            client.setMoney(self, amount)

        return True

    def sitOutPlayer(self, client, serial):
        game = self.game
        if not self.isSeated(client):
            client.error("player %d can't sit out before getting a seat" % serial)
            return False
        #
        # Silently do nothing if already sit out
        #
        if not self.isSit(client):
            return True

        client.sitOutPlayer(self, serial)
        return True

    def chatPlayer(self, client, serial, message):
        self.broadcast(PacketPokerChat(game_id = self.game.id,
                                       serial = serial,
                                       message = message + "\n"))

    def autoBlindAnte(self, client, serial, auto):
        game = self.game
        if not self.isSeated(client):
            client.error("player %d can't set auto blind/ante before getting a seat" % serial)
            return False
        client.autoBlindAnte(self, serial, auto)
        
    def sitPlayer(self, client, serial):
        game = self.game
        if not self.isSeated(client):
            client.error("player %d can't sit before getting a seat" % serial)
            return False

        client.sitPlayer(self, serial)
        return True
        
    def destroyPlayer(self, client, serial):
        game = self.game
        if client in self.observers:
            self.observers.remove(client)
        else:
            del self.serial2client[serial]
        del client.tables[self.game.id]

    def buyInPlayer(self, client, amount):
        game = self.game
        if not self.isSeated(client):
            client.error("player %d can't bring money to a table before getting a seat" % client.getSerial())
            return False

        if client.getSerial() in game.serialsPlaying():
            client.error("player %d can't bring money while participating in a hand" % client.getSerial())
            return False

        if self.transient:
            client.error("player %d can't bring money to a transient table" % client.getSerial())
            return False

        amount = self.factory.buyInPlayer(client.getSerial(), game.id, self.custom_money, max(amount, game.buyIn()))
        return client.setMoney(self, amount)
        
    def rebuyPlayerRequest(self, client, amount):
        game = self.game
        if not self.isSeated(client):
            client.error("player %d can't rebuy to a table before getting a seat" % client.getSerial())
            return False

        serial = client.getSerial()
        player = game.getPlayer(serial)
        if not player.isBuyInPayed():
            client.error("player %d can't rebuy before paying the buy in" % serial)
            return False

        if self.transient:
            client.error("player %d can't rebuy on a transient table" % serial)
            return False

        maximum = game.maxBuyIn() - game.getPlayerMoney(serial)
        if maximum <= 0:
            client.error("player %d can't bring more money to the table" % serial)
            return False

        if amount == 0:
            amount = game.buyIn()
            
        amount = self.factory.buyInPlayer(serial, game.id, self.custom_money, min(amount, maximum))

        if amount == 0:
            client.error("player %d is broke and cannot rebuy" % serial)
            return False
        
        if not game.rebuy(serial, amount):
            client.error("player %d rebuy denied" % serial)
            return False

        self.broadcast(PacketPokerRebuy(game_id = game.id,
                                        serial = serial,
                                        amount = amount))
        return True
        
    def playerWarningTimer(self, serial):
        game = self.game
        info = self.timer_info
        if game.isRunning() and serial == game.getSerialInPosition():
            timeout = self.playerTimeout / 2;
            self.broadcast(PacketPokerTimeoutWarning(game_id = game.id,
                                                     serial = serial,
                                                     timeout = timeout))
            info["playerTimeout"] = reactor.callLater(timeout, self.playerTimeoutTimer, serial)
        else:
            self.updateTimers()

    def playerTimeoutTimer(self, serial):
        if self.factory.verbose:
            print "player %d times out" % serial
        game = self.game
        if game.isRunning() and serial == game.getSerialInPosition():
            if self.timeout_policy == "sitOut":
                game.sitOutNextTurn(serial)
                game.autoPlayer(serial)
            elif self.timeout_policy == "fold":
                game.autoPlayer(serial)
                self.broadcast(PacketPokerAutoFold(game_id = game.id,
                                                   serial = serial))
            else:
                print " *ERROR* unknown timeout_policy %s" % self.timeout_policy
            self.broadcast(PacketPokerTimeoutNotice(game_id = game.id,
                                                    serial = serial))
            self.update()
        else:
            self.updateTimers()
        
    def cancelTimers(self):
        info = self.timer_info

        timer = info["playerTimeout"]
        if timer != None:
            if timer.active():
                timer.cancel()
            info["playerTimeout"] = None
        info["playerTimeoutSerial"] = 0
        
    def updateTimers(self):
        game = self.game
        info = self.timer_info

        timer = info["playerTimeout"]
        if game.isRunning():
            serial = game.getSerialInPosition()
            #
            # Any event in the game resets the player timeout
            #
            if ( info["playerTimeoutSerial"] != serial or
                 len(game.historyGet()) > self.history_index ):
                if timer != None and timer.active():
                    timer.cancel()

                timer = reactor.callLater(self.playerTimeout / 2, self.playerWarningTimer, serial)
                info["playerTimeout"] = timer
                info["playerTimeoutSerial"] = serial
        else:
            #
            # If the game is not running, cancel the previous timeout
            #
            self.cancelTimers()

class IPokerService(Interface):

    def createAvatar(self):
        """ """

    def destroyAvatar(self, avatar):
        """ """

class IPokerFactory(Interface):

    def createAvatar(self):
        """ """

    def destroyAvatar(self, avatar):
        """ """

    def buildProtocol(self, addr):
        """ """

class PokerFactoryFromPokerService(protocol.ServerFactory):

    implements(IPokerFactory)

    protocol = PokerServerProtocol

    def __init__(self, service):
        self.service = service
        self.verbose = service.verbose

    def createAvatar(self):
        """ """
        return self.service.createAvatar()

    def destroyAvatar(self, avatar):
        """ """
        return self.service.destroyAvatar(avatar)

components.registerAdapter(PokerFactoryFromPokerService,
                           IPokerService,
                           IPokerFactory)

class PokerService(service.Service):

    implements(IPokerService)

    def __init__(self, settings):
        self.db = PokerDatabase(settings)
        self.poker_auth = PokerAuth(self.db, settings)
        self.settings = settings
        self.dirs = split(settings.headerGet("/server/path"))
        self.serial2client = {}
        self.tables = []
        self.groups = {}
        self.table_serial = 100
        self.shutting_down = False
        self.down = False
        self.simultaneous = self.settings.headerGetInt("/server/@simultaneous")
        self.verbose = self.settings.headerGetInt("/server/@verbose")
        self.chat = self.settings.headerGet("/server/@chat") == "yes"
        self.cleanupCrashedTables()
        for description in self.settings.headerGetProperties("/server/table"):
            self.createTable(0, description)
        self.tourneys = {}
        self.schedule2tourneys = {}
        self.tourneys_schedule = {}
        self.updateTourneysSchedule()
        self.poker_auth.SetLevel(PACKET_POKER_SEAT, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_GET_USER_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_GET_PERSONAL_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_PLAYER_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_TOURNEY_REGISTER, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_HAND_SELECT_ALL, User.ADMIN)

    def stopServiceFinish(self, x):
        service.Service.stopService(self)

    def stopService(self):
        deferred = self.shutdown()
        deferred.addCallback(self.stopServiceFinish)
        return deferred
    
    def shutdown(self):
        self.shutting_down = True
        self.shutdown_deferred = defer.Deferred()
        reactor.callLater(0, self.shutdownCheck)
        return self.shutdown_deferred
        
    def shutdownCheck(self):
        if self.down:
            return
        
        playing = 0
        for table in self.tables:
            if table.game.isRunning():
                playing += 1
        if self.verbose and playing > 0:
            print "Shutting down, waiting for %d games to finish" % playing
        if playing <= 0:
            if self.verbose:
                print "Shutdown immediately"
            self.down = True
            self.shutdown_deferred.callback(True)
        else:
            reactor.callLater(10, self.shutdownCheck)
        
    def isShuttingDown(self):
        return self.shutting_down
    
    def stopFactory(self):
        pass

    def createAvatar(self):
        return PokerAvatar(self)

    def destroyAvatar(self, avatar):
        avatar.connectionLost("Disconnected")

    def auth(self, name, password):
        for (serial, client) in self.serial2client.iteritems():
            if client.getName() == name:
                if self.verbose: print "PokerService::auth: %s attempt to login more than once" % name
                return ( False, "Already logged in from somewhere else" ) 
        return self.poker_auth.auth(name, password)
            
    def updateTourneysSchedule(self):
        cursor = self.db.cursor(DictCursor)

        sql = ( " select * from tourneys_schedule " )
        cursor.execute(sql)
        result = cursor.fetchall()
        self.tourneys_schedule = dict(zip(map(lambda schedule: schedule['serial'], result), result))
        cursor.close()
        self.checkTourneysSchedule()
        reactor.callLater(10 * 60, self.updateTourneysSchedule)

    def checkTourneysSchedule(self):
        if self.verbose > 4: print "checkTourneysSchedule"
        for schedule in filter(lambda schedule: schedule['respawn'] == 'y', self.tourneys_schedule.values()):
            schedule_serial = schedule['serial']
            if ( not self.schedule2tourneys.has_key(schedule_serial) or
                 not filter(lambda tourney: tourney.state == TOURNAMENT_STATE_REGISTERING, self.schedule2tourneys[schedule_serial]) ):
                self.spawnTourney(schedule)
        now = time.time()
        for tourney in filter(lambda tourney: tourney.state == TOURNAMENT_STATE_COMPLETE, self.tourneys.values()):
            if now - tourney.finish_time > 15 * 60:
                self.deleteTourney(tourney)
        reactor.callLater(60, self.checkTourneysSchedule)

    def spawnTourney(self, schedule):
        cursor = self.db.cursor()
        cursor.execute("insert into tourneys "
                       " (schedule_serial, name, description_short, description_long, players_quota, variant, betting_structure, seats_per_game, custom_money, buy_in, rake, sit_n_go, breaks_interval, rebuy_delay, add_on, add_on_delay )"
                       " values"
                       " (%s,              %s,   %s,                %s,               %s,            %s,      %s,                %s,             %s,         %s,     %s,   %s,       %s,              %s,          %s,     %s )",
                       ( schedule['serial'],
                         schedule['name'],
                         schedule['description_short'],
                         schedule['description_long'],
                         schedule['players_quota'],
                         schedule['variant'],
                         schedule['betting_structure'],
                         schedule['seats_per_game'],
                         schedule['custom_money'],
                         schedule['buy_in'],
                         schedule['rake'],
                         schedule['sit_n_go'],
                         schedule['breaks_interval'],
                         schedule['rebuy_delay'],
                         schedule['add_on'],
                         schedule['add_on_delay'] ) )
        if self.verbose > 2: print "spawnTourney: " + str(schedule)
        #
        # Accomodate with MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            tourney_serial = cursor.lastrowid
        else:
            tourney_serial = cursor.insert_id()
        cursor.close()
        
        tourney = PokerTournament(**schedule)
        tourney.serial = tourney_serial
        tourney.verbose = self.verbose
        tourney.schedule_serial = schedule['serial']
        tourney.custom_money = schedule['custom_money']
        tourney.callback_new_state = self.tourneyNewState
        tourney.callback_create_game = self.tourneyCreateTable
        tourney.callback_game_filled = self.tourneyGameFilled
        tourney.callback_destroy_game = self.tourneyDestroyGame
        tourney.callback_move_player = self.tourneyMovePlayer
        tourney.callback_remove_player = self.tourneyRemovePlayer
        if not self.schedule2tourneys.has_key(schedule['serial']):
            self.schedule2tourneys[schedule['serial']] = []
        self.schedule2tourneys[schedule['serial']].append(tourney)
        self.tourneys[tourney.serial] = tourney

    def deleteTourney(self, tourney):
        if self.verbose > 2: print "deleteTourney: %d" % tourney.serial
        self.schedule2tourneys[tourney.schedule_serial].remove(tourney)
        if len(self.schedule2tourneys[tourney.schedule_serial]) <= 0:
            del self.schedule2tourneys[tourney.schedule_serial]
        del self.tourneys[tourney.serial]

    def tourneyNewState(self, tourney):
        cursor = self.db.cursor()
        updates = [ "state = '" + tourney.state + "'" ]
        if tourney.state == TOURNAMENT_STATE_RUNNING:
            updates.append("start_time = %d" % tourney.start_time)
        sql = "update tourneys set " + ", ".join(updates) + " where serial = " + str(tourney.serial)
        if self.verbose > 4: print "tourneyNewState: " + sql
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()
        
    def tourneyEndTurn(self, tourney, game_id):
        if not tourney.endTurn(game_id):
            self.tourneyFinished(tourney)
        
    def tourneyFinished(self, tourney):
        tourney_schedule = self.tourneys_schedule[tourney.schedule_serial]
        prizes = tourney.prizes(tourney_schedule['buy_in'])
        winners = tourney.winners[:len(prizes)]
        cursor = self.db.cursor()
        base = tourney_schedule['custom_money'] == 'y' and "custom" or "play"
        while prizes:
            prize = prizes.pop(0)
            serial = winners.pop(0)
            sql = "update users set " + base + "_money = " + base + "_money + " + str(prize) + " where serial = " + str(serial)
            if self.verbose > 4: print "tourneyFinished: " + sql
            cursor.execute(sql)
            if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()

    def tourneyGameFilled(self, tourney, game):
        tourney_schedule = self.tourneys_schedule[tourney.schedule_serial]
        table = self.getTable(game.id)
        cursor = self.db.cursor()
        for serial in game.serialsAll():
            client = self.serial2client.get(serial, None)
            if client:
                table.serial2client[serial] = client
            self.seatPlayer(serial, game.id, 'n', game.buyIn())

            if client:
                client.join(table)
            sql = "update user2tourney set table_serial = %d where user_serial = %d and tourney_serial = %d" % ( game.id, serial, tourney.serial ) 
            if self.verbose > 4: print "tourneyGameFilled: " + sql
            cursor.execute(sql)
            if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()
        table.update()

    def tourneyCreateTable(self, tourney):
        tourney_schedule = self.tourneys_schedule[tourney.schedule_serial]
        table = self.createTable(0, { 'name': tourney.name + str(self.table_serial),
                                      'variant': tourney.variant,
                                      'betting_structure': tourney.betting_structure,
                                      'seats': tourney.seats_per_game,
                                      'custom_money': ( tourney_schedule['custom_money'] == 'y' and 1 or 0 ),
                                      'timeout': 60,
                                      'transient': True,
                                      'tourney': tourney,
                                      })
        table.timeout_policy = "fold"
        self.table_serial += 1
        return table.game

    def tourneyDestroyGame(self, tourney, game):
        table = self.getTable(game.id)
        table.destroy()

    def tourneyMovePlayer(self, tourney, from_game_id, to_game_id, serial):
        from_table = self.getTable(from_game_id)
        from_table.movePlayer(from_table.serial2client[serial], serial, to_game_id)
        cursor = self.db.cursor()
        sql = "update user2tourney set table_serial = %d where user_serial = %d and tourney_serial = %d" % ( to_game_id, serial, tourney.serial ) 
        if self.verbose > 4: print "tourneyMovePlayer: " + sql
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()

    def tourneyRemovePlayer(self, tourney, game_id, serial):
        table = self.getTable(game_id)
        table.kickPlayer(serial)
        cursor = self.db.cursor()
        sql = "update user2tourney set rank = %d, table_serial = -1 where user_serial = %d and tourney_serial = %d" % ( tourney.getRank(serial), serial, tourney.serial ) 
        if self.verbose > 4: print "tourneyRemovePlayer: " + sql
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()

    def tourneyPlayersList(self, tourney_serial):
        if not self.tourneys.has_key(tourney_serial):
            return PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                               code = PacketPokerTourneyRegister.DOES_NOT_EXIST,
                               message = "Tournament %d does not exist" % tourney_serial)
        tourney = self.tourneys[tourney_serial]
        players = map(lambda serial: ( self.getName(serial), -1, 0 ), tourney.players)
        return PacketPokerTourneyPlayersList(serial = tourney_serial,
                                             players = players)

    def tourneyStats(self):
        players = reduce(operator.add, map(lambda tourney: tourney.registered, self.tourneys.values()))
        scheduled = filter(lambda schedule: schedule['respawn'] == 'n', self.tourneys_schedule.values())
        return ( players, len(self.tourneys) + len(scheduled) )

    def tourneySelect(self, string):
        tourneys = filter(lambda schedule: schedule['respawn'] == 'n', self.tourneys_schedule.values()) + map(lambda tourney: tourney.__dict__, self.tourneys.values() )
        criterion = split(string, "\t")
        if string == '':
            return tourneys
        elif len(criterion) > 1:
            ( custom_money, type ) = criterion
            sit_n_go = type == 'sit_n_go' and 'y' or 'n'
            if custom_money:
                return filter(lambda tourney: tourney['custom_money'] == custom_money and tourney['sit_n_go'] == sit_n_go, tourneys)
            else:
                return filter(lambda tourney: tourney['sit_n_go'] == sit_n_go, tourneys)
        else:
            return filter(lambda tourney: tourney['name'] == string, tourneys)
    
    def tourneyRegister(self, packet):
        serial = packet.serial
        tourney_serial = packet.game_id
        client = self.serial2client.get(serial, None)
        
        if not self.tourneys.has_key(tourney_serial):
            error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                code = PacketPokerTourneyRegister.DOES_NOT_EXIST,
                                message = "Tournament %d does not exist" % tourney_serial)
            print error
            if client: client.sendPacketVerbose(error)
            return False
        tourney = self.tourneys[tourney_serial]

        if tourney.isRegistered(serial):
            error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                code = PacketPokerTourneyRegister.ALREADY_REGISTERED,
                                message = "Player %d already registered in tournament %d " % ( serial, tourney_serial ) )
            print error
            if client: client.sendPacketVerbose(error)
            return False

        if not tourney.canRegister(serial):
            error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                code = PacketPokerTourneyRegister.REGISTRATION_REFUSED,
                                message = "Registration refused in tournament %d " % tourney_serial)
            print error
            if client: client.sendPacketVerbose(error)
            return False

        cursor = self.db.cursor()
        #
        # Buy in
        #
        schedule = self.tourneys_schedule[tourney.schedule_serial]
        base = schedule['custom_money'] == 'y' and "custom" or "play"
        withdraw = schedule['buy_in'] + schedule['rake']
        sql = ( "update users set "
                " users." + str(base) + "_money = users." + str(base) + "_money - " + str(withdraw) + " "
                " where serial = " + str(serial) + " and "
                "       " + str(base) + "_money > " + str(withdraw) )
        if self.verbose > 1:
            print "tourneyRegister: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount == 0:
            error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                code = PacketPokerTourneyRegister.NOT_ENOUGH_MONEY,
                                message = "Not enough money to enter the tournament %d" % tourney_serial)
            if client: client.sendPacketVerbose(error)
            print error
            return False
        if cursor.rowcount != 1:
            print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
            if client:
                client.sendPacketVerbose(PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                                     code = PacketPokerTourneyRegister.SERVER_ERROR,
                                                     message = "Server error"))
            return False
        #
        # Register
        #
        sql = "insert into user2tourney (user_serial, tourney_serial) values (%d, %d)" % ( serial, tourney_serial )
        if self.verbose > 4: print "tourneyRegister: " + sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* insert %d rows (expected 1): %s " % ( cursor.rowcount, sql )
            cursor.close()
            if client:
                client.sendPacketVerbose(PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                                     code = PacketPokerTourneyRegister.SERVER_ERROR,
                                                     message = "Server error"))
            return False
        cursor.close()

        # notify success
        client.sendPacketVerbose(packet)
        tourney.register(serial)
        return True

    def tourneyUnregister(self, packet):
        serial = packet.serial
        tourney_serial = packet.game_id
        if not self.tourneys.has_key(tourney_serial):
            return PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                               code = PacketPokerTourneyUnregister.DOES_NOT_EXIST,
                               message = "Tournament %d does not exist" % tourney_serial)
        tourney = self.tourneys[tourney_serial]

        if not tourney.isRegistered(serial):
            return PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                               code = PacketPokerTourneyUnregister.NOT_REGISTERED,
                               message = "Player %d is not registered in tournament %d " % ( serial, tourney_serial ) )

        if not tourney.canUnregister(serial):
            return PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                               code = PacketPokerTourneyUnregister.TOO_LATE,
                               message = "It is too late to unregister player %d from tournament %d " % ( serial, tourney_serial ) )

        cursor = self.db.cursor()
        #
        # Refund buy in
        #
        schedule = self.tourneys_schedule[tourney.schedule_serial]
        base = schedule['custom_money'] == 'y' and "custom" or "play"
        withdraw = schedule['buy_in'] + schedule['rake']
        sql = ( "update users set "
                " users." + str(base) + "_money = users." + str(base) + "_money + " + str(withdraw) + " "
                " where serial = " + str(serial) )
        if self.verbose > 1:
            print "tourneyUnregister: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
            return PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                               code = PacketPokerTourneyUnregister.SERVER_ERROR,
                               message = "Server error")
        #
        # Unregister
        #
        sql = "delete from user2tourney where user_serial = %d and tourney_serial = %d" % ( serial, tourney_serial )
        if self.verbose > 4: print "tourneyUnregister: " + sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* insert %d rows (expected 1): %s " % ( cursor.rowcount, sql )
            cursor.close()
            return PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                               code = PacketPokerTourneyUnregister.SERVER_ERROR,
                               message = "Server error")
        cursor.close()

        tourney.unregister(serial)
            
        return packet

    def getHandSerial(self):
        cursor = self.db.cursor()
        cursor.execute("insert into hands (description) values ('[]')")
        #
        # Accomodate with MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            serial = cursor.lastrowid
        else:
            serial = cursor.insert_id()
        cursor.close()
        return int(serial)

    def getHandHistory(self, hand_serial, serial):
        history = self.loadHand(hand_serial)

        if not history:
            return PacketPokerError(game_id = hand_serial,
                                    serial = serial,
                                    other_type = PACKET_POKER_HAND_HISTORY,
                                    code = PacketPokerHandHistory.NOT_FOUND,
                                    message = "Hand %d was not found in history of player %d" % ( hand_serial, serial ) )

        (type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips) = history[0]

        if serial not in player_list:
            return PacketPokerError(game_id = hand_serial,
                                    serial = serial,
                                    other_type = PACKET_POKER_HAND_HISTORY,
                                    code = PacketPokerHandHistory.FORBIDDEN,
                                    message = "Player %d did not participate in hand %d" % ( serial, hand_serial ) )
            
        serial2name = {}
        for serial in player_list:
            serial2name[serial] = self.getName(serial)
        #
        # Filter out the pocket cards that do not belong to player "serial"
        #
        for event in history:
            if event[0] == "round":
                (type, name, board, pockets) = event
                if pockets:
                    for (player_serial, pocket) in pockets.iteritems():
                        if player_serial != serial:
                            pocket.loseNotVisible()
            elif event[0] == "showdown":
                (type, board, pockets) = event
                if pockets:
                    for (player_serial, pocket) in pockets.iteritems():
                        if player_serial != serial:
                            pocket.loseNotVisible()

        return PacketPokerHandHistory(game_id = hand_serial,
                                      serial = serial,
                                      history = str(history),
                                      serial2name = str(serial2name))
        
    def loadHand(self, hand_serial):
        cursor = self.db.cursor()
        sql = ( "select description from hands where serial = " + str(hand_serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* loadHand(%d) expected one row got %d" % ( hand_serial, cursor.rowcount )
            cursor.close()            
            return None
        (description,) = cursor.fetchone()
        cursor.close()
        try:
            history = eval(description.replace("\r",""))
            return history
        except:
            print " *ERROR* loadHand(%d) eval failed for %s" % ( hand_serial, description )
            print_exc()
            return None
            
    def saveHand(self, description, hand_serial):
        (type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips) = description[0]
        cursor = self.db.cursor()

        sql = ( "update hands set " + 
                " description = %s "
                " where serial = " + str(hand_serial) )
        if self.verbose > 1:
            print "saveHand: %s" % sql
        cursor.execute(sql, pformat(description))
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            print " *ERROR* modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql )
            cursor.close()
            return

        sql = "insert into user2hand values "
        sql += ", ".join(map(lambda player_serial: "(%d, %d)" % ( player_serial, hand_serial ), player_list))
        if self.verbose > 1:
            print "saveHand: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != len(player_list):
            print " *ERROR* inserted %d rows (expected exactly %d): %s " % ( cursor.rowcount, len(player_list), sql )

       
        cursor.close()
        
    def listHands(self, sql_list, sql_total):
        cursor = self.db.cursor()
        if self.verbose > 1:
            print "listHands: " + sql_list + " " + sql_total
        cursor.execute(sql_list)
        hands = cursor.fetchall()
        cursor.execute(sql_total)
        total = cursor.fetchone()[0]
        cursor.close()
        return (total, map(lambda x: x[0], hands))

    def statsTables(self):
        players = reduce(operator.add, map(lambda table: table.game.allCount(), self.tables))
        return ( players, len(self.tables) )
                         
    def listTables(self, string, serial):
        criterion = split(string, "\t")
        if string == '' or string == 'all':
            return self.tables
        elif string == 'my':
            return filter(lambda table: serial in table.game.serialsAll(), self.tables)
        elif string == 'play':
            return filter(lambda table: table.custom_money == 0, self.tables)
        elif string == 'custom':
            return filter(lambda table: table.custom_money == 1, self.tables)
        elif len(criterion) > 1:
            ( custom_money, variant ) = criterion
            if custom_money:
                custom_money = custom_money == 'y' and 1 or 0
                return filter(lambda table: table.game.variant == variant and table.custom_money == custom_money, self.tables)
            else:
                return filter(lambda table: table.game.variant == variant, self.tables)
        else:
            return filter(lambda table: table.game.name == string, self.tables)

    def cleanUp(self, temporary_users = ''):
        cursor = self.db.cursor()
        sql = "delete from user2table"
        cursor.execute(sql)
        cursor.close()

        if temporary_users:
            cursor = self.db.cursor()
            sql = "delete from users where name like '" + temporary_users + "%'"
            cursor.execute(sql)
            cursor.close()
        
    def getMoney(self, serial, base):
        cursor = self.db.cursor()
        sql = ( "select " + base + "_money from users where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getMoney(%d) expected one row got %d" % ( serial, cursor.rowcount )
            cursor.close()            
            return 0
        (money,) = cursor.fetchone()
        cursor.close()
        money = int(money)
        if money < 0:
            print " *ERROR* getMoney(%d) found %d" % ( serial, money)
            money = 0
        return money

    def getPlayerInfo(self, serial):
        placeholder = PacketPokerPlayerInfo(serial = serial,
                                            name = "anonymous",
                                            url= "default",
                                            outfit = "default")
        if serial == 0:
            return placeholder
        
        cursor = self.db.cursor()
        sql = ( "select name,skin_url,skin_outfit from users where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getPlayerInfo(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return placeholder
        (name,skin_url,skin_outfit) = cursor.fetchone()
        cursor.close()
        return PacketPokerPlayerInfo(serial = serial,
                                     name = name,
                                     url = skin_url,
                                     outfit = skin_outfit)

    def getUserInfo(self, serial):
        cursor = self.db.cursor()
        
        sql = ( "select play_money,custom_money,point_money,rating,email,name from users where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getUserInfo(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return PacketPokerUserInfo(serial = serial)
        (play_money,custom_money,point_money,rating,email,name) = cursor.fetchone()
        if email == None: email = ""

        sql = ( "select sum(user2table.bet) + sum(user2table.money) from user2table,pokertables "
                "  where user2table.user_serial = " + str(serial) + " and "
                "        user2table.table_serial = pokertables.serial and "
                "        pokertables.custom_money = \"n\" ")
        cursor.execute(sql)
        if cursor.rowcount < 1:
            print " *ERROR* getUserInfo(%d) play money expected one row got %d" % ( serial, cursor.rowcount )
            return PacketPokerUserInfo(serial = serial)
        else:
            (play_money_in_game,) = cursor.fetchone()
            if not play_money_in_game:
                play_money_in_game = 0

        sql = ( "select sum(user2table.bet) + sum(user2table.money) from user2table,pokertables "
                "  where user2table.user_serial = " + str(serial) + " and "
                "        user2table.table_serial = pokertables.serial and "
                "        pokertables.custom_money = \"y\" ")
        cursor.execute(sql)
        if cursor.rowcount < 1:
            print " *ERROR* getUserInfo(%d) custom money expected one row got %d" % ( serial, cursor.rowcount )
            return PacketPokerUserInfo(serial = serial)
        else:
            (custom_money_in_game,) = cursor.fetchone()
            if not custom_money_in_game:
                custom_money_in_game = 0
        
        cursor.close()
        
        packet = PacketPokerUserInfo(serial = serial,
                                     name = name,
                                     email = email,
                                     play_money = play_money,
                                     play_money_in_game = play_money_in_game,
                                     custom_money = custom_money,
                                     custom_money_in_game = custom_money_in_game,
                                     point_money = point_money,
                                     rating = rating)
        return packet

    def getPersonalInfo(self, serial):
        user_info = self.getUserInfo(serial)
        print "getPersonalInfo %s" % str(user_info)
        packet = PacketPokerPersonalInfo(serial = user_info.serial,
                                         name = user_info.name,
                                         email = user_info.email,
                                         play_money = user_info.play_money,
                                         play_money_in_game = user_info.play_money_in_game,
                                         custom_money = user_info.custom_money,
                                         custom_money_in_game = user_info.custom_money_in_game,
                                         point_money = user_info.point_money,
                                         rating = user_info.rating)
        cursor = self.db.cursor()
        sql = ( "select addr_street,addr_zip,addr_town,addr_state,addr_country,phone from users_private where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getPersonalInfo(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return PacketPokerPersonalInfo(serial = serial)
        (packet.addr_street, packet.addr_zip, packet.addr_town, packet.addr_state, packet.addr_country, packet.phone) = cursor.fetchone()
        cursor.close()
        return packet

    def setPersonalInfo(self, personal_info):
        cursor = self.db.cursor()
        sql = ( "update users_private set "
                " addr_street = '" + personal_info.addr_street + "', "
                " addr_zip = '" + personal_info.addr_zip + "', "
                " addr_town = '" + personal_info.addr_town + "', "
                " addr_state = '" + personal_info.addr_state + "', "
                " addr_country = '" + personal_info.addr_country + "', "
                " phone = '" + personal_info.phone + "' "
                " where serial = " + str(personal_info.serial) )
        if self.verbose > 1:
            print "setPersonalInfo: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            print " *ERROR* setPersonalInfo: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql )
            return False
        else:
            return True

    def setAccount(self, packet):
        #
        # name constraints check
        #
        status = checkName(packet.name)
        if not status[0]:
            return PacketError(code = status[1],
                               message = status[2],
                               other_type = packet.type)
        #
        # Look for user
        #
        cursor = self.db.cursor()
        cursor.execute("select serial from users where name = '%s'" % packet.name)
        numrows = int(cursor.rowcount)
        #
        # password constraints check
        #
        if ( numrows == 0 or ( numrows > 0 and packet.password != "" )):
            status = checkPassword(packet.password)
            if not status[0]:
                return PacketError(code = status[1],
                                   message = status[2],
                                   other_type = packet.type)
        #
        # email constraints check
        #
        email_regexp = ".*.@.*\..*$"
        if not re.match(email_regexp, packet.email):
            return PacketError(code = PacketPokerSetAccount.INVALID_EMAIL,
                               message = "email %s does not match %s " % ( packet.email, email_regexp ),
                               other_type = packet.type)
        if numrows == 0:
            cursor.execute("select serial from users where email = '%s' " % packet.email)
            numrows = int(cursor.rowcount)
            if numrows > 0:
                return PacketError(code = PacketPokerSetAccount.EMAIL_ALREADY_EXISTS,
                                   message = "there already is another account with the email %s" % packet.email,
                                   other_type = packet.type)
            #
            # User does not exists, create it
            #
            sql = "insert into users (name, password, email) values ('%s', '%s', '%s')" % (packet.name, packet.password, packet.email)
            cursor.execute(sql)
            if cursor.rowcount != 1:
                print " *ERROR* setAccount: insert %d rows (expected 1): %s " % ( cursor.rowcount, sql )
                return PacketError(code = PacketPokerSetAccount.SERVER_ERROR,
                                   message = "inserted %d rows (expected 1)" % cursor.rowcount,
                                   other_type = packet.type)
            #
            # Accomodate for MySQLdb versions < 1.1
            #
            if hasattr(cursor, "lastrowid"):
                packet.serial = cursor.lastrowid
            else:
                packet.serial = cursor.insert_id()
            cursor.execute("insert into users_private (serial) values ('%d')" % packet.serial)
            if int(cursor.rowcount) == 0:
                print " *ERROR* setAccount: unable to create user_private entry for serial %d" % packet.serial
                return PacketError(code = PacketPokerSetAccount.SERVER_ERROR,
                                   message = "unable to create user_private entry for serial %d" % packet.serial,
                                   other_type = packet.type)
        else:
            #
            # User exists, update name, password and email
            #
            (serial,) = cursor.fetchone()
            if serial != packet.serial:
                return PacketError(code = PacketPokerSetAccount.NAME_ALREADY_EXISTS,
                                   message = "user name %s already exists" % packet.name,
                                   other_type = packet.type)
            cursor.execute("select serial from users where email = '%s' and serial != %d" % ( packet.email, serial ))
            numrows = int(cursor.rowcount)
            if numrows > 0:
                return PacketError(code = PacketPokerSetAccount.EMAIL_ALREADY_EXISTS,
                                   message = "there already is another account with the email %s" % packet.email,
                                   other_type = packet.type)
            set_password = packet.password and ", password = '" + packet.password + "' " or ""
            sql = ( "update users set "
                    " name = '" + packet.name + "', "
                    " email = '" + packet.email + "' " + 
                    set_password +
                    " where serial = " + str(packet.serial) )
            if self.verbose > 1:
                print "setAccount: %s" % sql
            cursor.execute(sql)
            if cursor.rowcount != 1 and cursor.rowcount != 0:
                print " *ERROR* setAccount: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql )
                return PacketError(code = PacketPokerSetAccount.SERVER_ERROR,
                                   message = "modified %d rows (expected 1 or 0)" % cursor.rowcount,
                                   other_type = packet.type)
        #
        # Set personal information
        #
        if not self.setPersonalInfo(packet):
                return PacketError(code = PacketPokerSetAccount.SERVER_ERROR,
                                   message = "unable to set personal information",
                                   other_type = packet.type)
        return self.getPersonalInfo(packet.serial)

    def setPlayerInfo(self, player_info):
        cursor = self.db.cursor()
        sql = ( "update users set "
                " name = '" + player_info.name + "', "
                " skin_url = '" + player_info.url + "', "
                " skin_outfit = '" + player_info.outfit + "' "
                " where serial = " + str(player_info.serial) )
        if self.verbose > 1:
            print "setPlayerInfo: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            print " *ERROR* setPlayerInfo: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql )
            return False
        return True
        
        
    def getName(self, serial):
        if serial == 0:
            return "anonymous"
        
        cursor = self.db.cursor()
        sql = ( "select name from users where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getName(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return "UNKNOWN"
        (name,) = cursor.fetchone()
        cursor.close()
        return name

    def buyInPlayer(self, serial, table_id, custom_money, amount):
        base = custom_money and "custom" or "play"
        withdraw = min(self.getMoney(serial, base), amount)
        cursor = self.db.cursor()
        sql = ( "update users,user2table set "
                " user2table.money = user2table.money + " + str(withdraw) + ", "
                " users." + str(base) + "_money = users." + str(base) + "_money - " + str(withdraw) + " "
                " where users.serial = " + str(serial) + " and "
                "       user2table.user_serial = " + str(serial) + " and "
                "       user2table.table_serial = " + str(table_id) )
        if self.verbose > 1:
            print "buyInPlayer: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 0 and cursor.rowcount != 2:
            print " *ERROR* modified %d rows (expected 0 or 2): %s " % ( cursor.rowcount, sql )
        return withdraw

    def seatPlayer(self, serial, table_id, custom_money, amount):
        custom_money = custom_money and "y" or "n"
        status = True
        cursor = self.db.cursor()
        sql = ( "insert user2table ( user_serial, table_serial, money, custom_money) values "
                " ( " + str(serial) + ", " + str(table_id) + ", " + str(amount) + ", \"" + custom_money + "\" )" )
        if self.verbose > 1:
            print "seatPlayer: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* inserted %d rows (expected 1): %s " % ( cursor.rowcount, sql )
            status = False
        cursor.close()
        return status

    def movePlayer(self, serial, from_table_id, to_table_id):
        money = -1
        cursor = self.db.cursor()
        sql = ( "select money from user2table "
                "  where user_serial = " + str(serial) + " and"
                "        table_serial = " + str(from_table_id) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* movePlayer(%d) expected one row got %d" % ( serial, cursor.rowcount )
        (money,) = cursor.fetchone()
        cursor.close()

        if money > 0:
            cursor = self.db.cursor()
            sql = ( "update user2table "
                    "  set table_serial = " + str(to_table_id) +
                    "  where user_serial = " + str(serial) + " and"
                    "        table_serial = " + str(from_table_id) )
            if self.verbose > 1:
                print "movePlayer: %s" % sql
            cursor.execute(sql)
            if cursor.rowcount != 1:
                print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
                money = -1
            cursor.close()

        # HACK CHECK
#        cursor = self.db.cursor()
#        sql = ( "select sum(money), sum(bet) from user2table" )
#        cursor.execute(sql)
#        (total_money,bet) = cursor.fetchone()
#        if total_money + bet != 120000:
#            print "BUG(6) %d" % (total_money + bet)
#            os.abort()
#        cursor.close()
        # END HACK CHECK
        
        return money
        
    def leavePlayer(self, serial, table_id, custom_money):
        base = custom_money and "custom" or "play"
        status = True
        cursor = self.db.cursor()
        sql = ( "update users,user2table set "
                " users." + str(base) + "_money = users." + str(base) + "_money + user2table.money "
                " where users.serial = " + str(serial) + " and "
                "       user2table.user_serial = " + str(serial) + " and "
                "       user2table.table_serial = " + str(table_id) )
        if self.verbose > 1:
            print "leavePlayer %s" % sql
        cursor.execute(sql)
        if cursor.rowcount > 1:
            print " *ERROR* modified %d rows (expected 0 or 1): %s " % ( cursor.rowcount, sql )
            status = False
        sql = ( "delete from user2table "
                " where user_serial = " + str(serial) + " and "
                "       table_serial = " + str(table_id) )
        if self.verbose > 1:
            print "leavePlayer %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()
        return status

    def updatePlayerMoney(self, serial, table_id, amount):
        if amount == 0:
            return True
        status = True
        cursor = self.db.cursor()
        sql = ( "update user2table set "
                " money = money + " + str(amount) + ", "
                " bet = bet - " + str(amount) +
                " where user_serial = " + str(serial) + " and "
                "       table_serial = " + str(table_id) )
        if self.verbose > 1:
            print "updatePlayerMoney: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
            status = False
        cursor.close()
        
#         # HACK CHECK
#         cursor = self.db.cursor()
#         sql = ( "select sum(money), sum(bet) from user2table" )
#         cursor.execute(sql)
#         (money,bet) = cursor.fetchone()
#         if money + bet != 120000:
#             print "BUG(4) %d" % (money + bet)
#             os.abort()
#         cursor.close()

#         cursor = self.db.cursor()
#         sql = ( "select user_serial,table_serial,money from user2table where money < 0" )
#         cursor.execute(sql)
#         if cursor.rowcount >= 1:
#             (user_serial, table_serial, money) = cursor.fetchone()
#             print "BUG(11) %d/%d/%d" % (user_serial, table_serial, money)
#             os.abort()
#         cursor.close()
#         # END HACK CHECK
        
        return status

    def tableMoneyAndBet(self, table_id):
        cursor = self.db.cursor()
        sql = ( "select sum(money), sum(bet) from user2table where table_serial = " + str(table_id) )
        cursor.execute(sql)
        status = cursor.fetchone()
        cursor.close()
        return  status
        
    def destroyTable(self, table_id):

#         # HACK CHECK
#         cursor = self.db.cursor()
#         sql = ( "select * from user2table where money != 0 and bet != 0 and table_serial = " + str(table_id) )
#         cursor.execute(sql)
#         if cursor.rowcount != 0:
#             print "BUG(10)"
#             os.abort()
#         cursor.close()
#         # END HACK CHECK
        
        cursor = self.db.cursor()
        sql = ( "delete from user2table "
                "  where table_serial = " + str(table_id) )
        if self.verbose > 1:
            print "destroy: %s" % sql
        cursor.execute(sql)

#     def setRating(self, winners, serials):
#         url = self.settings.headerGet("/server/@rating")
#         if url == "":
#             return
        
#         params = []
#         for first in range(0, len(serials) - 1):
#             for second in range(first + 1, len(serials)):
#                 first_wins = serials[first] in winners
#                 second_wins = serials[second] in winners
#                 if first_wins or second_wins:
#                     param = "a=%d&b=%d&c=" % ( serials[first], serials[second] )
#                     if first_wins and second_wins:
#                         param += "2"
#                     elif first_wins:
#                         param += "0"
#                     else:
#                         param += "1"
#                     params.append(param)

#         params = join(params, '&')
#         if self.verbose > 2:
#             print "setRating: url = %s" % url + params
#         content = loadURL(url + params)
#         if self.verbose > 2:
#             print "setRating: %s" % content
        
    def resetBet(self, table_id):
        status = True
        cursor = self.db.cursor()
        sql = ( "update user2table set bet = 0 "
                " where table_serial = " + str(table_id) )
        if self.verbose > 1:
            print "resetBet: %s" % sql
        cursor.execute(sql)
        cursor.close()

#         # HACK CHECK
#         cursor = self.db.cursor()
#         sql = ( "select sum(money), sum(bet) from user2table" )
#         cursor.execute(sql)
#         (money,bet) = cursor.fetchone()
#         if money + bet != 120000:
#             print "BUG(2) %d" % (money + bet)
#             os.abort()
#         cursor.close()
#         # END HACK CHECK
        
        return status
        
    def getTable(self, game_id):
        for table in self.tables:
            if game_id == table.game.id:
                game = table.game
                return table
        return False

    def createTable(self, owner, description):
        #
        # Do not create two tables by the same name
        #
        if filter(lambda table: table.game.name == description["name"], self.tables):
            print "*ERROR* will not create two tables by the same name %s" % description["name"]
            return False
        
        id = self.table_serial
        table = PokerTable(self, id, description)
        table.owner = owner
        custom_money = table.custom_money and "y" or "n"

        cursor = self.db.cursor()
        sql = ( "insert pokertables ( serial, name, custom_money ) values "
                " ( " + str(id) + ", \"" + description["name"] + "\", \"" + custom_money + "\" ) " )
        if self.verbose > 1:
            print "createTable: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* inserted %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()

        self.tables.append(table)
        self.table_serial += 1

        if self.verbose:
            print "table created : %s" % table.game.name

        return table

    def cleanupCrashedTables(self):
        cursor = self.db.cursor()

        sql = ( "select user_serial,table_serial,custom_money from user2table " )
        cursor.execute(sql)
        for i in xrange(cursor.rowcount):
            (user_serial, table_serial, custom_money) = cursor.fetchone()
            self.leavePlayer(user_serial, table_serial, custom_money == "y")

        cursor.close()
        self.shutdownTables()

    def shutdownTables(self):
        cursor = self.db.cursor()
        sql = ( "delete from pokertables" )
        cursor.execute(sql)
        if self.verbose > 1:
            print "shutdownTables: " + sql
        cursor.close()
        
    def deleteTable(self, table):
        if self.verbose:
            print "table %s/%d removed from server" % ( table.game.name, table.game.id )
        self.tables.remove(table)
        cursor = self.db.cursor()
        sql = ( "delete from  pokertables where serial = " + str(table.game.id) )
        if self.verbose > 1:
            print "deleteTable: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* deleted %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()
        for groups in self.groups.itervalues():
            if table in groups:
                groups.remove(table)

    def setTableGroup(self, owner, table_ids):
        tables = []
        for table in self.tables:
            if table.game.id in table_ids:
                if table.owner != owner:
                    print "*ERROR* player %d attempted to balance table %d but is not the owner" % ( owner, table.game.id )
                    return 0
                tables.append(table)

        serial = self.table_serial
        self.groups[serial] = tables
        self.table_serial += 1
        return serial

    def unsetTableGroup(self, owner, group_id):
        if not group_id in self.groups.keys():
            print "*ERROR* not group id %d" % group_id
            return 0
        
        for table in self.groups[group_id]:
            if table.owner != owner:
                print "*ERROR* player %d attempted to unset table group %d but is not the owner of the tables it contains" % ( owner, group_id )
                return 0
        del self.groups[group_id]
        return group_id
        
    def balance(self, owner, group_id):
        for table in self.groups[group_id]:
            if table.owner != owner:
                print "*ERROR* player %d attempted to balance table group %d but is not the owner of all the tables it contains" % ( owner, group_id )
                return 0

        balance_packet = PacketPokerTableGroupBalance(serial = group_id)
        tables = self.groups[group_id]

        games = [ table.game for table in tables ]
        id2table = dict(zip([ game.id for game in games ], tables))
        
        to_break = breakGames(games)
        tables_broken = {}
        for (from_id, to_id, serials) in to_break:
            for serial in serials:
                table = id2table[from_id]
                table.movePlayer(table.serial2client[serial], serial, to_id)
            tables_broken[from_id] = True

        if len(to_break) > 0:
            for table in self.groups[group_id]:
                table.broadcast(balance_packet)
            for table_id in tables_broken.keys():
                table = id2table[table_id]
                table.destroy()
            return group_id
        
        to_equalize = equalizeGames(games)
        for (from_id, to_id, serial) in to_equalize:
            table = id2table[from_id]
            table.movePlayer(table.serial2client[serial], serial, to_id)
            table.broadcast(PacketPokerTableGroupBalance(serial = group_id))
        if len(to_equalize) > 0:
            for table in self.groups[group_id]:
                table.broadcast(balance_packet)
            return group_id
        else:
            return 0

class PokerAuth:

    def __init__(self, db, settings):
        self.db = db
        self.type2auth = {}
        self.verbose = settings.headerGetInt("/server/@verbose")

    def SetLevel(self, type, level):
        self.type2auth[type] = level

    def GetLevel(self, type):
        return self.type2auth.has_key(type) and self.type2auth[type]
    
    def auth(self, name, password):
        cursor = self.db.cursor()
        cursor.execute("select serial, password, privilege from users "
                       "where name = '%s'" % name)
        numrows = int(cursor.rowcount)
        serial = 0
        privilege = User.REGULAR
        if numrows <= 0:
            if self.verbose > 1:
                print "user %s does not exist, create it" % name
            serial = self.userCreate(name, password)
        elif numrows > 1:
            print "more than one row for %s" % name
            return ( False, "Invalid login or password" )
        else: 
            (serial, password_sql, privilege) = cursor.fetchone()
            cursor.close()
            if password_sql != password:
                print "password mismatch for %s" % name
                return ( False, "Invalid login or password" )

        return ( (serial, name, privilege), None )

    def userCreate(self, name, password):
        if self.verbose:
            print "creating user %s" % name,
        cursor = self.db.cursor()
        cursor.execute("insert into users (name, password) values ('%s', '%s')" %
                       (name, password))
        #
        # Accomodate for MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            serial = cursor.lastrowid
        else:
            serial = cursor.insert_id()
        if self.verbose:
            print "create user with serial %s" % serial
        cursor.execute("insert into users_private (serial) values ('%d')" % serial)
        cursor.close()
        return int(serial)

class SSLContextFactory:

    def __init__(self, settings):
        self.pem_file = None
        for dir in split(settings.headerGet("/server/path")):
            if exists(dir + "/poker.pem"):
                self.pem_file = dir + "/poker.pem"
        
    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file(self.pem_file)
        ctx.use_privatekey_file(self.pem_file)
        return ctx

from twisted.web import resource, server

class PokerTree(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.putChild("RPC2", PokerXMLRPC(self.service))
        self.putChild("SOAP", PokerSOAP(self.service))
        self.putChild("", self)

    def render_GET(self, request):
        return "Use /RPC2"

components.registerAdapter(PokerTree, IPokerService, resource.IResource)

class PokerXML(resource.Resource):

    encoding = "ISO-8859-1"
    
    def __init__(self, service):
        self.service = service
        self.verbose = service.verbose

    def sessionExpires(self, session):
        self.service.destroyAvatar(session.avatar)
        del session.avatar

    def render(self, request):
        if self.verbose > 2:
            print "PokerXML::render " + request.content.read()
        request.content.seek(0, 0)
        if self.encoding is not None:
            mimeType = 'text/xml; charset="%s"' % self.encoding
        else:
            mimeType = "text/xml"
        request.setHeader("Content-type", mimeType)
        args = self.getArguments(request)
        if self.verbose > 2:
            print "PokerXML: " + str(args)
        session = None
        use_sessions = args[0]
        args = args[1:]
        if use_sessions == "use sessions":
            session = request.getSession()
            if not hasattr(session, "avatar"):
                session.avatar = self.service.createAvatar()
                session.notifyOnExpire(lambda: self.sessionExpires(session))
# For test : trigger session expiration in the next 4 seconds
# see http://twistedmatrix.com/bugs/issue1090
#                session.lastModified -= 900
#                reactor.callLater(4, session.checkExpired)
            avatar = session.avatar
        else:
            avatar = self.service.createAvatar()

        logout = False
        result_packets = []
        for packet in self.args2packets(args):
            if isinstance(packet, PacketError):
                result_packets.append(packet)
                break
            else:
                results = avatar.handlePacket(packet)
                if use_sessions == "use sessions" and len(results) > 1:
                    for result in results:
                        if isinstance(result, PacketSerial):
                            if self.verbose > 2:
                                print "PokerXML: Session cookie " + str(request.cookies)
                            result.cookie = request.cookies[0]
                            break
                result_packets.extend(results)
                if isinstance(packet, PacketLogout):
                    logout = True
        result_maps = self.packets2maps(result_packets)

        if use_sessions != "use sessions":
            self.service.destroyAvatar(avatar)
        elif use_sessions == "use sessions" and logout:
            session.expire()

        result_string = self.maps2result(result_maps)
        request.setHeader("Content-length", str(len(result_string)))
        return result_string

    def args2packets(self, args):
        packets = []
        for arg in args:
            if re.match("^[a-zA-Z]+$", arg['type']):
                try:
                    fun_args = len(arg) > 1 and '(**arg)' or '()'
                    packets.append(eval(arg['type'] + fun_args))
                except:
                    packets.append(PacketError(message = "Unable to instantiate %s(%s)" % ( arg['type'], arg )))
            else:
                packets.append(PacketError(message = "Invalid type name %s" % arg['type']))
        return packets

    def packets2maps(self, packets):
        maps = []
        for packet in packets:
            attributes = packet.__dict__.copy()
            attributes['type'] = packet.__class__.__name__
            maps.append(attributes)
        return maps

    def getArguments(self, request):
        pass
    
    def maps2result(self, maps):
        pass

    def fromutf8(self, tree):
        return self.walk(tree, lambda x: x.encode(self.encoding))

    def toutf8(self, tree):
        return self.walk(tree, lambda x: unicode(x, self.encoding))

    def walk(self, tree, convert):
        if type(tree) is TupleType or type(tree) is ListType:
            result = map(lambda x: self.walk(x, convert), tree)
            if type(tree) is TupleType:
                return tuple(result)
            else:
                return result
        elif type(tree) is DictionaryType:
            for (key, value) in tree.iteritems():
                tree[key] = self.walk(value, convert)
            return tree
        elif ( type(tree) is UnicodeType or type(tree) is StringType ):
            return convert(tree)
        else:
            return tree

import xmlrpclib

class PokerXMLRPC(PokerXML):

    def getArguments(self, request):
        ( args, functionPath ) = xmlrpclib.loads(request.content.read())
        return self.fromutf8(args)
    
    def maps2result(self, maps):
        return xmlrpclib.dumps((maps, ), methodresponse = 1)

import SOAPpy

class PokerSOAP(PokerXML):

    def getArguments(self, request):
        data = request.content.read()

        p, header, body, attrs = SOAPpy.parseSOAPRPC(data, 1, 1, 1)

        methodName, args, kwargs, ns = p._name, p._aslist, p._asdict, p._ns
        
        # deal with changes in SOAPpy 0.11
        if callable(args):
            args = args()
        if callable(kwargs):
            kwargs = kwargs()

        return self.fromutf8(SOAPpy.simplify(args[0]))
    
    def maps2result(self, maps):
        return SOAPpy.buildSOAP(kw = {'Result': self.toutf8(maps)},
                                method = 'returnPacket',
                                encoding = self.encoding)

def makeApplication(argv):
    configuration = argv[-1][-4:] == ".xml" and argv[-1] or "/etc/poker-network/poker.server.xml"
    settings = Config([''])
    settings.load(configuration)
    if not settings.header:
        sys.exit(1)

    application = service.Application('poker')
    serviceCollection = service.IServiceCollection(application)
    poker_service = PokerService(settings)
    poker_service.cleanUp(temporary_users = settings.headerGet("/server/users/@temporary"))
    poker_service.setServiceParent(serviceCollection)

    poker_factory = IPokerFactory(poker_service)

    #
    # Poker protocol (with or without SSL)
    #
    tcp_port = settings.headerGetInt("/server/listen/@tcp")
    internet.TCPServer(tcp_port, poker_factory
                       ).setServiceParent(serviceCollection)    

    tcp_ssl_port = settings.headerGetInt("/server/listen/@tcp_ssl")
    internet.SSLServer(tcp_ssl_port, poker_factory, SSLContextFactory(settings)
                       ).setServiceParent(serviceCollection)

    site = server.Site(resource.IResource(poker_service))

    #
    # HTTP (with or without SLL) that implements XML-RPC and SOAP
    #
    http_port = settings.headerGetInt("/server/listen/@http")
    internet.TCPServer(http_port, site
                       ).setServiceParent(serviceCollection)

    http_ssl_port = settings.headerGetInt("/server/listen/@http_ssl")
    internet.SSLServer(http_ssl_port, site, SSLContextFactory(settings)
                       ).setServiceParent(serviceCollection)
    return application
        
application = makeApplication(sys.argv)

def run():
    try:
        app.startApplication(application, None)
        reactor.run()
    except:
        if application.verbose:
            print_exc()
        else:
            print sys.exc_value

if __name__ == '__main__':
    run()
