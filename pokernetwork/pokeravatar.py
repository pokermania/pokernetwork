#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
# Copyright (C) 2008 Bradley M. Kuhn <bkuhn@ebb.org>
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
#  Henry Precheur <henry@precheur.org> (2004)
#

from string import join
import sets

from twisted.internet import defer

from pokerengine import pokergame
from pokernetwork.user import User, checkNameAndPassword
from pokernetwork.pokerpackets import *
from pokernetwork.pokerexplain import PokerExplain

DEFAULT_PLAYER_USER_DATA = { 'ready': True }

class PokerAvatar:

    def __init__(self, service):
        self.protocol = None
        self.roles = sets.Set()
        self.service = service
        self.tables = {}
        self.user = User()
        self._packets_queue = []
        self.setExplain(0)
        self.has_session = False
        self.bugous_processing_hand = False
        self.noqueuePackets()

    def __str__(self):
        return "PokerAvatar serial = %s, name = %s" % ( self.getSerial(), self.getName() )

    def setExplain(self, what):
        if what:
            if self.explain == None:
                if self.tables:
                    self.error("setExplain must be called when not connected to any table")
                    return False

                self.explain = PokerExplain(dirs = self.service.dirs,
                                            verbose = self.service.verbose)
        else:
            self.explain = None
        return True
            
    def setProtocol(self, protocol):
        self.protocol = protocol

#    def __del__(self):
#       self.message("instance deleted")

    def error(self, string):
        self.message("ERROR " + str(string))
        
    def message(self, string):
        print "PokerAvatar: " + str(string)
        
    def isAuthorized(self, type):
        return self.user.hasPrivilege(self.service.poker_auth.GetLevel(type))

    def login(self, info):
        (serial, name, privilege) = info
        self.user.serial = serial
        self.user.name = name
        self.user.privilege = privilege

        player_info = self.service.getPlayerInfo(serial)
        self.user.url = player_info.url
        self.user.outfit = player_info.outfit
        
        self.sendPacketVerbose(PacketSerial(serial = self.user.serial))
        if PacketPokerRoles.PLAY in self.roles:
            self.service.serial2client[serial] = self
        if self.service.verbose:
            self.message("user %s/%d logged in" % ( self.user.name, self.user.serial ))
        if self.protocol:
            self.has_session = self.service.sessionStart(self.getSerial(), str(self.protocol.transport.client[0]))
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
            if PacketPokerRoles.PLAY in self.roles:
                del self.service.serial2client[self.user.serial]
            if self.has_session:
                self.service.sessionEnd(self.getSerial())
            self.user.logout()
        
    def auth(self, packet):
        status = checkNameAndPassword(packet.name, packet.password)
        if status[0]:
            ( info, reason ) = self.service.auth(packet.name, packet.password, self.roles)
            code = 0
        else:
            self.message("auth: failure " + str(status))
            reason = status[2]
            code = status[1]
            info = False
        if info:
            self.sendPacketVerbose(PacketAuthOk())
            self.login(info)
        else:
            self.sendPacketVerbose(PacketAuthRefused(message = reason,
                                                     code = code,
                                                     other_type = PACKET_LOGIN))

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
	if self.explain and not isinstance(packet, defer.Deferred) and packet.type != PACKET_ERROR:
	    self.explain.explain(packet)
	    packets = self.explain.forward_packets
	else:
	    packets = [ packet ]
        if self._queue_packets:
            self._packets_queue.extend(packets)
        else:
	    for packet in packets:
                self.protocol.sendPacket(packet)

    queueDeferred = sendPacket
    
    def sendPacketVerbose(self, packet):
        if self.service.verbose > 1 and hasattr(packet, 'type') and packet.type != PACKET_PING or self.service.verbose > 5:
            self.message("sendPacket(%d): %s" % ( self.getSerial(), str(packet) ))
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
        if self.service.verbose > 2 and packet.type != PACKET_PING:
            self.message("handlePacketLogic(%d): " % self.getSerial() + str(packet))
        
        if packet.type == PACKET_POKER_EXPLAIN:
            if self.setExplain(packet.value):
                self.sendPacketVerbose(PacketAck())
            else:
                self.sendPacketVerbose(PacketError(other_type = PACKET_POKER_EXPLAIN))
            return
        
        if packet.type == PACKET_POKER_STATS_QUERY:
            self.sendPacketVerbose(self.service.stats(packet.string))
            return
        
        if packet.type == PACKET_POKER_MONITOR:
            self.sendPacketVerbose(self.service.monitor(self))
            return
        
        if not self.isAuthorized(packet.type):
            self.sendPacketVerbose(PacketAuthRequest())
            return

        if packet.type == PACKET_PING:
            return
        
        if packet.type == PACKET_LOGIN:
            if self.isLogged():
                self.sendPacketVerbose(PacketError(other_type = PACKET_LOGIN,
                                                   code = PacketLogin.LOGGED,
                                                   message = "already logged in"))
            else:
                self.auth(packet)
            return

        if packet.type == PACKET_POKER_GET_PLAYER_INFO:
            self.sendPacketVerbose(self.getPlayerInfo())
            return

        if packet.type == PACKET_POKER_GET_PLAYER_IMAGE:
            self.sendPacketVerbose(self.service.getPlayerImage(packet.serial))
            return

        if packet.type == PACKET_POKER_GET_USER_INFO:
            if self.getSerial() == packet.serial:
                self.getUserInfo(packet.serial)
            else:
                self.message("attempt to get user info for user %d by user %d" % ( packet.serial, self.getSerial() ))
            return

        elif packet.type == PACKET_POKER_GET_PERSONAL_INFO:
            if self.getSerial() == packet.serial:
                self.getPersonalInfo(packet.serial)
            else:
                self.message("attempt to get personal info for user %d by user %d" % ( packet.serial, self.getSerial() ))
                self.sendPacketVerbose(PacketAuthRequest())
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
                self.message("attempt to set player info for player %d by player %d" % ( packet.serial, self.getSerial() ))
            return
                
        elif packet.type == PACKET_POKER_PLAYER_IMAGE:
            if self.getSerial() == packet.serial:
                if self.service.setPlayerImage(packet):
                    self.sendPacketVerbose(PacketAck())
                else:
                    self.sendPacketVerbose(PacketError(other_type = PACKET_POKER_PLAYER_IMAGE,
                                                       code = PACKET_POKER_PLAYER_IMAGE,
                                                       message = "Failed to save set player image"))
            else:
                self.message("attempt to set player info for player %d by player %d" % ( packet.serial, self.getSerial() ))
            return
                
        elif packet.type == PACKET_POKER_PERSONAL_INFO:
            if self.getSerial() == packet.serial:
                self.setPersonalInfo(packet)
            else:
                self.message("attempt to set player info for player %d by player %d" % ( packet.serial, self.getSerial() ))
            return

        elif packet.type == PACKET_POKER_CASH_IN:
            if self.getSerial() == packet.serial:
                self.queueDeferred(self.service.cashIn(packet))
            else:
                self.message("attempt to cash in for user %d by user %d" % ( packet.serial, self.getSerial() ))
                self.sendPacketVerbose(PacketPokerError(serial = self.getSerial(),
                                                        other_type = PACKET_POKER_CASH_IN))
            return

        elif packet.type == PACKET_POKER_CASH_OUT:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.service.cashOut(packet))
            else:
                self.message("attempt to cash out for user %d by user %d" % ( packet.serial, self.getSerial() ))
                self.sendPacketVerbose(PacketPokerError(serial = self.getSerial(),
                                                        other_type = PACKET_POKER_CASH_OUT))
            return

        elif packet.type == PACKET_POKER_CASH_QUERY:
            self.sendPacketVerbose(self.service.cashQuery(packet))
            return

        elif packet.type == PACKET_POKER_CASH_OUT_COMMIT:
            self.sendPacketVerbose(self.service.cashOutCommit(packet))
            return

        elif packet.type == PACKET_POKER_SET_ROLE:
            self.sendPacketVerbose(self.setRole(packet))
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
                self.service.autorefill(packet.serial)
                self.service.tourneyRegister(packet)
            else:
                self.message("attempt to register in tournament %d for player %d by player %d" % ( packet.game_id, packet.serial, self.getSerial() ))
            return
            
        elif packet.type == PACKET_POKER_TOURNEY_UNREGISTER:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.service.tourneyUnregister(packet))
            else:
                self.message("attempt to unregister from tournament %d for player %d by player %d" % ( packet.game_id, packet.serial, self.getSerial() ))
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
                self.message("attempt to get history of player %d by player %d" % ( packet.serial, self.getSerial() ))
            return

        elif packet.type == PACKET_POKER_HAND_SELECT_ALL:
            self.listHands(packet, None)
            return

        elif packet.type == PACKET_POKER_TABLE_JOIN:
            table = self.service.getTable(packet.game_id)
            if table:
                if not table.joinPlayer(self, self.getSerial()):
                    self.sendPacketVerbose(PacketPokerTable())
            return


        table = self.packet2table(packet)
            
        if table:
            if self.service.verbose > 2:
                self.message("packet for table " + str(table.game.id))
            game = table.game

            if packet.type == PACKET_POKER_READY_TO_PLAY:
                if self.getSerial() == packet.serial:
                    self.sendPacketVerbose(table.readyToPlay(packet.serial))
                else:
                    self.message("attempt to set ready to play for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_PROCESSING_HAND:
                if self.getSerial() == packet.serial:
                    if not self.bugous_processing_hand:
                        self.sendPacketVerbose(table.processingHand(packet.serial))
                    else:
                        self.sendPacketVerbose(PacketPokerError(game_id = game.id,
                                                                serial = self.getSerial(),
                                                                other_type = PACKET_POKER_PROCESSING_HAND))
                else:
                    self.message("attempt to set processing hand for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_START:
                if not game.isEndOrNull():
                    self.message("player %d tried to start a new game while in game " % self.getSerial())
                    self.sendPacketVerbose(PacketPokerStart(game_id = game.id))
                elif self.service.shutting_down:
                    self.message("server shutting down")
                elif table.owner != 0:
                    if self.getSerial() != table.owner:
                        self.message("player %d tried to start a new game but is not the owner of the table" % self.getSerial())
                        self.sendPacketVerbose(PacketPokerStart(game_id = game.id))
                    else:
                        table.beginTurn()
                else:
                    self.message("player %d tried to start a new game but is not the owner of the table" % self.getSerial())

            elif packet.type == PACKET_POKER_SEAT:
                if PacketPokerRoles.PLAY not in self.roles:
                    self.sendPacketVerbose(PacketPokerError(game_id = game.id,
                                                            serial = packet.serial,
                                                            code = PacketPokerSeat.ROLE_PLAY,
                                                            message = "PACKET_POKER_ROLES must set the role to PLAY before chosing a seat",
                                                            other_type = PACKET_POKER_SEAT))
                elif ( self.getSerial() == packet.serial or
                     self.getSerial() == table.owner ):
                    if not table.seatPlayer(self, packet.serial, packet.seat):
                        packet.seat = -1
                    else:
                        packet.seat = game.getPlayer(packet.serial).seat
                    self.getUserInfo(packet.serial)
                    self.sendPacketVerbose(packet)
                else:
                    self.message("attempt to get seat for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))
                
            elif packet.type == PACKET_POKER_BUY_IN:
                if self.getSerial() == packet.serial:
                    self.service.autorefill(packet.serial)
                    if not table.buyInPlayer(self, packet.amount):
                        self.sendPacketVerbose(PacketPokerError(game_id = game.id,
                                                                serial = packet.serial,
                                                                other_type = PACKET_POKER_BUY_IN))
                else:
                    self.message("attempt to bring money for player %d by player %d" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_REBUY:
                if self.getSerial() == packet.serial:
                    self.service.autorefill(packet.serial)
                    if not table.rebuyPlayerRequest(self, packet.amount):
                        self.sendPacketVerbose(PacketPokerError(game_id = game.id,
                                                                serial = packet.serial,
                                                                other_type = PACKET_POKER_REBUY))
                else:
                    self.message("attempt to rebuy for player %d by player %d" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_CHAT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.chatPlayer(self, packet.serial, packet.message[:128])
                else:
                    self.message("attempt chat for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_PLAYER_LEAVE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.leavePlayer(self, packet.serial)
                else:
                    self.message("attempt to leave for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_SIT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.sitPlayer(self, packet.serial)
                else:
                    self.message("attempt to sit back for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))
                
            elif packet.type == PACKET_POKER_SIT_OUT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:

                    table.sitOutPlayer(self, packet.serial)
                else:
                    self.message("attempt to sit out for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))
                
            elif packet.type == PACKET_POKER_AUTO_BLIND_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.autoBlindAnte(self, packet.serial, True)
                else:
                    self.message("attempt to set auto blind/ante for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))
                
            elif packet.type == PACKET_POKER_NOAUTO_BLIND_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.autoBlindAnte(self, packet.serial, False)
                else:
                    self.message("attempt to set auto blind/ante for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))
            
            elif packet.type == PACKET_POKER_AUTO_MUCK:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    if table.game.getPlayer(packet.serial):
                        table.game.autoMuck(packet.serial, packet.auto_muck)
                else:
                    self.message("attempt to set auto muck for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() )             )
                
            elif packet.type == PACKET_POKER_MUCK_ACCEPT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.muckAccept(self, packet.serial)
                else:
                    self.message("attempt to accept muck for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))
                    
            elif packet.type == PACKET_POKER_MUCK_DENY:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.muckDeny(self, packet.serial)
                else:
                    self.message("attempt to deny muck for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))
                
            elif packet.type == PACKET_POKER_BLIND:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    game.blind(packet.serial)
                else:
                    self.message("attempt to pay the blind of player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_WAIT_BIG_BLIND:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    game.waitBigBlind(packet.serial)
                else:
                    self.message("attempt to wait for big blind of player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    game.ante(packet.serial)
                else:
                    self.message("attempt to pay the ante of player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_LOOK_CARDS:
                table.broadcast(packet)
                
            elif packet.type == PACKET_POKER_FOLD:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.fold(packet.serial)
                else:
                    self.message("attempt to fold player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_CALL:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.call(packet.serial)
                else:
                    self.message("attempt to call for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_RAISE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.callNraise(packet.serial, packet.amount)
                else:
                    self.message("attempt to raise for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_CHECK:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    
                    game.check(packet.serial)
                else:
                    self.message("attempt to check for player %d by player %d that is not the owner of the game" % ( packet.serial, self.getSerial() ))

            elif packet.type == PACKET_POKER_TABLE_QUIT:
                table.quitPlayer(self, self.getSerial())

            elif packet.type == PACKET_POKER_HAND_REPLAY:
                table.handReplay(self, packet.serial)

            table.update()

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

    def setRole(self, packet):
        if packet.roles not in PacketPokerRoles.ROLES:
            return PacketError(code = PacketPokerSetRole.UNKNOWN_ROLE,
                               message = "role %s is unknown (roles = %s)" % ( packet.roles, PacketPokerRoles.ROLES),
                               other_type = PACKET_POKER_SET_ROLE)

        if packet.roles in self.roles:
            return PacketError(code = PacketPokerSetRole.NOT_AVAILABLE,
                               message = "another client already has role %s" % packet.roles,
                               other_type = PACKET_POKER_SET_ROLE)
        self.roles.add(packet.roles)
        return PacketPokerRoles(serial = packet.serial,
                                roles = join(self.roles, " "))
            
    def getPlayerInfo(self):
        if self.user.isLogged():
            return PacketPokerPlayerInfo(serial = self.getSerial(),
                                         name = self.getName(),
                                         url = self.user.url,
                                         outfit = self.user.outfit)
        else:
            return PacketError(code = PacketPokerGetPlayerInfo.NOT_LOGGED,
                               message = "Not logged in",
                               other_type = PACKET_POKER_GET_PLAYER_INFO)
    
    def listPlayers(self, packet):
        table = self.service.getTable(packet.game_id)
        if table:
            players = table.listPlayers()
            self.sendPacketVerbose(PacketPokerPlayersList(game_id = packet.game_id,
                                                          players = players))
        
    def listTables(self, packet):
        packets = []
        for table in self.service.listTables(packet.string, self.getSerial()):
            packets.append(table.toPacket())
        ( players, tables ) = self.service.statsTables()
        self.sendPacketVerbose(PacketPokerTableList(players = players,
                                                    tables = tables,
                                                    packets = packets))

    def listHands(self, packet, serial):
        if packet.type != PACKET_POKER_HAND_SELECT_ALL:
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
        if packet.type != PACKET_POKER_HAND_SELECT_ALL:
            limit = " limit %d,%d " % ( start, count )
        else:
            limit = '';
        (total, hands) = self.service.listHands(select_list + where + limit, select_total + where)
        if packet.type == PACKET_POKER_HAND_SELECT_ALL:
            start = 0
            count = total
        self.sendPacketVerbose(PacketPokerHandList(string = packet.string,
                                                   start = start,
                                                   count = count,
                                                   hands = hands,
                                                   total = total))

    def createTable(self, packet):
        table = self.service.createTable(self.getSerial(), {
            "seats": packet.seats,
            "name": packet.name,
            "variant": packet.variant,
            "betting_structure": packet.betting_structure,
            "player_timeout": packet.player_timeout,
            "muck_timeout": packet.muck_timeout,
            "currency_serial": packet.currency_serial,
            "skin": packet.skin })
        if not table:
            self.sendPacket(PacketPokerTable())
        return table            

    def join(self, table):
        game = table.game
        
        self.tables[game.id] = table

        self.sendPacketVerbose(table.toPacket())
        self.sendPacketVerbose(PacketPokerBuyInLimits(game_id = game.id,
                                                      min = game.buyIn(),
                                                      max = game.maxBuyIn(),
                                                      best = game.bestBuyIn(),
                                                      rebuy_min = game.minMoney()))
        self.sendPacketVerbose(PacketPokerBatchMode(game_id = game.id))
        nochips = 0
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
                                                              money = player.money))
                if game.isSit(player.serial):
                    self.sendPacketVerbose(PacketPokerSit(game_id = game.id,
                                                          serial = player.serial))

        self.sendPacketVerbose(PacketPokerSeats(game_id = game.id,
                                                seats = game.seats()))
        if not game.isEndOrNull():
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
        game = table.game
        if game.addPlayer(serial, seat):
            player = game.getPlayer(serial)
            player.setUserData(DEFAULT_PLAYER_USER_DATA.copy())
        table.sendNewPlayerInformation(serial)
        
    def connectionLost(self, reason):
        if self.service.verbose:
            self.message("connection lost for %s/%d" % ( self.getName(), self.getSerial() ))
        for table in self.tables.values():
            table.disconnectPlayer(self, self.getSerial())
        self.logout()

    def getUserInfo(self, serial):
        self.service.autorefill(serial)
        self.sendPacketVerbose(self.service.getUserInfo(serial))

    def getPersonalInfo(self, serial):
        self.service.autorefill(serial)
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
            nochips = 0
            table.broadcast(PacketPokerPlayerChips(game_id = game.id,
                                                   serial = self.getSerial(),
                                                   bet = nochips,
                                                   money = player.money))
            return True
        else:
            return False
        
