#
# Copyright (C) 2007, 2008 Loic Dachary <loic@dachary.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
#
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
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
#  Johan Euphrosine <johan@mekensleep.com>
#  Cedric Pinson <cpinson@freesheep.org> (2003-2006)
#
from pprint import pprint
from twisted.internet import reactor, defer
from twisted.python.runtime import seconds

from pokernetwork.pokerclientpackets import *
from random import choice, uniform, randint
from time import time

class PokerAnimationPlayer:
    """A poker player seated at a poker table"""
    
    def __init__(self, *args, **kwargs):
        self.myself = kwargs.get('myself', False)
        self.animation_renderer = kwargs.get('animation_renderer', None)
        self.table = kwargs.get('table', None)
        self.verbose = self.table.verbose
        self.config = kwargs.get('config', None)
        self.serial = kwargs.get('serial', 0)
        self.seat = kwargs.get('seat', -1)
        self.sitin_flag = False
        self.timers = {}
        self.sitin_stack=[]
        self.player_bet_stack=[]
        self.last_end_round=0
        self.initStateAnimation()

    def init(self):
        pass
    
    def enable(self):
        self.initStateAnimation()
        self.resume()

    def initStateAnimation(self):
        pass
        
    def disable(self):
        self.suspend()
        
    def destroy(self):
        self.stopAll()
        del self.table

    def suspend(self):
        """Another part of the program wants to play with animations
        and asks us to suspend all running animations. The "resume"
        function may be called at a later time if we are allowed to
        keep handling animations."""
        self.is_suspended = True
        self.stopAll()

    def resume(self):
        """Run animations according to the state of the game. It is
        designed to be called after a suspend but will also work
        otherwise."""
        self.is_suspended = False

    def setPlayerDelay(self, delay):
        if not hasattr(self, 'table'): return
        game = self.table.game
        if self.table.scheduler and self.table.scheduler.protocol:
            protocol = self.table.scheduler.protocol
            protocol.setPlayerDelay(game, self.serial, delay)
        
    def callLater(self, delay, function, *args, **kwargs):
        self.callLaterTagged(function.__name__, delay, function, *args, **kwargs)
        
    def callLaterTagged(self, tag, delay, function, *args, **kwargs):
        timer = reactor.callLater(delay, function, *args, **kwargs)
        self.timers[tag] = timer

    def stopAll(self):
        """Stop the currently running animations and the scheduled animations.
        """
        for (function, timer) in self.timers.iteritems():
            if timer and timer.active():
                timer.cancel()
        self.timers = {}

    def endRound(self):
        self.last_end_round = seconds()

    def playerArrive(self):
        #print "player arrive run stand animation"
        self.enable()

    def isInPosition(self):
        return self.serial == self.table.game.getSerialInPosition()
    
    def maybeSitout(self):
        if self.sitin_flag is False:
            return 0
        
        self.sitin_flag = False
        return self.sitout()

    def sitout(self):
        return 0
    
    def setAnimationCallback(self, animation, callback):
        pass
    
    def manageSitinSitout(self):
        
        self.sitin_stack.pop(0) # remove the first element
        if len(self.sitin_stack) > 0:
            if self.sitin_stack[0] == "sitout":
                anim=self.maybeSitout()
                if anim != 0:
                    self.setAnimationCallback(anim, self.manageSitinSitout)
                else:
                    self.sitin_stack.pop()
            else:
                anim=self.maybeSitin()
                if anim != 0:
                    self.setAnimationCallback(anim, self.manageSitinSitout)
                else:
                    self.sitin_stack.pop()

    def sitoutAction(self):
        if len(self.sitin_stack) > 0:
            if self.sitin_stack[-1]!="sitout":
                if len(self.sitin_stack) > 1:
                    self.sitin_stack.pop()
                else:
                    self.sitin_stack.append("sitout")
        else:
            self.sitin_stack.append("sitout")
            self.sitin_stack.append("sitout")
            self.manageSitinSitout()

    def lookCards(self, packet):
        pass
    
    def sitinAction(self):
        if len(self.sitin_stack) > 0:
            if self.sitin_stack[-1]!="sitin":
                if len(self.sitin_stack) > 1:
                    self.sitin_stack.pop()
                else:
                    self.sitin_stack.append("sitin")
        else:
            self.sitin_stack.append("sitin")
            self.sitin_stack.append("sitin")
            self.manageSitinSitout()
            
    def maybeSitin(self):
        if self.sitin_flag is True:
            return 0

        self.sitin_flag = True
        return self.sitin()

    def sitin(self):
        return 0
    
    def check(self):
        pass
            
    def bet(self,game_id,chips):
        pass

    def timeoutWarning(self):
        pass

    def pot2player(self, packet):
        pass
    
    def fold(self, game_id):
        player = self.table.game.getPlayer(self.serial)
        if self.myself and player is not None and player.sit_out_next_turn:
            self.sitoutAction()

    def sitoutIfNotInGame(self):
        game = self.table.game
        if self.myself and not game.isInGame(self.serial):
            self.sitoutAction()
        
    def playerChips(self,chips):
        self.player_bet_stack = chips

    def chat(self, packet):
        pass

class PokerAnimationTable:

    def __init__(self, *args, **kwargs):
        self.stream = True # see PACKET_POKER_STREAM_MODE documentation
        self.game = None
        self.serial2player = {}
        self.config = kwargs["config"]
        self.settings = kwargs["settings"]
        self.animation_renderer = kwargs["animation_renderer"]
        self.verbose = kwargs["verbose"]
        self.scheduler = kwargs["scheduler"]
        self.PokerAnimationPlayerType = PokerAnimationPlayer
        self.dealer = None

    def createPlayer(self, protocol, packet):
        player = self.PokerAnimationPlayerType(table = self,
                                      myself = packet.serial == protocol.getSerial(),
                                      game_id = packet.game_id,
                                      serial = packet.serial,
                                      seat = packet.seat,
                                      config = self.config,
                                      animation_renderer = self.animation_renderer)
        return player

    def playerArrive(self, protocol, packet):
        if packet.game_id != self.game.id:
            print "PokerAnimationScheduler::playerArrive unexpected packet.game_id (%d) != self.game.id (%d) " % ( packet.game_id, self.game.id )

        if self.serial2player.has_key(packet.serial) == True:
            self.serial2player[packet.serial].enable()
            return

        player = self.createPlayer(protocol, packet)
        self.serial2player[packet.serial] = player
        player.init()
        player.playerArrive()

    def enable(self):
        for (serial, player) in self.serial2player.iteritems():
            player.enable()

    def disable(self):
        for (serial, player) in self.serial2player.iteritems():
            player.disable()
    
    def playerLeave(self, protocol, packet):
        self.serial2player[packet.serial].destroy()
        del self.serial2player[packet.serial]
        if self.dealer is not None:
            if self.seats[self.dealer] is not None and self.seats[self.dealer] == packet.serial:
                self.dealer = None

    def showdown(self, protocol, packet):
        if self.game.id != packet.game_id:
            print "PokerAnimationScheduler::showdown unexpected packet.game_id (%d) != self.game.id (%d) " % ( packet.game_id, self.game.id )

        serials = None
        serial2delta = None
        serial2share = None
        for frame in packet.showdown_stack:
            if frame['type'] == 'game_state':
                serial2delta = frame['serial2delta']
                serial2share = frame['serial2share']
            elif frame['type'] == 'resolve':
                serials = frame['serials']
                break

        if serials == None:
            print "showdown problem on game id %d" % self.game.id
            print packet
            
        delta_max = -1
        delta_min = 0x0FFFFFFF
        for serial in serials:
            delta = serial2delta[serial]
            if delta >= delta_max:
                delta_max = delta
            if delta_min >= delta:
                delta_min = delta
        for serial in serials:
            delta = serial2delta[serial]
            chips = 0
            if serial in serial2share.keys():
                chips = serial2share[serial]
            # a predicat check that winner are on the table when we use this packet but not the loosers
            # so it's possible to come on a table with this packet and serials (who loose) missing in the
            # serial list
            # to find a bug
            if serial not in self.serial2player.keys():
                continue
            
            player = self.serial2player[serial]
            player.showdownDelta(delta, serial2delta[serial] == delta_max, serial2delta[serial] == delta_min, chips)
            

    def endRound(self):
        for serial in self.serial2player.keys():
            self.serial2player[serial].endRound()

    def playersRemove(self):
        for serial in self.serial2player.keys():
            self.serial2player[serial].destroy()
            del self.serial2player[serial]
        self.serial2player = {}

    def tableQuit(self, protocol, packet):
        if self.verbose > 1:
            print "PokerAnimationScheduler: quit/destroy table %d" % packet.game_id
        self.game = None
        self.playersRemove()

    def getSeatIndex(self,serial):
        for i in range(len(self.seats)):
            if self.seats[i] == serial:
                return i
        return -1

    def tableSeats(self,protocol,packet):
        self.seats = packet.seats
        # check that all player are here, if there are players that have been removed
        # typically during a table switch we remove the player
        for serial in self.serial2player.keys():
            if serial not in self.seats:
                self.serial2player[serial].destroy()
                del self.serial2player[serial]

class PokerAnimationScheduler:
    """Packet receiver (see pokerpackets.py for the list of packets
    and their documentation). It is registered by
    poker3d.py:PokerClientFactory on a
    pokerclient.py:PokerClientProtocol instance talking to the server.
    """
    def __init__(self, *args, **kwargs):
        def sitinActionsCallback(protocol, packet):
            self.toPlayer(self.PokerAnimationPlayerType.sitinAction, packet)

        def sitoutActionsCallback(protocol, packet):
            self.toPlayer(self.PokerAnimationPlayerType.sitoutAction, packet)

        self.received2function = {
            PACKET_POKER_STREAM_MODE: lambda protocol, packet: self.setStream(packet, True),

            PACKET_POKER_BATCH_MODE: lambda protocol, packet: self.setStream(packet, False),

            PACKET_POKER_TABLE: self.table,

            PACKET_POKER_TABLE_QUIT: self.tableQuit,

            PACKET_POKER_TABLE_DESTROY: self.tableQuit,

            PACKET_POKER_PLAYER_ARRIVE: self.playerArrive,

            PACKET_POKER_PLAYER_LEAVE: self.playerLeave,

            PACKET_POKER_LOOK_CARDS: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.lookCards, packet, packet),

            PACKET_POKER_SEATS: self.tableSeats,

            PACKET_POKER_SIT: sitinActionsCallback,

            PACKET_POKER_SIT_REQUEST: sitinActionsCallback,

            PACKET_POKER_SIT_OUT: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.sitoutAction, packet),

            PACKET_POKER_SIT_OUT_NEXT_TURN: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.sitoutIfNotInGame, packet),

            PACKET_POKER_FOLD: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.fold, packet, packet.game_id),

            PACKET_POKER_CHECK: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.check, packet),

            PACKET_POKER_CHIPS_PLAYER2BET: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.bet, packet,packet.game_id,packet.chips),

            PACKET_POKER_TIMEOUT_WARNING: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.timeoutWarning, packet),

            PACKET_POKER_END_ROUND: self.endRound,

            PACKET_POKER_CHIPS_POT2PLAYER: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.pot2player, packet, packet),

            PACKET_POKER_SHOWDOWN: self.showdown,

            PACKET_POKER_PLAYER_CHIPS: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.playerChips, packet, packet.bet),

            PACKET_POKER_CHAT_WORD: lambda protocol, packet:
            self.toPlayer(self.PokerAnimationPlayerType.chat, packet, packet),
            }

        self.animation_renderer = kwargs.get("animation_renderer", None)
        self.config = kwargs.get("config", None)
        self.settings = kwargs.get("settings", None)
        if self.config:
            chips_values = self.config.headerGet("/sequence/chips")
            if not chips_values:
                raise UserWarning, "PokerAnimationScheduler: no /sequence/chips found in %s" % self.config.path
            self.chips_values = map(int, chips_values.split())
        else:
            self.chips_values = [1]
        self.verbose = self.settings and int(self.settings.headerGet("/settings/@verbose")) or 0
        self.protocol = None
        self.id2table = {}
        self.PokerAnimationPlayerType = PokerAnimationPlayer
        self.PokerAnimationTableType = PokerAnimationTable

    def setStream(self, packet, state):
        self.createTable(packet.game_id)
        self.id2table[packet.game_id].stream = state

    def playerArrive(self, protocol, packet):
        if not self.id2table.has_key(packet.game_id):
            print "PokerAnimationScheduler::playerArrive unknown game id (%d) " % packet.game_id
        self.id2table[packet.game_id].playerArrive(protocol, packet)
        
    def playerLeave(self, protocol, packet):
        if not self.id2table.has_key(packet.game_id):
            print "PokerAnimationScheduler::playerLeave unknown game id (%d) " % packet.game_id
        self.id2table[packet.game_id].playerLeave(protocol, packet)

    def createTable(self, id):
        if not self.id2table.has_key(id):
            self.id2table[id] = self.PokerAnimationTableType(scheduler = self,
                                                             config = self.config,
                                                             settings = self.settings,
                                                             animation_renderer = self.animation_renderer,
                                                             verbose = self.verbose)

    def table(self, protocol, packet):
        if self.verbose > 1:
            print "PokerAnimationScheduler: observing table %d" % packet.id
        self.createTable(packet.id)
        table = self.id2table[packet.id]
        table.game = self.protocol.getGame(packet.id)
        table.enable()
        for (id, table) in self.id2table.iteritems():
            if id != packet.id:
                table.disable()

    def tableQuit(self, protocol, packet):
        if not self.id2table.has_key(packet.game_id):
            print "PokerAnimationScheduler::tableQuit unknown game id (%d) " % packet.game_id
        self.id2table[packet.game_id].tableQuit(protocol, packet)
        del self.id2table[packet.game_id]

    def tableSeats(self, protocol, packet):
        if not self.id2table.has_key(packet.game_id):
            print "PokerAnimationScheduler::tableSeats unknown game id (%d) " % packet.game_id
        self.id2table[packet.game_id].tableSeats(protocol, packet)

    def showdown(self, protocol, packet):
        if not self.id2table.has_key(packet.game_id):
            print "PokerAnimationScheduler::showdown unknown game id (%d) " % packet.game_id
        self.id2table[packet.game_id].showdown(protocol, packet)
        
    def endRound(self,protocol,packet):
        self.id2table[packet.game_id].endRound()

    def suspend(self, packet):
        self.toPlayer(self.PokerAnimationPlayerType.suspend, packet)
        
    def resume(self, packet):
        self.toPlayer(self.PokerAnimationPlayerType.resume, packet)

    def toPlayer(self, function, packet, *args):
        """Call the "function" of the player object with serial equal
        to "serial" using the "*args" arguments. """
        if not self.id2table.has_key(packet.game_id):
            print "PokerAnimationScheduler::toPlayer unknown game id (%d) " % packet.game_id
        table = self.id2table[packet.game_id]
        player = table.serial2player.get(packet.serial, None)
        if player:
            return function(player, *args)
        else:
            return None
        
    def setProtocol(self, protocol):
        self.protocol = protocol
        for (type, function) in self.received2function.iteritems():
            protocol.registerHandler('current', type, function)
        #
        # In order to ease debugging we want the pokeranimation
        # callback to be called first so that the C++ side can
        # assume that there are no pending pointers to the animated
        # object.
        #
        tmp = protocol.callbacks['current'][PACKET_POKER_PLAYER_LEAVE]
        tmp.remove(self.playerLeave)
        tmp.insert(0, self.playerLeave)
        tmp = protocol.callbacks['current'][PACKET_POKER_TABLE_DESTROY]
        tmp.remove(self.tableQuit)
        tmp.insert(0, self.tableQuit)
        tmp = protocol.callbacks['current'][PACKET_POKER_TABLE_QUIT]
        tmp.remove(self.tableQuit)
        tmp.insert(0, self.tableQuit)
        tmp = protocol.callbacks['current'][PACKET_POKER_SEATS]
        tmp.remove(self.tableSeats)
        tmp.insert(0, self.tableSeats)

    def unsetProtocol(self):
        for (type, function) in self.received2function.iteritems():
            self.protocol.unregisterHandler('current', type, function)
            
