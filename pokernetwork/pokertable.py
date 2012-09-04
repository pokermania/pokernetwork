#
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2006, 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C)             2008 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C)             2009 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple 75004 Paris
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
#  Bradley M. Kuhn <bkuhn@ebb.org> (2008-)
#  Henry Precheur <henry@precheur.org> (2004)
#
import re

from twisted.internet import reactor
from twisted.python.runtime import seconds

from pokerengine.pokergame import PokerGameServer
from pokerengine import pokergame, pokertournament
from pokerengine.pokercards import PokerCards

from pokerpackets.networkpackets import *  # @UnusedWildImport
from pokernetwork.lockcheck import LockCheck

from pokernetwork import pokeravatar
from pokernetwork.pokerpacketizer import createCache, history2packets

from pokernetwork import log as network_log
log = network_log.get_child('pokertable')

class PokerAvatarCollection:

    log = log.get_child('PokerAvatarCollection')

    def __init__(self, prefix=''):
        self.serial2avatars = {}
        self.prefix = prefix

    def get(self, serial):
        return self.serial2avatars.get(serial, [])

    def set(self, serial, avatars):
        self.log.debug("set %d %s", serial, avatars)
        assert not serial in self.serial2avatars, \
            "setting %d with %s would override %s" % (
                serial,
                str(avatars),
                str(self.serial2avatars[serial])
            )
        self.serial2avatars[serial] = avatars[:]

    def add(self, serial, avatar):
        self.log.debug("add %d %s", serial, avatar)
        if serial not in self.serial2avatars:
            self.serial2avatars[serial] = []
        if avatar not in self.serial2avatars[serial]:
            self.serial2avatars[serial].append(avatar)

    def remove(self, serial, avatar):
        self.log.debug("remove %d %s", serial, avatar)
        assert avatar in self.serial2avatars[serial], "expected %d avatar in %s" % (
            serial,
            str(self.serial2avatars[serial])
        )
        self.serial2avatars[serial].remove(avatar)
        if len(self.serial2avatars[serial]) <= 0:
            del self.serial2avatars[serial]

    def values(self):
        return self.serial2avatars.values()

    def itervalues(self):
        return self.serial2avatars.itervalues()


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
    
    TIMEOUT_DELAY_COMPENSATION = 2

    log = log.get_child('PokerTable')
    
    def __init__(self, factory, id=0, description=None):
        self.log = PokerTable.log.get_instance(self, refs=[
            ('Game', self, lambda table: table.game.id),
            ('Hand', self, lambda table: table.game.hand_serial if table.game.hand_serial > 1 else None)
        ])
        self.factory = factory
        settings = self.factory.settings
        self.game = PokerGameServer("poker.%s.xml", factory.dirs)
        self.game.prefix = "[Server]"
        self.history_index = 0
        predefined_decks = settings.headerGetList("/server/decks/deck")
        if predefined_decks:
            self.game.shuffler = PokerPredefinedDecks(map(
                lambda deck: self.game.eval.string2card(deck.split()),
                predefined_decks
            ))
        self.observers = []
        self.waiting = []
        self.game.id = id
        self.game.name = description["name"]
        self.game.setVariant(description["variant"])
        self.game.setBettingStructure(description["betting_structure"])
        self.game.setMaxPlayers(int(description["seats"]))
        self.game.forced_dealer_seat = int(description.get("forced_dealer_seat", -1))
        self.game.registerCallback(self._gameCallbackTourneyEndTurn)
        self.game.registerCallback(self._gameCallbackTourneyUpdateStats)
        self.skin = description.get("skin", "default")
        self.currency_serial = int(description.get("currency_serial", 0))
        self.playerTimeout = int(description.get("player_timeout", 60))
        self.muckTimeout = int(description.get("muck_timeout", 5))
        self.transient = 'transient' in description
        self.tourney = description.get("tourney", None)

        # max_missed_round can be configured on a per table basis, which
        # overrides the server-wide default
        self.max_missed_round = int(description.get("max_missed_round",factory.getMissedRoundMax()))

        self.delays = settings.headerGetProperties("/server/delays")[0]
        self.autodeal = settings.headerGet("/server/@autodeal") == "yes"
        self.autodeal_temporary = settings.headerGet("/server/users/@autodeal_temporary") == 'yes'
        self.cache = createCache()
        self.owner = 0
        self.avatar_collection = PokerAvatarCollection("Table%d" % id)
        self.timer_info = {
            "playerTimeout": None,
            "playerTimeoutSerial": 0,
            "playerTimeoutTime": None,
            "muckTimeout": None,
        }
        self.timeout_policy = "sitOut"
        self.previous_dealer = -1
        self.game_delay = {
            "start": 0,
            "delay": 0,
        }
        self.update_recursion = False

        # Lock Checker
        self._initLockCheck()

    def _warnLock(self):
        self._lock_check_locked = True
        game_id = str(self.game.id) if hasattr(self, 'game') else '?'
        hand_serial = str(self.game.hand_serial) if hasattr(self, 'game') else '?'
        self.log.warn("Table is locked! game_id: %s, hand_serial: %s", game_id, hand_serial)

    def isLocked(self):
        return self._lock_check_locked

    def isValid(self):
        """Returns true if the table has a factory."""
        return hasattr(self, "factory")

    def destroy(self):
        """Destroys the table and deletes it from factory.tables.Also informs connected avatars."""
        self.log.debug("destroy table %d", self.game.id)
        #
        # cancel DealTimeout timer
        self.cancelDealTimeout()
        #
        # cancel PlayerTimeout timers
        self.cancelPlayerTimers()
        #
        # destroy factory table
        if self.transient:
            self.factory.destroyTable(self.game.id)
        #
        # broadcast TableDestroy to connected avatars
        self.broadcast(PacketPokerTableDestroy(game_id=self.game.id))
        #
        # remove table from avatars
        for avatars in self.avatar_collection.itervalues():
            for avatar in avatars:
                del avatar.tables[self.game.id]
        #
        # remove table from oberservers
        for observer in self.observers:
            del observer.tables[self.game.id]
        #
        # cut connection from and to factory
        self.factory.deleteTable(self)
        del self.factory
        #
        # kill lock check timer
        self._stopLockCheck()

    def getName(self, serial):
        """Returns the name to the given serial"""
        avatars = self.avatar_collection.get(serial)
        return avatars[0].getName() if avatars else self.factory.getName(serial)

    def getPlayerInfo(self, serial):
        """Returns a PacketPlayerInfo to the given serial"""
        avatars = self.avatar_collection.get(serial)
        return avatars[0].getPlayerInfo() if avatars and avatars[0].user.isLogged() else self.factory.getPlayerInfo(serial)

    def listPlayers(self):
        """Returns a list of names of all Players in game"""
        return [
                (self.getName(serial), self.game.getPlayerMoney(serial), 0,)
                for serial in self.game.serialsAll()
        ]

    def cancelDealTimeout(self):
        """If there is a dealTimeout timer in timer_info cancel and delete it"""
        info = self.timer_info
        if 'dealTimeout' in info:
            if info["dealTimeout"].active():
                info["dealTimeout"].cancel()
            del info["dealTimeout"]

    def beginTurn(self):
        self._startLockCheck()
        self.cancelDealTimeout()
        if self.game.isEndOrNull():
            self.historyReset()
            hand_serial = self.factory.getHandSerial()
            self.log.debug("Dealing hand %s/%d", self.game.name, hand_serial)
            self.game.setTime(seconds())
            self.game.beginTurn(hand_serial)
            for player in self.game.playersAll():
                player.getUserData()['ready'] = True

    def historyReset(self):
        self.history_index = 0
        self.cache = createCache()

    def toPacket(self):
        return PacketPokerTable(
            id=self.game.id,
            name = self.game.name,
            variant = self.game.variant,
            betting_structure = self.game.betting_structure,
            seats = self.game.max_players,
            players = self.game.allCount(),
            hands_per_hour = self.game.stats["hands_per_hour"],
            average_pot = self.game.stats["average_pot"],
            percent_flop = self.game.stats["percent_flop"],
            player_timeout = self.playerTimeout,
            muck_timeout = self.muckTimeout,
            observers = len(self.observers),
            waiting = len(self.waiting),
            skin = self.skin,
            currency_serial = self.currency_serial,
            tourney_serial = self.tourney and self.tourney.serial or 0
        )

    def broadcast(self, packets):
        """Broadcast a list of packets to all connected avatars on this table."""
        if type(packets) is not list:
            packets = [packets]
        for packet in packets:
            keys = self.game.serial2player.keys()
            self.log.debug("broadcast%s %s ", keys, packet)
            for serial in keys:
                #
                # player may be in game but disconnected.
                for avatar in self.avatar_collection.get(serial):
                    avatar.sendPacket(self.private2public(packet, serial))
            for avatar in self.observers:
                avatar.sendPacket(self.private2public(packet, 0))

        self.factory.eventTable(self)

    def private2public(self, packet, serial):
        #
        # cards private to each player are shown only to the player
        if packet.type == PACKET_POKER_PLAYER_CARDS and packet.serial != serial:
            return PacketPokerPlayerCards(
                game_id = packet.game_id,
                serial = packet.serial,
                cards = PokerCards(packet.cards).tolist(False)
            )
        else:
            return packet
    
    def syncDatabase(self):
        updates = {}
        serial2rake = {}
        reset_bet = False
        for event in self.game.historyGet()[self.history_index:]:
            event_type = event[0]
            if event_type == "game":
                pass

            elif event_type == "wait_for":
                pass

            elif event_type == "rebuy":
                pass

            elif event_type == "player_list":
                pass

            elif event_type == "round":
                pass

            elif event_type == "showdown":
                pass

            elif event_type == "rake":
                serial2rake = event[2]

            elif event_type == "muck":
                pass

            elif event_type == "position":
                pass

            elif event_type == "blind_request":
                pass

            elif event_type == "wait_blind":
                pass

            elif event_type == "blind":
                serial, amount, dead = event[1:]
                if serial not in updates:
                    updates[serial] = 0
                updates[serial] -= amount + dead

            elif event_type == "ante_request":
                pass

            elif event_type == "ante":
                serial, amount = event[1:]
                if serial not in updates:
                    updates[serial] = 0
                updates[serial] -= amount

            elif event_type == "all-in":
                pass

            elif event_type == "call":
                serial, amount = event[1:]
                if serial not in updates:
                    updates[serial] = 0
                updates[serial] -= amount

            elif event_type == "check":
                pass

            elif event_type == "fold":
                pass

            elif event_type == "raise":
                serial, amount = event[1:]
                if serial not in updates:
                    updates[serial] = 0
                updates[serial] -= amount

            elif event_type == "canceled":
                serial, amount = event[1:]
                if serial > 0 and amount > 0:
                    if serial not in updates:
                        updates[serial] = 0
                    updates[serial] += amount

            elif event_type == "end":
                showdown_stack = event[2]
                game_state = showdown_stack[0]
                for (serial, share) in game_state['serial2share'].iteritems():
                    if serial not in updates:
                        updates[serial] = 0
                    updates[serial] += share
                reset_bet = True

            elif event_type == "sitOut":
                pass

            elif event_type == "sit":
                pass

            elif event_type == "leave":
                pass

            elif event_type == "finish":
                hand_serial = event[1]
                self.factory.saveHand(self.compressedHistory(self.game.historyGet()), hand_serial)
                self.factory.updateTableStats(self.game, len(self.observers), len(self.waiting))
                transient = 1 if self.transient else 0
                self.factory.databaseEvent(event=PacketPokerMonitorEvent.HAND, param1=hand_serial, param2=transient, param3=self.game.id)
            else:
                self.log.warn("syncDatabase: unknown history type %s", event_type)

        for (serial, amount) in updates.iteritems():
            self.factory.updatePlayerMoney(serial, self.game.id, amount)

        for (serial, rake) in serial2rake.iteritems():
            self.factory.updatePlayerRake(self.currency_serial, serial, rake)

        if reset_bet:
            self.factory.resetBet(self.game.id)

    def compressedHistory(self, history):
        new_history = []
        cached_pockets = None
        cached_board = None
        for event in history:
            event_type = event[0]
            if event_type in (
                'all-in', 'wait_for','blind_request',
                'muck','finish', 'leave','rebuy'
            ):
                pass
            
            elif event_type == 'game':
                new_history.append(event)
                
            elif event_type == 'round':
                name, board, pockets = event[1:]
                if pockets != cached_pockets: cached_pockets = pockets
                else: pockets = None
                if board != cached_board: cached_board = board
                else: board = None
                new_history.append((event_type, name, board, pockets))
                
            elif event_type == 'showdown':
                board, pockets = event[1:]
                if pockets != cached_pockets: cached_pockets = pockets
                else: pockets = None
                if board != cached_board: cached_board = board
                else: board = None
                new_history.append((event_type, board, pockets))
                
            elif event_type in (
                'call', 'check', 'fold',
                'raise', 'canceled', 'position',
                'blind', 'ante', 'player_list',
                'rake', 'end', 'sitOut',
            ):
                new_history.append(event)
                
            else:
                self.log.warn("compressedHistory: unknown history type %s ", event_type)

        return new_history

    def delayedActions(self):
        for event in self.game.historyGet()[self.history_index:]:
            event_type = event[0]
            if event_type == "game":
                self.game_delay = {
                    "start": seconds(),
                    "delay": float(self.delays["autodeal"])
                }
            elif event_type in ('round', 'position', 'showdown', 'finish'):
                self.game_delay["delay"] += float(self.delays[event_type])
                self.log.debug("delayedActions: game estimated duration is now %s "
                    "and is running since %.02f seconds",
                    self.game_delay["delay"],
                    seconds() - self.game_delay["start"],
                )

            elif event_type == "leave":
                quitters = event[1]
                for serial, seat in quitters:  # @UnusedVariable
                    self.factory.leavePlayer(serial, self.game.id, self.currency_serial)
                    for avatar in self.avatar_collection.get(serial)[:]:
                        self.seated2observer(avatar, serial)

    def cashGame_kickPlayerSittingOutTooLong(self, historyToSearch):
        if self.tourney:
            return
        handIsFinished = False
        # Go through the history backwards, stopping at
        # self.history_index, since we expect finish to be at the end if
        # it is there, and we don't want to consider previously reduced
        # history.
        for event in reversed(historyToSearch):
            if event[0] == "finish":
                handIsFinished = True
                break
        if handIsFinished:
            for player in self.game.playersAll():
                if player.getMissedRoundCount() >= self.max_missed_round:
                    self.kickPlayer(player.serial)

    def tourneyEndTurn(self):
        if not self.tourney:
            return
        for event in self.game.historyGet()[self.history_index:]:
            event_type = event[0]
            if event_type == "end":
                self.factory.tourneyEndTurn(self.tourney, self.game.id)

    def tourneyUpdateStats(self):
        if self.tourney:
            self.factory.tourneyUpdateStats(self.tourney, self.game.id)

    def autoDeal(self):
        self.cancelDealTimeout()
        if not self.allReadyToPlay():
            #
            # All avatars that fail to send a PokerReadyToPlay packet
            # within imposed delays after sending a PokerProcessingHand
            # are marked as bugous and their next PokerProcessingHand
            # request will be ignored.
            #
            for player in self.game.playersAll():
                if player.getUserData()['ready'] == False:
                    for avatar in self.avatar_collection.get(player.serial):
                        self.log.warn("Player %d marked as having a bugous "
                            "PokerProcessingHand protocol",
                            player.serial
                        )
                        avatar.bugous_processing_hand = True

        self.beginTurn()
        self.update()

    def autoDealCheck(self, autodeal_check, delta):
        self.log.debug("autoDealCheck")
        self.cancelDealTimeout()
        if autodeal_check > delta:
            self.log.debug("Autodeal for %d scheduled in %f seconds", self.game.id, delta)
            self.timer_info["dealTimeout"] = reactor.callLater(delta, self.autoDeal)
            return
        #
        # Issue a poker message to all players that are ready
        # to play.
        #
        serials = []
        for player in self.game.playersAll():
            if player.getUserData()['ready'] == True:
                serials.append(player.serial)
        if serials:
            self.broadcastMessage(PacketPokerMessage, "Waiting for players.\nNext hand will be dealt shortly.\n(maximum %d seconds)" % int(delta), serials)
        self.log.debug("AutodealCheck(2) for %d scheduled in %f seconds", self.game.id, delta)
        self.timer_info["dealTimeout"] = reactor.callLater(autodeal_check, self.autoDealCheck, autodeal_check, delta - autodeal_check)

    def broadcastMessage(self, message_type, message, serials=None):
        if serials == None:
            serials = self.game.serialsAll()
        connected_serials = [serial for serial in serials if self.avatar_collection.get(serial)]
        if not connected_serials:
            return False
        packet = message_type(game_id = self.game.id, string = message)
        for serial in connected_serials:
            for avatar in self.avatar_collection.get(serial):
                avatar.sendPacket(packet)
        return True

    def scheduleAutoDeal(self):
        self.cancelDealTimeout()
        if self.factory.shutting_down:
            self.log.debug("Not autodealing because server is shutting down")
            return False
        if not self.autodeal:
            self.log.debug("No autodeal")
            return False
        if self.isRunning():
            self.log.debug("Not autodealing %d because game is running", self.game.id)
            return False
        if self.game.state == pokergame.GAME_STATE_MUCK:
            self.log.debug("Not autodealing %d because game is in muck state", self.game.id)
            return False
        if self.game.sitCount() < 2:
            self.log.debug("Not autodealing %d because less than 2 players willing to play", self.game.id)
            return False
        if self.game.isTournament():
            if self.tourney:
                if self.tourney.state != pokertournament.TOURNAMENT_STATE_RUNNING:
                    self.log.debug("Not autodealing %d because in tournament state %s", self.game.id, self.tourney.state)
                    if self.tourney.state == pokertournament.TOURNAMENT_STATE_BREAK_WAIT:
                        self.broadcastMessage(PacketPokerGameMessage, "Tournament will break when the other tables finish their hand")
                    return False
        elif not self.autodeal_temporary:
            #
            # Do not auto deal a table where there are only temporary
            # users (i.e. bots)
            #
            only_temporary_users = True
            for serial in self.game.serialsSit():
                if not self.factory.isTemporaryUser(serial):
                    only_temporary_users = False
                    break
            if only_temporary_users:
                self.log.debug("Not autodealing because players are categorized as temporary")
                return False

        delay = self.game_delay["delay"]
        if not self.allReadyToPlay() and delay > 0:
            delta = (self.game_delay["start"] + delay) - seconds()
            autodeal_max = float(self.delays.get("autodeal_max", 120))
            delta = min(autodeal_max, max(0, delta))
            self.game_delay["delay"] = (seconds() - self.game_delay["start"]) + delta
        elif self.transient:
            delta = int(self.delays.get("autodeal_tournament_min", 15))
            if seconds() - self.game_delay["start"] > delta:
                delta = 0
        else:
            delta = 0
        self.log.debug("AutodealCheck scheduled in %f seconds", delta)
        autodeal_check = max(0.01, float(self.delays.get("autodeal_check", 15)))
        self.timer_info["dealTimeout"] = reactor.callLater(min(autodeal_check, delta), self.autoDealCheck, autodeal_check, delta)
        return True

    def updatePlayerUserData(self, serial, key, value):
        if self.game.isSeated(serial):
            player = self.game.getPlayer(serial)
            user_data = player.getUserData()
            if user_data[key] != value:
                user_data[key] = value
                self.update()

    def allReadyToPlay(self):
        status = True
        notready = []
        for player in self.game.playersAll():
            if player.getUserData()['ready'] == False:
                notready.append(str(player.serial))
                status = False
        if notready:
            self.log.debug("allReadyToPlay: waiting for %s", ",".join(notready))
        return status

    def readyToPlay(self, serial):
        self.updatePlayerUserData(serial, 'ready', True)
        return PacketAck()

    def processingHand(self, serial):
        self.updatePlayerUserData(serial, 'ready', False)
        return PacketAck()

    def update(self):
        if self.update_recursion:
            self.log.warn("unexpected recursion (ignored)", exc_info=1)
            return "recurse"
        self.update_recursion = True
        if not self.isValid():
            return "not valid"
        
        history = self.game.historyGet()
        history_len = len(history)
        history_tail = history[self.history_index:]

        try:
            self.updateTimers(history_tail)
            packets, self.previous_dealer, errors = history2packets(history_tail, self.game.id, self.previous_dealer, self.cache)
            for error in errors: self.log.warn("%s", error)
            self.syncDatabase()
            self.delayedActions()
            if len(packets) > 0:
                self.broadcast(packets)
            self.tourneyEndTurn()
            if self.isValid():
                self.cashGame_kickPlayerSittingOutTooLong(history_tail)
                self.scheduleAutoDeal()
        finally:
            if history_len != len(history):
                self.log.error("%s length changed from %d to %d (i.e. %s was added)",
                    history,
                    history_len,
                    len(history),
                    history[history_len:]
                )
            if self.game.historyCanBeReduced():
                try:
                    self.game.historyReduce()
                except Exception:
                    self.log.error('history reduce error', exc_info=1)
            self.history_index = len(self.game.historyGet())
            self.update_recursion = False
        return "ok"

    def handReplay(self, avatar, hand):
        history = self.factory.loadHand(hand)
        if not history:
            return
        event_type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips = history[0]  # @UnusedVariable
        for player in self.game.playersAll():
            avatar.sendPacketVerbose(PacketPokerPlayerLeave(
                game_id = self.game.id,
                serial = player.serial,
                seat = player.seat
            ))
        self.game.reset()
        self.game.name = "*REPLAY*"
        self.game.setVariant(variant)
        self.game.setBettingStructure(betting_structure)
        self.game.setTime(time)
        self.game.setHandsCount(hands_count)
        self.game.setLevel(level)
        self.game.hand_serial = hand
        for serial in player_list:
            self.game.addPlayer(serial)
            self.game.getPlayer(serial).money = serial2chips[serial]
            self.game.sit(serial)
        if self.isJoined(avatar):
            avatar.join(self, reason=PacketPokerTable.REASON_HAND_REPLAY)
        else:
            self.joinPlayer(avatar, avatar.getSerial(), reason = PacketPokerTable.REASON_HAND_REPLAY)
        serial = avatar.getSerial()
        cache = createCache()
        packets, previous_dealer, errors = history2packets(history, self.game.id, -1, cache) #@UnusedVariable
        for packet in packets:
            if packet.type == PACKET_POKER_PLAYER_CARDS and packet.serial == serial:
                packet.cards = cache["pockets"][serial].toRawList()
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                continue
            avatar.sendPacketVerbose(packet)

    def isJoined(self, avatar):
        serial = avatar.getSerial()
        return avatar in self.observers or avatar in self.avatar_collection.get(serial)

    def isSeated(self, avatar):
        return self.isJoined(avatar) and self.game.isSeated(avatar.getSerial())

    def isSit(self, avatar):
        return self.isSeated(avatar) and self.game.isSit(avatar.getSerial())

    def isSerialObserver(self, serial):
        return serial in [avatar.getSerial() for avatar in self.observers]

    def isOpen(self):
        return self.game.is_open

    def isRunning(self):
        return self.game.isRunning()

    def seated2observer(self, avatar, serial):
        if avatar.getSerial() != serial:
            self.log.warn("pokertable.seated2observer: avatar.user.serial (%d) "
                "doesn't match serial argument (%d)",
                avatar.getSerial(),
                serial
            )
        self.avatar_collection.remove(serial, avatar)
        self.observers.append(avatar)

    def observer2seated(self, avatar):
        self.observers.remove(avatar)
        self.avatar_collection.add(avatar.getSerial(), avatar)

    def quitPlayer(self, avatar, serial):
        if self.isSit(avatar):
            if self.isOpen():
                self.game.sitOutNextTurn(serial)
            self.game.autoPlayer(serial)
        self.update()
        if self.isSeated(avatar):
            #
            # If not on a closed table, stand up
            #
            if self.isOpen():
                if avatar.removePlayer(self, serial):
                    self.seated2observer(avatar, serial)
                    self.factory.leavePlayer(serial, self.game.id, self.currency_serial)
                    self.factory.updateTableStats(self.game, len(self.observers), len(self.waiting))
                else:
                    self.update()
            else:
                avatar.log.inform("cannot quit a closed table, request ignored")
                return False

        if self.isJoined(avatar):
            #
            # The player is no longer connected to the table
            #
            self.destroyPlayer(avatar, serial)

        return True

    def kickPlayer(self, serial):
        player = self.game.getPlayer(serial)
        seat = player and player.seat

        if not self.game.removePlayer(serial):
            self.log.warn("kickPlayer did not succeed in removing player %d from game %d",
                serial,
                self.game.id
            )
            return

        self.factory.leavePlayer(serial, self.game.id, self.currency_serial)
        self.factory.updateTableStats(self.game, len(self.observers), len(self.waiting))

        for avatar in self.avatar_collection.get(serial)[:]:
            self.seated2observer(avatar, serial)

        self.broadcast(PacketPokerPlayerLeave(
            game_id = self.game.id,
            serial = serial,
            seat = seat
        ))

    def disconnectPlayer(self, avatar, serial):
        if self.isSeated(avatar):
            self.game.getPlayer(serial).getUserData()['ready'] = True
            if self.isOpen():
                #
                # If not on a closed table, stand up.
                #
                if avatar.removePlayer(self, serial):
                    self.seated2observer(avatar, serial)
                    self.factory.leavePlayer(serial, self.game.id, self.currency_serial)
                    self.factory.updateTableStats(self.game, len(self.observers), len(self.waiting))
                else:
                    self.update()
            else:
                #
                # If on a closed table, the player
                # will stay at the table, he does not
                # have the option to leave.
                #
                pass

        if self.isJoined(avatar):
            #
            # The player is no longer connected to the table
            #
            self.destroyPlayer(avatar, serial)

        return True

    def leavePlayer(self, avatar, serial):
        if self.isSit(avatar):
            if self.isOpen():
                self.game.sitOutNextTurn(serial)
            self.game.autoPlayer(serial)
        self.update()
        if self.isSeated(avatar):
            #
            # If not on a closed table, stand up
            #
            if self.isOpen():
                if avatar.removePlayer(self, serial):
                    self.seated2observer(avatar, serial)
                    self.factory.leavePlayer(serial, self.game.id, self.currency_serial)
                    self.factory.updateTableStats(self.game, len(self.observers), len(self.waiting))
                else:
                    self.update()
            else:
                self.log.warn("cannot leave a closed table")
                avatar.sendPacketVerbose(PacketPokerError(
                    game_id = self.game.id,
                    serial = serial,
                    other_type = PACKET_POKER_PLAYER_LEAVE,
                    code = PacketPokerPlayerLeave.TOURNEY,
                    message = "Cannot leave tournament table"
                ))
                return False

        return True

    def movePlayer(self, avatars, serial, to_game_id, reason=""):
        avatars = avatars[:]
        #
        # We are safe because called from within the server under
        # controlled circumstances.
        #

        money = self.game.serial2player[serial].money
        name = self.game.serial2player[serial].name
        
        sit_out = self.movePlayerFrom(serial, to_game_id)
        for avatar in avatars:
            self.destroyPlayer(avatar, serial)

        other_table = self.factory.getTable(to_game_id)
        for avatar in avatars:
            other_table.observers.append(avatar)
            other_table.observer2seated(avatar)

        money_check = self.factory.movePlayer(serial, self.game.id, to_game_id)
        if money_check != money:
            self.log.warn("movePlayer: player %d money %d in database, %d in memory", serial, money_check, money)

        for avatar in avatars:
            avatar.join(other_table, reason=reason)
        other_table.movePlayerTo(serial, name, money, sit_out)
        other_table.sendNewPlayerInformation(serial)
        if not other_table.update_recursion:
            other_table.scheduleAutoDeal()
        self.log.debug("player %d moved from table %d to table %d", serial, self.game.id, to_game_id)

    def sendNewPlayerInformation(self, serial):
        packets = self.newPlayerInformation(serial)
        self.broadcast(packets)

    def newPlayerInformation(self, serial):
        player_info = self.getPlayerInfo(serial)
        player = self.game.getPlayer(serial)
        nochips = 0
        packets = []
        packets.append(PacketPokerPlayerArrive(
            game_id = self.game.id,
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
            seat = player.seat
        ))
        if self.factory.has_ladder:
            packet = self.factory.getLadder(self.game.id, self.currency_serial, player.serial)
            if packet.type == PACKET_POKER_PLAYER_STATS:
                packets.append(packet)
        packets.append(PacketPokerSeats(game_id = self.game.id, seats = self.game.seats()))
        packets.append(PacketPokerPlayerChips(
            game_id = self.game.id,
            serial = serial,
            bet = nochips,
            money = self.game.getPlayer(serial).money
        ))
        return packets

    def movePlayerTo(self, serial, name, money, sit_out):
        self.game.open()
        self.game.addPlayer(serial,name=name)
        player = self.game.getPlayer(serial)
        player.setUserData(pokeravatar.DEFAULT_PLAYER_USER_DATA.copy())
        player.money = money
        player.buy_in_payed = True
        self.game.sit(serial)
        self.game.autoBlindAnte(serial)
        if sit_out:
            self.game.sitOut(serial)
        self.game.close()

    def movePlayerFrom(self, serial, to_game_id):
        game = self.game
        player = game.getPlayer(serial)
        self.broadcast(PacketPokerTableMove(
            game_id = game.id,
            serial = serial,
            to_game_id = to_game_id,
            seat = player.seat)
        )
        sit_out = game.isSitOut(serial)
        game.removePlayer(serial)
        return sit_out

    def possibleObserverLoggedIn(self, avatar, serial):
        if not self.game.getPlayer(serial):
            return False
        self.observer2seated(avatar)
        self.game.comeBack(serial)
        return True

    def joinPlayer(self, avatar, serial, reason=""):
        #
        # Nothing to be done except sending all packets.
        # Useful in disconnected mode to resume a session.
        if self.isJoined(avatar):
            avatar.join(self, reason=reason)
            return True
        #
        # Next, test to see if we have reached the server-wide maximum for
        # seated/observing players.
        if not self.game.isSeated(avatar.getSerial()) and self.factory.joinedCountReachedMax():
            self.log.crit("joinPlayer: %d cannot join game %d because the server is full", serial, self.game.id)
            avatar.sendPacketVerbose(PacketPokerError(
                game_id = self.game.id,
                serial = serial,
                other_type = PACKET_POKER_TABLE_JOIN,
                code = PacketPokerTableJoin.FULL,
                message = "This server has too many seated players and observers."
            ))
            return False
        #
        # Next, test to see if joining this table will cause the avatar to
        # exceed the maximum permitted by the server.
        if len(avatar.tables) >= self.factory.simultaneous:
            self.log.crit("joinPlayer: %d seated at %d tables (max %d)" % (serial, len(avatar.tables), self.factory.simultaneous))
            return False

        #
        # Player is now an observer, unless he is seated
        # at the table.
        self.factory.joinedCountIncrease()
        if not self.game.isSeated(avatar.getSerial()):
            self.observers.append(avatar)
        else:
            self.avatar_collection.add(serial, avatar)
        #
        # If it turns out that the player is seated
        # at the table already, presumably because he
        # was previously disconnected from a tournament
        # or an ongoing game.
        came_back = False
        if self.isSeated(avatar):
            #
            # Sit back immediately, as if we just seated
            came_back = self.game.comeBack(serial)
        avatar.join(self, reason=reason)

        if came_back:
            #
            # it does not hurt to re-sit the avatar
            # but is needed for other clients to notice
            # the arrival
            avatar.sitPlayer(self, serial)

        return True

    def seatPlayer(self, avatar, serial, seat):
        if not self.isJoined(avatar):
            self.log.error("player %d can't seat before joining", serial)
            return False
        if self.isSeated(avatar):
            self.log.inform("player %d is already seated", serial)
            return False
        if not self.game.canAddPlayer(serial):
            self.log.warn("table refuses to seat player %d", serial)
            return False
        if seat != -1 and seat not in self.game.seats_left:
            self.log.warn("table refuses to seat player %d at seat %d", serial, seat)
            return False

        amount = self.game.buyIn() if self.transient else 0
        minimum_amount = (self.currency_serial, self.game.buyIn())
        
        if not self.factory.seatPlayer(serial, self.game.id, amount, minimum_amount):
            return False

        self.observer2seated(avatar)

        avatar.addPlayer(self, seat)
        if amount > 0:
            avatar.setMoney(self, amount)

        self.factory.updateTableStats(self.game, len(self.observers), len(self.waiting))
        return True

    def sitOutPlayer(self, avatar, serial):
        if not self.isSeated(avatar):
            self.log.warn("player %d can't sit out before getting a seat", serial)
            return False
        #
        # silently do nothing if already sit out
        if not self.isSit(avatar):
            return True
        avatar.sitOutPlayer(self, serial)
        return True

    def chatPlayer(self, avatar, serial, message):
        if not self.isJoined(avatar):
            self.log.error("player %d can't chat before joining", serial)
            return False
        message = self.chatFilter(message)
        self.broadcast(PacketPokerChat(
            game_id = self.game.id,
            serial = serial,
            message = message+"\n"
        ))
        self.factory.chatMessageArchive(serial, self.game.id, message)

    def chatFilter(self, message):
        return self.factory.chat_filter.sub('poker', message) \
            if self.factory.chat_filter \
            else message

    def autoBlindAnte(self, avatar, serial, auto):
        if not self.isSeated(avatar):
            self.log.warn("player %d can't set auto blind/ante before getting a seat", serial)
            return False
        return avatar.autoBlindAnte(self, serial, auto)

    def muckAccept(self, avatar, serial):
        if not self.isSeated(avatar):
            self.log.warn("player %d can't accept muck before getting a seat", serial)
            return False
        return self.game.muck(serial, want_to_muck=True)

    def muckDeny(self, avatar, serial):
        if not self.isSeated(avatar):
            self.log.warn("player %d can't deny muck before getting a seat", serial)
            return False
        return self.game.muck(serial, want_to_muck=False)

    def sitPlayer(self, avatar, serial):
        if not self.isSeated(avatar):
            self.log.warn("player %d can't sit before getting a seat", serial)
            return False
        return avatar.sitPlayer(self, serial)

    def destroyPlayer(self, avatar, serial):
        self.factory.joinedCountDecrease()
        if avatar in self.observers:
            self.observers.remove(avatar)
        else:
            self.avatar_collection.remove(serial, avatar)
        del avatar.tables[self.game.id]

    def buyInPlayer(self, avatar, amount):
        if not self.isSeated(avatar):
            self.log.warn("player %d can't bring money to a table before getting a seat", avatar.getSerial())
            return False

        if avatar.getSerial() in self.game.serialsPlaying():
            self.log.warn("player %d can't bring money while participating in a hand", avatar.getSerial())
            return False

        if self.transient:
            self.log.warn("player %d can't bring money to a transient table", avatar.getSerial())
            return False

        player = self.game.getPlayer(avatar.getSerial())
        if player and player.isBuyInPayed():
            self.log.warn("player %d already payed the buy-in", avatar.getSerial())
            return False

        amount = self.factory.buyInPlayer(avatar.getSerial(), self.game.id, self.currency_serial, max(amount, self.game.buyIn()))
        return avatar.setMoney(self, amount)

    def rebuyPlayerRequest(self, avatar, amount):
        if not self.isSeated(avatar):
            self.log.warn("player %d can't rebuy to a table before getting a seat", avatar.getSerial())
            return False

        serial = avatar.getSerial()
        player = self.game.getPlayer(serial)
        if not player.isBuyInPayed():
            self.log.warn("player %d can't rebuy before paying the buy in", serial)
            return False

        maximum = self.game.maxBuyIn() - self.game.getPlayerMoney(serial)
        if maximum <= 0:
            self.log.warn("player %d can't bring more money to the table", serial)
            return False

        if amount == 0:
            amount = self.game.buyIn()

        amount = self.factory.buyInPlayer(serial, self.game.id, self.currency_serial, min(amount, maximum))

        if amount == 0:
            self.log.warn("player %d is broke and cannot rebuy", serial)
            return False

        if self.tourney and not self.tourney.isRebuyAllowed(serial):
            return False

        if not self.game.rebuy(serial, amount):
            self.log.warn("player %d rebuy denied", serial)
            return False

        if self.tourney:
            self.tourney.reenterGame(self.game.id, serial)

        self.broadcast(PacketPokerRebuy(
            game_id = self.game.id,
            serial = serial,
            amount = amount
        ))
        return True

    def playerWarningTimer(self, serial):
        info = self.timer_info
        if self.game.isRunning() and serial == self.game.getSerialInPosition():
            timeout = self.playerTimeout / 2
            #
            # Compensate the communication lag by always giving the avatar
            # an extra 2 seconds to react. The warning says that there only is
            # N seconds left but the server will actually timeout after N + TIMEOUT_DELAY_COMPENSATION
            # seconds.
            self.broadcast(PacketPokerTimeoutWarning(
                game_id = self.game.id,
                serial = serial,
                timeout = timeout
            ))
            info["playerTimeout"] = reactor.callLater(timeout+self.TIMEOUT_DELAY_COMPENSATION, self.playerTimeoutTimer, serial)
        else:
            self.updatePlayerTimers()

    def playerTimeoutTimer(self, serial):
        self.log.debug("player %d times out" % serial)
        if self.game.isRunning() and serial == self.game.getSerialInPosition():
            if self.timeout_policy == "sitOut":
                self.game.sitOutNextTurn(serial)
                self.game.autoPlayer(serial)
            elif self.timeout_policy == "fold":
                self.game.autoPlayerFoldNextTurn(serial)
                self.game.autoPlayer(serial)
                self.broadcast(PacketPokerAutoFold(
                    game_id=self.game.id,
                    serial=serial
                ))
            else:
                self.log.error("unknown timeout_policy %s", self.timeout_policy)
            self.broadcast(PacketPokerTimeoutNotice(
                game_id=self.game.id,
                serial=serial
            ))
            self.update()
        else:
            self.updatePlayerTimers()

    def muckTimeoutTimer(self):
        self.log.debug("muck timed out")
        # timer expires, force muck on muckables not responding
        for serial in self.game.muckable_serials[:]:
            self.game.muck(serial, want_to_muck=True)
        self.cancelMuckTimer()
        self.update()

    def cancelMuckTimer(self):
        info = self.timer_info
        timer = info["muckTimeout"]
        if timer != None:
            if timer.active(): timer.cancel()
            info["muckTimeout"] = None

    def cancelPlayerTimers(self):
        info = self.timer_info
        timer = info["playerTimeout"]
        if timer != None:
            if timer.active(): timer.cancel()
            info["playerTimeout"] = None
        info["playerTimeoutSerial"] = 0
        info["playerTimeoutTime"] = None

    def updateTimers(self, history=()):
        self.updateMuckTimer(history)
        self.updatePlayerTimers()

    def updateMuckTimer(self, history):
        for event in reversed(history):
            if event[0] == "muck":
                self.cancelMuckTimer()
                self.timer_info["muckTimeout"] = reactor.callLater(self.muckTimeout, self.muckTimeoutTimer)
                return

    def updatePlayerTimers(self):
        info = self.timer_info
        if self.game.isRunning():
            serial = self.game.getSerialInPosition()
            #
            # any event in the game resets the player timeout
            if (
                info["playerTimeoutSerial"] != serial or 
                len(self.game.historyGet()) > self.history_index
            ):
                timer = info["playerTimeout"]
                if timer != None and timer.active(): timer.cancel()
                timer = reactor.callLater(self.playerTimeout / 2, self.playerWarningTimer, serial)
                info["playerTimeout"] = timer
                info["playerTimeoutSerial"] = serial
                info["playerTimeoutTime"] = self.playerTimeout + seconds()
        else:
            #
            # if the game is not running, cancel the previous timeout
            self.cancelPlayerTimers()
    
    def getCurrentTimeoutWarning(self):
        info = self.timer_info
        packet = None
        if (
            self.game.isRunning() and 
            info["playerTimeout"] is not None and
            info["playerTimeoutSerial"] != 0 and
            info["playerTimeoutTime"] is not None and
            info["playerTimeout"].active()
        ):
            serial = info["playerTimeoutSerial"]
            timeout = int(info["playerTimeoutTime"] - seconds())
            packet = PacketPokerTimeoutWarning(
                game_id = self.game.id,
                serial = serial,
                timeout = timeout
            )
        return packet

    
    def _gameCallbackTourneyEndTurn(self,game_id,game_type,*args):
        if game_type == 'end':
            self.tourneyEndTurn()
            
    def _gameCallbackTourneyUpdateStats(self,game_id,game_type,*args):
        if game_type == 'end':
            self.tourneyUpdateStats()
                
    def _initLockCheck(self):
        self._lock_check = LockCheck(20 * 60, self._warnLock)
        self.game.registerCallback(self.__lockCheckEndCallback)
        self._lock_check_locked = False
        
    def _startLockCheck(self):
        if self._lock_check:
            self._lock_check.start()
        
    def _stopLockCheck(self):
        if self._lock_check:
            self._lock_check.stop()
    
    def __lockCheckEndCallback(self, game_id, event_type, *args):
        if event_type == 'end':
            self._stopLockCheck()
