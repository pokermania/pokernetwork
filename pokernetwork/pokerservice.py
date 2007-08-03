#
# -*- py-indent-offset: 4; coding: iso-8859-1 -*-
#
# Copyright (C) 2006, 2007 Loic Dachary <loic@dachary.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
#  Henry Precheur <henry@precheur.org> (2004)
#  Cedric Pinson <cpinson@freesheep.org> (2004-2006)

from os.path import exists
from types import *
from string import split, join
import os
import operator
import re
import libxml2
from traceback import print_exc

from MySQLdb.cursors import DictCursor
from MySQLdb.constants import ER

from OpenSSL import SSL

try:
    from OpenSSL import SSL
    HAS_OPENSSL=True
except:
    print "openSSL not available."
    HAS_OPENSSL=False


from twisted.application import service
from twisted.internet import protocol, reactor, defer
from twisted.python.runtime import seconds

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

from pokerengine.pokertournament import *
from pokerengine.pokercards import PokerCards

from pokernetwork.server import PokerServerProtocol
from pokernetwork.user import checkName, checkPassword
from pokernetwork.pokerdatabase import PokerDatabase
from pokernetwork.pokerpackets import *
from pokernetwork.pokertable import PokerTable
from pokernetwork import pokeravatar
from pokernetwork.user import User
from pokernetwork import pokercashier
from pokernetwork import pokernetworkconfig

UPDATE_TOURNEYS_SCHEDULE_DELAY = 10 * 60
CHECK_TOURNEYS_SCHEDULE_DELAY = 60
DELETE_OLD_TOURNEYS_DELAY = 15 * 60

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
        if type(settings) is StringType:
            settings_object = pokernetworkconfig.Config([])
            settings_object.doc = libxml2.parseMemory(settings, len(settings))
            settings_object.header = settings_object.doc.xpathNewContext()
            settings = settings_object
        self.settings = settings
        self.verbose = self.settings.headerGetInt("/server/@verbose")
        self.delays = settings.headerGetProperties("/server/delays")[0]
        self.db = None
        self.cashier = None
        self.poker_auth = None
        self.timer = {}
        self.down = True
        self.shutdown_deferred = None

    def startService(self):
        self.db = PokerDatabase(self.settings)
        self.cleanupCrashedTables()
        self.cleanUp(temporary_users = self.settings.headerGet("/server/users/@temporary"))
        self.cashier = pokercashier.PokerCashier(self.settings)
        self.cashier.setDb(self.db)
        self.poker_auth = PokerAuth(self.db, self.settings)
        self.dirs = split(self.settings.headerGet("/server/path"))
        self.serial2client = {}
        self.avatars = []
        self.tables = []
        self.table_serial = 100
        self.shutting_down = False
        self.simultaneous = self.settings.headerGetInt("/server/@simultaneous")
        self._ping_delay = self.settings.headerGetInt("/server/@ping")
        self.chat = self.settings.headerGet("/server/@chat") == "yes"
        for description in self.settings.headerGetProperties("/server/table"):
            self.createTable(0, description)
        self.cleanupTourneys()
        self.updateTourneysSchedule()
        self.messageCheck()
        self.poker_auth.SetLevel(PACKET_POKER_SEAT, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_GET_USER_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_GET_PERSONAL_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_PLAYER_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_TOURNEY_REGISTER, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_HAND_SELECT_ALL, User.ADMIN)
        service.Service.startService(self)
        self.down = False

    def stopServiceFinish(self, x):
        if self.cashier: self.cashier.close()
        if self.db: self.db.close()
        if self.poker_auth: self.poker_auth.db = None
        service.Service.stopService(self)

    def stopService(self):
        deferred = self.shutdown()
        deferred.addCallback(lambda x: reactor.disconnectAll())
        deferred.addCallback(self.stopServiceFinish)
        return deferred

    def cancelTimer(self, key):
        if self.timer.has_key(key):
           if self.verbose > 3: print "cancelTimer " + key
           timer = self.timer[key]
           if timer.active():
              timer.cancel()
           del self.timer[key]

    def cancelTimers(self, what):
        for key in self.timer.keys():
            if what in key:
                self.cancelTimer(key)

    def shutdown(self):
        self.shutting_down = True
        self.cancelTimer('checkTourney')
        self.cancelTimer('updateTourney')
        self.cancelTimer('messages')
        self.cancelTimers('tourney_breaks')
        self.shutdown_deferred = defer.Deferred()
        reactor.callLater(0.01, self.shutdownCheck)
        return self.shutdown_deferred

    def shutdownCheck(self):
        if self.down:
            if self.shutdown_deferred:
                self.shutdown_deferred.callback(True)
            return

        playing = 0
        for table in self.tables:
            if not table.game.isEndOrNull():
                playing += 1
        if self.verbose and playing > 0:
            print "Shutting down, waiting for %d games to finish" % playing
        if playing <= 0:
            if self.verbose:
                print "Shutdown immediately"
            self.down = True
            self.shutdown_deferred.callback(True)
            self.shutdown_deferred = False
        else:
            reactor.callLater(10, self.shutdownCheck)

    def isShuttingDown(self):
        return self.shutting_down

    def stopFactory(self):
        pass

    def createAvatar(self):
        avatar = pokeravatar.PokerAvatar(self)
        self.avatars.append(avatar)
        return avatar

    def destroyAvatar(self, avatar):
        if avatar in self.avatars:
            self.avatars.remove(avatar)
        else:
            print "*ERROR* PokerService: avatar %s is not in the list of known avatars" % str(avatar)
        avatar.connectionLost("Disconnected")

    def sessionStart(self, serial, ip):
        if self.verbose > 2: print "PokerService::sessionStart(%d, %s): " % ( serial, ip )
        cursor = self.db.cursor()
        sql = "insert into session ( user_serial, started, ip ) values ( %d, %d, '%s')" % ( serial, seconds(), ip )
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s" % ( cursor.rowcount, sql )
        cursor.close()
        return True

    def sessionEnd(self, serial):
        if self.verbose > 2: print "PokerService::sessionEnd(%d): " % ( serial )
        cursor = self.db.cursor()
        sql = "insert into session_history ( user_serial, started, ended, ip ) select user_serial, started, %d, ip from session where user_serial = %d" % ( seconds(), serial )
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* a) modified %d rows (expected 1): %s" % ( cursor.rowcount, sql )
        sql = "delete from session where user_serial = %d" % serial
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* b) modified %d rows (expected 1): %s" % ( cursor.rowcount, sql )
        cursor.close()
        return True

    def auth(self, name, password, roles):
        for (serial, client) in self.serial2client.iteritems():
            if client.getName() == name and roles.intersection(client.roles):
                if self.verbose: print "PokerService::auth: %s attempt to login more than once with similar roles %s" % ( name, roles.intersection(client.roles) )
                return ( False, "Already logged in from somewhere else" )
        return self.poker_auth.auth(name, password)

    def updateTourneysSchedule(self):
        if self.verbose > 3: print "updateTourneysSchedule"
        cursor = self.db.cursor(DictCursor)

        sql = ( " SELECT * FROM tourneys_schedule WHERE " + 
                "          active = 'y' AND " + 
                "          ( respawn = 'y' OR " + 
                "            register_time < " + str(int(seconds())) + " )" )
        cursor.execute(sql)
        result = cursor.fetchall()
        self.tourneys_schedule = dict(zip(map(lambda schedule: schedule['serial'], result), result))
        cursor.close()
        self.checkTourneysSchedule()
        self.cancelTimer('updateTourney')
        self.timer['updateTourney'] = reactor.callLater(UPDATE_TOURNEYS_SCHEDULE_DELAY, self.updateTourneysSchedule)

    def checkTourneysSchedule(self):
        if self.verbose > 3: print "checkTourneysSchedule"
        #
        # Respawning tournaments
        # 
        for schedule in filter(lambda schedule: schedule['respawn'] == 'y', self.tourneys_schedule.values()):
            schedule_serial = schedule['serial']
            if ( not self.schedule2tourneys.has_key(schedule_serial) or
                 not filter(lambda tourney: tourney.state == TOURNAMENT_STATE_REGISTERING, self.schedule2tourneys[schedule_serial]) ):
                self.spawnTourney(schedule)
        #
        # One time tournaments
        # 
        now = seconds()
        one_time = []
        for serial in self.tourneys_schedule.keys():
            schedule = self.tourneys_schedule[serial]
            if ( schedule['respawn'] == 'n' and 
                 int(schedule['register_time']) < now ):
                one_time.append(schedule)
                del self.tourneys_schedule[serial]
        for schedule in one_time:
            self.spawnTourney(schedule)

        #
        # Update tournaments with time clock
        # 
        for tourney in filter(lambda tourney: tourney.sit_n_go == 'n', self.tourneys.values()):
            tourney.updateRunning()
        #
        # Forget about old tournaments 
        #
        for tourney in filter(lambda tourney: tourney.state in ( TOURNAMENT_STATE_COMPLETE,  TOURNAMENT_STATE_CANCELED ), self.tourneys.values()):
            if now - tourney.finish_time > DELETE_OLD_TOURNEYS_DELAY:
                self.deleteTourney(tourney)

        self.cancelTimer('checkTourney')
        self.timer['checkTourney'] = reactor.callLater(CHECK_TOURNEYS_SCHEDULE_DELAY, self.checkTourneysSchedule)

    def spawnTourney(self, schedule):
        cursor = self.db.cursor()
        cursor.execute("INSERT INTO tourneys "
                       " (schedule_serial, name, description_short, description_long, players_quota, players_min, variant, betting_structure, seats_per_game, player_timeout, currency_serial, prize_min, bailor_serial, buy_in, rake, sit_n_go, breaks_first, breaks_interval, breaks_duration, rebuy_delay, add_on, add_on_delay, start_time)"
                       " VALUES "
                       " (%s,              %s,   %s,                %s,               %s,            %s,          %s,      %s,                %s,             %s,             %s,              %s,        %s,            %s,     %s,   %s,       %s,           %s,              %s,              %s,          %s,     %s,           %s )",
                       ( schedule['serial'],
                         schedule['name'],
                         schedule['description_short'],
                         schedule['description_long'],
                         schedule['players_quota'],
                         schedule['players_min'],
                         schedule['variant'],
                         schedule['betting_structure'],
                         schedule['seats_per_game'],
                         schedule['player_timeout'],
                         schedule['currency_serial'],
                         schedule['prize_min'],
                         schedule['bailor_serial'],
                         schedule['buy_in'],
                         schedule['rake'],
                         schedule['sit_n_go'],
                         schedule['breaks_first'],
                         schedule['breaks_interval'],
                         schedule['breaks_duration'],
                         schedule['rebuy_delay'],
                         schedule['add_on'],
                         schedule['add_on_delay'],
                         schedule['start_time'] ) )
        if self.verbose > 2: print "spawnTourney: " + str(schedule)
        #
        # Accomodate with MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            tourney_serial = cursor.lastrowid
        else:
            tourney_serial = cursor.insert_id()
        if schedule['respawn'] == 'n':
            cursor.execute("UPDATE tourneys_schedule SET active = 'n' WHERE serial = %s" % schedule['serial'])
        cursor.close()
        self.spawnTourneyInCore(schedule, tourney_serial, schedule['serial'])

    def spawnTourneyInCore(self, tourney_map, tourney_serial, schedule_serial):
        tourney_map['start_time'] = int(tourney_map['start_time'])
        tourney_map['register_time'] = int(tourney_map.get('register_time', 0))
        tourney = PokerTournament(dirs = self.dirs, **tourney_map)
        tourney.serial = tourney_serial
        tourney.verbose = self.verbose
        tourney.schedule_serial = schedule_serial
        tourney.currency_serial = tourney_map['currency_serial']
        tourney.bailor_serial = tourney_map['bailor_serial']
        tourney.player_timeout = int(tourney_map['player_timeout'])
        tourney.callback_new_state = self.tourneyNewState
        tourney.callback_create_game = self.tourneyCreateTable
        tourney.callback_game_filled = self.tourneyGameFilled
        tourney.callback_destroy_game = self.tourneyDestroyGame
        tourney.callback_move_player = self.tourneyMovePlayer
        tourney.callback_remove_player = self.tourneyRemovePlayer
        tourney.callback_cancel = self.tourneyCancel
        if not self.schedule2tourneys.has_key(schedule_serial):
            self.schedule2tourneys[schedule_serial] = []
        self.schedule2tourneys[schedule_serial].append(tourney)
        self.tourneys[tourney.serial] = tourney
        return tourney

    def deleteTourney(self, tourney):
        if self.verbose > 2: print "deleteTourney: %d" % tourney.serial
        self.schedule2tourneys[tourney.schedule_serial].remove(tourney)
        if len(self.schedule2tourneys[tourney.schedule_serial]) <= 0:
            del self.schedule2tourneys[tourney.schedule_serial]
        del self.tourneys[tourney.serial]

    def tourneyNewState(self, tourney, old_state, new_state):
        cursor = self.db.cursor()
        updates = [ "state = '" + new_state + "'" ]
        if old_state != TOURNAMENT_STATE_BREAK and new_state == TOURNAMENT_STATE_RUNNING:
            updates.append("start_time = %d" % tourney.start_time)
        sql = "update tourneys set " + ", ".join(updates) + " where serial = " + str(tourney.serial)
        if self.verbose > 2: print "tourneyNewState: " + sql
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()
        if new_state == TOURNAMENT_STATE_BREAK:
            self.tourneyBreakCheck(tourney)
        elif old_state == TOURNAMENT_STATE_BREAK and new_state == TOURNAMENT_STATE_RUNNING:
            self.tourneyBreakResume(tourney)
            self.tourneyDeal(tourney)
        elif new_state == TOURNAMENT_STATE_RUNNING:
            self.tourneyDeal(tourney)
        elif new_state == TOURNAMENT_STATE_BREAK_WAIT:
            self.tourneyBreakWait(tourney)

    def tourneyBreakCheck(self, tourney):
        key = 'tourney_breaks_%d' % id(tourney)
        self.cancelTimer(key)
        tourney.updateBreak()
        if tourney.state == TOURNAMENT_STATE_BREAK:
            remaining = tourney.remainingBreakSeconds()
            if remaining < 60:
                remaining = "less than a minute"
            elif remaining < 120:
                remaining = "one minute"
            else:
                remaining = "%d minutes" % int(remaining / 60)
            for game_id in map(lambda game: game.id, tourney.games):
                table = self.getTable(game_id)
                table.broadcastMessage(PacketPokerGameMessage, "Tournament is now on break for " + remaining)
        
            self.timer[key] = reactor.callLater(int(self.delays.get('breaks_check', 30)), self.tourneyBreakCheck, tourney)

    def tourneyDeal(self, tourney):
        for game_id in map(lambda game: game.id, tourney.games):
            table = self.getTable(game_id)
            table.scheduleAutoDeal()

    def tourneyBreakWait(self, tourney):
        for game_id in map(lambda game: game.id, tourney.games):
            table = self.getTable(game_id)
            if table.game.isRunning():
                table.broadcastMessage(PacketPokerGameMessage, "Tournament break at the end of the hand")
            else:
                table.broadcastMessage(PacketPokerGameMessage, "Tournament break will start when the other tables finish their hand")

    def tourneyBreakResume(self, tourney):
        for game_id in map(lambda game: game.id, tourney.games):
            table = self.getTable(game_id)
            table.broadcastMessage(PacketPokerGameMessage, "Tournament resumes")

    def tourneyEndTurn(self, tourney, game_id):
        if not tourney.endTurn(game_id):
            self.tourneyFinished(tourney)

    def tourneyFinished(self, tourney):
        prizes = tourney.prizes()
        winners = tourney.winners[:len(prizes)]
        cursor = self.db.cursor()
        #
        # Guaranteed prize pool is withdrawn from a given account if and only if
        # the buy in of the players is not enough.
        #
        bail = tourney.prize_min - ( tourney.buy_in * tourney.registered )
        if bail > 0:
            sql = ( "UPDATE user2money SET amount = amount - " + str(bail) + " WHERE " + 
                    "       user_serial = " + str(tourney.bailor_serial) + " AND " +
                    "       currency_serial = " + str(tourney.currency_serial) + " AND " +
                    "       amount >= " + str(bail) )
            if self.verbose > 2: print "tourneyFinished: bailor pays " + sql
            cursor.execute(sql)
            if cursor.rowcount != 1: 
                print " *ERROR* tourneyFinished: bailor failed to provide requested money modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
                cursor.close()
                return
            
        while prizes:
            prize = prizes.pop(0)
            serial = winners.pop(0)
            if prize <= 0:
                continue
            sql = "UPDATE user2money SET amount = amount + " + str(prize) + " WHERE user_serial = " + str(serial) + " AND currency_serial = " + str(tourney.currency_serial)
            if self.verbose > 2: print "tourneyFinished: " + sql
            cursor.execute(sql)
            if cursor.rowcount == 0:
                sql = ( "INSERT INTO user2money (user_serial, currency_serial, amount) VALUES (%d, %d, %d)" %
                        ( serial, tourney.currency_serial, prize ) )
                if self.verbose > 2: print "tourneyFinished: " + sql
                cursor.execute(sql)

            if cursor.rowcount != 1: 
                print " *ERROR* tourneyFinished: affected %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        
        cursor.close()

    def tourneyGameFilled(self, tourney, game):
        table = self.getTable(game.id)
        cursor = self.db.cursor()
        for player in game.playersAll():
            serial = player.serial
            player.setUserData(pokeravatar.DEFAULT_PLAYER_USER_DATA.copy())
            client = self.serial2client.get(serial, None)
            if client:
                if self.verbose > 2: print "tourneyGameFilled: player %d connected" % serial
                table.serial2client[serial] = client
            else:
                if self.verbose > 2: print "tourneyGameFilled: player %d disconnected" % serial
            self.seatPlayer(serial, game.id, game.buyIn())

            if client:
                client.join(table)
            sql = "update user2tourney set table_serial = %d where user_serial = %d and tourney_serial = %d" % ( game.id, serial, tourney.serial )
            if self.verbose > 4: print "tourneyGameFilled: " + sql
            cursor.execute(sql)
            if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()
        table.update()

    def tourneyCreateTable(self, tourney):
        table = self.createTable(0, { 'name': tourney.name + str(self.table_serial),
                                      'variant': tourney.variant,
                                      'betting_structure': tourney.betting_structure,
                                      'seats': tourney.seats_per_game,
                                      'currency_serial': 0,
                                      'player_timeout': tourney.player_timeout,
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
        from_table.movePlayer(from_table.serial2client.get(serial, None), serial, to_game_id)
        cursor = self.db.cursor()
        sql = "update user2tourney set table_serial = %d where user_serial = %d and tourney_serial = %d" % ( to_game_id, serial, tourney.serial )
        if self.verbose > 4: print "tourneyMovePlayer: " + sql
        cursor.execute(sql)
        if cursor.rowcount != 1: print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
        cursor.close()

    def tourneyRemovePlayer(self, tourney, game_id, serial):
        #
        # Inform the player about its position and prize
        #
        prizes = tourney.prizes()
        rank = tourney.getRank(serial)
        money = 0
        players = len(tourney.players)
        if rank-1 < len(prizes):
            money = prizes[rank-1]

        client = self.serial2client.get(serial, None)
        if client:
            packet = PacketPokerTourneyRank(serial = tourney.serial,
                                            game_id = game_id,
                                            players = players,
                                            rank = rank,
                                            money = money)
            client.sendPacketVerbose(packet)
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
            ( currency_serial, type ) = criterion
            sit_n_go = type == 'sit_n_go' and 'y' or 'n'
            if currency_serial:
                currency_serial = int(currency_serial)
                return filter(lambda tourney: tourney['currency_serial'] == currency_serial and tourney['sit_n_go'] == sit_n_go, tourneys)
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
        currency_serial = tourney.currency_serial
        withdraw = tourney.buy_in + tourney.rake
        if withdraw > 0:
            sql = ( "UPDATE user2money SET amount = amount - " + str(withdraw) +
                    " WHERE user_serial = " + str(serial) + " AND " +
                    "       currency_serial = " + str(currency_serial) + " AND " +
                    "       amount >= " + str(withdraw)
                    )
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
        sql = "INSERT INTO user2tourney (user_serial, tourney_serial) VALUES (%d, %d)" % ( serial, tourney_serial )
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
        if client: client.sendPacketVerbose(packet)
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
        currency_serial = tourney.currency_serial
        withdraw = tourney.buy_in + tourney.rake
        if withdraw > 0:
            sql = ( "UPDATE user2money SET amount = amount + " + str(withdraw) +
                    " WHERE user_serial = " + str(serial) + " AND " +
                    "       currency_serial = " + str(currency_serial) )
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

    def tourneyCancel(self, tourney):
        if self.verbose > 1: print "tourneyCancel " + str(tourney.players)
        for serial in tourney.players:
            packet = self.tourneyUnregister(PacketPokerTourneyUnregister(game_id = tourney.serial,
                                                                         serial = serial))
            if packet.type == PACKET_ERROR:
                print "*ERROR* tourneyCancel: " + str(packet)

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
        for player_serial in player_list:
            serial2name[player_serial] = self.getName(player_serial)
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
            print "saveHand: %s" % ( sql % description )
        cursor.execute(sql, str(description))
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
        elif re.match("^[0-9]+$", string):
            return filter(lambda table: table.currency_serial == int(string), self.tables)
        elif len(criterion) > 1:
            ( currency_serial, variant ) = criterion
            if currency_serial:
                currency_serial = int(currency_serial)
                return filter(lambda table: table.game.variant == variant and table.currency_serial == currency_serial, self.tables)
            else:
                return filter(lambda table: table.game.variant == variant, self.tables)
        else:
            return filter(lambda table: table.game.name == string, self.tables)

    def cleanUp(self, temporary_users = ''):
        cursor = self.db.cursor()

        if len(temporary_users) > 2:
            sql = "delete session_history from session_history, users where session_history.user_serial = users.serial and users.name like '" + temporary_users + "%'"
            cursor.execute(sql)
            sql = "delete session from session, users where session.user_serial = users.serial and users.name like '" + temporary_users + "%'"
            cursor.execute(sql)
            sql = "delete from users where name like '" + temporary_users + "%'"
            cursor.execute(sql)

        sql = "insert into session_history ( user_serial, started, ended, ip ) select user_serial, started, %d, ip from session" % seconds()
        cursor.execute(sql)
        sql = "delete from session"
        cursor.execute(sql)

        cursor.close()

    def cleanupTourneys(self):
        self.tourneys = {}
        self.schedule2tourneys = {}
        self.tourneys_schedule = {}

        cursor = self.db.cursor(DictCursor)
        sql = "SELECT * FROM tourneys WHERE state = 'registering' AND start_time > (%d + 60)" % seconds()
        if self.verbose > 2: print "cleanupTourneys: " + sql
        cursor.execute(sql)
        for x in xrange(cursor.rowcount):
            row = cursor.fetchone()
            if self.verbose >= 0: message = "cleanupTourneys: restoring %s(%s) with players" % ( row['name'], row['serial'],  )
            tourney = self.spawnTourneyInCore(row, row['serial'], row['schedule_serial'])
            cursor1 = self.db.cursor()
            sql = "SELECT user_serial FROM user2tourney WHERE tourney_serial = " + str(row['serial'])
            if self.verbose > 2: print "cleanupTourneys: " + sql
            cursor1.execute(sql)
            for y in xrange(cursor1.rowcount):
                (serial,) = cursor1.fetchone()
                if self.verbose >= 0: message += " " + str(serial)
                tourney.register(serial)
                
            cursor1.execute(sql)
            cursor1.close()
            if self.verbose >= 0: print message
        cursor.close()

    def getMoney(self, serial, currency_serial):
        cursor = self.db.cursor()
        sql = ( "SELECT amount FROM user2money " +
                "       WHERE user_serial = " + str(serial) + " AND " +
                "             currency_serial = "  + str(currency_serial) )
        if self.verbose: print sql
        cursor.execute(sql)
        if cursor.rowcount > 1:
            print " *ERROR* getMoney(%d) expected one row got %d" % ( serial, cursor.rowcount )
            cursor.close()
            return 0
        elif cursor.rowcount == 1:
            (money,) = cursor.fetchone()
        else:
            money = 0
        cursor.close()
        return money

    def cashIn(self, packet):
        return self.cashier.cashIn(packet)

    def cashOut(self, packet):
        return self.cashier.cashOut(packet)

    def cashQuery(self, packet):
        return self.cashier.cashQuery(packet)

    def cashOutCommit(self, packet):
        count = self.cashier.cashOutCommit(packet)
        if count in (0, 1):
            return PacketAck()
        else:
            return PacketError(code = PacketPokerCashOutCommit.INVALID_TRANSACTION,
                               message = "transaction " + packet.transaction_id + " affected " + str(count) + " rows instead of zero or one",
                               other_type = PACKET_POKER_CASH_OUT_COMMIT)

    def getPlayerInfo(self, serial):
        placeholder = PacketPokerPlayerInfo(serial = serial,
                                            name = "anonymous",
                                            url= "random",
                                            outfit = "random")
        if serial == 0:
            return placeholder

        cursor = self.db.cursor()
        sql = ( "select name,skin_url,skin_outfit from users where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getPlayerInfo(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return placeholder
        (name,skin_url,skin_outfit) = cursor.fetchone()
        if skin_outfit == None:
            skin_outfit = "random"
        cursor.close()
        return PacketPokerPlayerInfo(serial = serial,
                                     name = name,
                                     url = skin_url,
                                     outfit = skin_outfit)

    def getUserInfo(self, serial):
        cursor = self.db.cursor(DictCursor)

        sql = ( "SELECT rating,affiliate,email,name FROM users WHERE serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getUserInfo(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return PacketPokerUserInfo(serial = serial)
        row = cursor.fetchone()
        if row['email'] == None: row['email'] = ""

        packet = PacketPokerUserInfo(serial = serial,
                                     name = row['name'],
                                     email = row['email'],
                                     rating = row['rating'],
                                     affiliate = row['affiliate'])
        sql = ( " SELECT user2money.currency_serial,user2money.amount,user2money.points,CAST(SUM(user2table.bet) + SUM(user2table.money) AS UNSIGNED) AS in_game "
                "        FROM user2money LEFT JOIN (pokertables,user2table) "
                "        ON (user2table.user_serial = user2money.user_serial  AND "
                "            user2table.table_serial = pokertables.serial AND  "
                "            user2money.currency_serial = pokertables.currency_serial)  "
                "        WHERE user2money.user_serial = " + str(serial) + " GROUP BY user2money.currency_serial " )
        if self.verbose: print sql
        cursor.execute(sql)
        for row in cursor:
            if not row['in_game']: row['in_game'] = 0
            if not row['points']: row['points'] = 0
            packet.money[row['currency_serial']] = ( row['amount'], row['in_game'], row['points'] )
        if self.verbose > 2: print "getUserInfo: " + str(packet)
        return packet

    def getPersonalInfo(self, serial):
        user_info = self.getUserInfo(serial)
        print "getPersonalInfo %s" % str(user_info)
        packet = PacketPokerPersonalInfo(serial = user_info.serial,
                                         name = user_info.name,
                                         email = user_info.email,
                                         rating = user_info.rating,
                                         affiliate = user_info.affiliate,
                                         money = user_info.money)
        cursor = self.db.cursor()
        sql = ( "SELECT firstname,lastname,addr_street,addr_street2,addr_zip,addr_town,addr_state,addr_country,phone,gender,birthdate FROM users_private WHERE serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getPersonalInfo(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return PacketPokerPersonalInfo(serial = serial)
        (packet.firstname, packet.lastname, packet.addr_street, packet.addr_street2, packet.addr_zip, packet.addr_town, packet.addr_state, packet.addr_country, packet.phone, packet.gender, packet.birthdate) = cursor.fetchone()
        cursor.close()
        if not packet.gender: packet.gender = ''
        if not packet.birthdate: packet.birthdate = ''
        return packet

    def setPersonalInfo(self, personal_info):
        cursor = self.db.cursor()
        sql = ( "UPDATE users_private SET "
                " firstname = '" + personal_info.firstname + "', "
                " lastname = '" + personal_info.lastname + "', "
                " addr_street = '" + personal_info.addr_street + "', "
                " addr_street2 = '" + personal_info.addr_street2 + "', "
                " addr_zip = '" + personal_info.addr_zip + "', "
                " addr_town = '" + personal_info.addr_town + "', "
                " addr_state = '" + personal_info.addr_state + "', "
                " addr_country = '" + personal_info.addr_country + "', "
                " phone = '" + personal_info.phone + "', "
                " gender = '" + personal_info.gender + "', "
                " birthdate = '" + personal_info.birthdate + "' "
                " WHERE serial = " + str(personal_info.serial) )
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
            sql = "INSERT INTO users (created, name, password, email, affiliate) values (%d, '%s', '%s', '%s', '%d')" % (seconds(), packet.name, packet.password, packet.email, packet.affiliate)
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


    def getPlayerImage(self, serial):
        placeholder = PacketPokerPlayerImage(serial = serial)

        if serial == 0:
            return placeholder

        cursor = self.db.cursor()
        sql = ( "select skin_image,skin_image_type from users where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* getPlayerImage(%d) expected one row got %d" % ( serial, cursor.rowcount )
            return placeholder
        (skin_image, skin_image_type) = cursor.fetchone()
        if skin_image == None:
            skin_image = ""
        cursor.close()
        return PacketPokerPlayerImage(serial = serial,
                                      image = skin_image,
                                      image_type = skin_image_type)

    def setPlayerImage(self, player_image):
        cursor = self.db.cursor()
        sql = ( "update users set "
                " skin_image = '" + player_image.image + "', "
                " skin_image_type = '" + player_image.image_type + "' "
                " where serial = " + str(player_image.serial) )
        if self.verbose > 1:
            print "setPlayerInfo: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            print " *ERROR* setPlayerImage: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql )
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

    def buyInPlayer(self, serial, table_id, currency_serial, amount):
        # unaccounted money is delivered regardless
        if not currency_serial: return amount

        withdraw = min(self.getMoney(serial, currency_serial), amount)
        cursor = self.db.cursor()
        sql = ( "UPDATE user2money,user2table SET "
                " user2table.money = user2table.money + " + str(withdraw) + ", "
                " user2money.amount = user2money.amount - " + str(withdraw) + " "
                " WHERE user2money.user_serial = " + str(serial) + " AND "
                "       user2money.currency_serial = " + str(currency_serial) + " AND "
                "       user2table.user_serial = " + str(serial) + " AND "
                "       user2table.table_serial = " + str(table_id) )
        if self.verbose > 1:
            print "buyInPlayer: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 0 and cursor.rowcount != 2:
            print " *ERROR* modified %d rows (expected 0 or 2): %s " % ( cursor.rowcount, sql )
        return withdraw

    def seatPlayer(self, serial, table_id, amount):
        status = True
        cursor = self.db.cursor()
        sql = ( "INSERT user2table ( user_serial, table_serial, money) VALUES "
                " ( " + str(serial) + ", " + str(table_id) + ", " + str(amount) + " )" )
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
        sql = ( "SELECT money FROM user2table "
                "  WHERE user_serial = " + str(serial) + " AND "
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

    def leavePlayer(self, serial, table_id, currency_serial):
        status = True
        cursor = self.db.cursor()
        if currency_serial != '':
           sql = ( "UPDATE user2money,user2table,pokertables SET " +
                   " user2money.amount = user2money.amount + user2table.money + user2table.bet " +
                   " WHERE user2money.user_serial = user2table.user_serial AND " +
                   "       user2money.currency_serial = pokertables.currency_serial AND " +
                   "       pokertables.serial = " + str(table_id) + " AND " +
                   "       user2table.table_serial = " + str(table_id) + " AND " +
                   "       user2table.user_serial = " + str(serial) )
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
            status = False
        cursor.close()
        return status

    def updatePlayerRake(self, currency_serial, serial, amount):
        if amount == 0:
            return True
        status = True
        cursor = self.db.cursor()
        sql = ( "UPDATE user2money SET "
                " rake = rake + " + str(amount) + ", "
                " points = points + " + str(amount) + " "
                " WHERE user_serial = " + str(serial) + " AND "
                "       currency_serial = " + str(currency_serial) )
        if self.verbose > 1:
            print "updatePlayerRake: %s" % sql
        cursor.execute(sql)
        if cursor.rowcount != 1:
            print " *ERROR* modified %d rows (expected 1): %s " % ( cursor.rowcount, sql )
            status = False
        cursor.close()
        return status

    def updatePlayerMoney(self, serial, table_id, amount):
        if amount == 0:
            return True
        status = True
        cursor = self.db.cursor()
        sql = ( "UPDATE user2table SET "
                " money = money + " + str(amount) + ", "
                " bet = bet - " + str(amount) +
                " WHERE user_serial = " + str(serial) + " AND "
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
        sql = ( "SELECT sum(money), sum(bet) FROM user2table WHERE table_serial = " + str(table_id) )
        cursor.execute(sql)
        (money, bet) = cursor.fetchone()
        cursor.close()
        if not money: money = 0
        elif type(money) == StringType: money = int(money)
        if not bet: bet = 0
        elif type(bet) == StringType: bet = int(bet)
        return  (money, bet)

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

        cursor = self.db.cursor()
        sql = ( "INSERT pokertables ( serial, name, currency_serial ) VALUES "
                " ( " + str(id) + ", \"" + description["name"] + "\", " + str(description["currency_serial"]) + " ) " )
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

        sql = ( "select user_serial,table_serial,currency_serial from pokertables,user2table where user2table.table_serial = pokertables.serial " )
        cursor.execute(sql)
        if cursor.rowcount > 0 and self.verbose > 1:
            print "cleanupCrashedTables found %d players" % cursor.rowcount
        for i in xrange(cursor.rowcount):
            (user_serial, table_serial, currency_serial) = cursor.fetchone()
            self.leavePlayer(user_serial, table_serial, currency_serial)

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

    def broadcast(self, packet):
        for avatar in self.avatars:
            if hasattr(avatar, "protocol") and avatar.protocol:
                avatar.sendPacketVerbose(packet)
            else:
                print "broadcast: avatar %s excluded" % str(avatar)

    def messageCheck(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT serial,message FROM messages WHERE " + 
                       "       sent = 'n' AND send_date < FROM_UNIXTIME(" + str(int(seconds())) + ")")
        rows = cursor.fetchall()
        for (serial, message) in rows:
            self.broadcast(PacketMessage(string = message))
            cursor.execute("UPDATE messages SET sent = 'y' WHERE serial = %d" % serial)
        cursor.close()
        self.cancelTimer('messages')
        delay = int(self.delays.get('messages', 60))
        self.timer['messages'] = reactor.callLater(delay, self.messageCheck)

class PokerAuth:

    def __init__(self, db, settings):
        self.db = db
        self.type2auth = {}
        self.verbose = settings.headerGetInt("/server/@verbose")
        self.auto_create_account = settings.headerGet("/server/@auto_create_account") != 'no'
        currency = settings.headerGetProperties("/server/currency")
        if len(currency) > 0:
            self.currency = currency[0]
        else:
            self.currency = None

    def SetLevel(self, type, level):
        self.type2auth[type] = level

    def GetLevel(self, type):
        return self.type2auth.has_key(type) and self.type2auth[type]

    def auth(self, name, password):
        cursor = self.db.cursor()
        cursor.execute("SELECT serial, password, privilege FROM users "
                       "WHERE name = '%s'" % name)
        numrows = int(cursor.rowcount)
        serial = 0
        privilege = User.REGULAR
        if numrows <= 0:
            if self.auto_create_account:
                if self.verbose > 1:
                    print "user %s does not exist, create it" % name
                serial = self.userCreate(name, password)
                cursor.close()
            else:
                if self.verbose > 1:
                    print "user %s does not exist" % name
                cursor.close()
                return ( False, "Invalid login or password" )
        elif numrows > 1:
            print "more than one row for %s" % name
            cursor.close()
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
        cursor.execute("INSERT INTO users (created, name, password) values (%d, '%s', '%s')" %
                       (seconds(), name, password))
        #
        # Accomodate for MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            serial = cursor.lastrowid
        else:
            serial = cursor.insert_id()
        if self.verbose:
            print "create user with serial %s" % serial
        cursor.execute("INSERT INTO users_private (serial) values ('%d')" % serial)
        if self.currency:
            cursor.execute("INSERT INTO user2money (user_serial, currency_serial, amount) values (%d, %s, %s)" % ( serial, self.currency['serial'], self.currency['amount']))
        cursor.close()
        return int(serial)

if HAS_OPENSSL:
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
        try:
            self.putChild("SOAP", PokerSOAP(self.service))
        except:
            print "SOAP service not available"
        self.putChild("", self)

    def render_GET(self, request):
        return "Use /RPC2 or /SOAP"

components.registerAdapter(PokerTree, IPokerService, resource.IResource)

def _getRequestCookie(request):
    if request.cookies:
        return request.cookies[0]
    else:
        return request.getCookie(join(['TWISTED_SESSION'] + request.sitepath, '_'))

class PokerXML(resource.Resource):

    encoding = "ISO-8859-1"

    def __init__(self, service):
        resource.Resource.__init__(self)
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
        if self.verbose > 2: print "PokerXML: " + str(args)
        session = None
        use_sessions = args[0]
        args = args[1:]
        if use_sessions == "use sessions":
            if self.verbose > 2: print "PokerXML: Receive session cookie %s " % _getRequestCookie(request)
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
                            result.cookie = _getRequestCookie(request)
                            if self.verbose > 2: print "PokerXML: Send session cookie " + result.cookie
                            break
                result_packets.extend(results)
                if isinstance(packet, PacketLogout):
                    logout = True

        #
        # If the result is a single packet, it means the requested
        # action is using sessions (non session packet streams all
        # start with an auth packet). It may be a Deferred but may never
        # be a logout (because logout is not supposed to return a deferred).
        #
        if len(result_packets) == 1 and isinstance(result_packets[0], defer.Deferred):
            def renderLater(packet):
                result_maps = self.packets2maps([packet])

                result_string = self.maps2result(result_maps)
                request.setHeader("Content-length", str(len(result_string)))
                request.write(result_string)
                request.finish()
                return
            d = result_packets[0]
            d.addCallback(renderLater)
            return server.NOT_DONE_YET
        else:
            if use_sessions != "use sessions":
                self.service.destroyAvatar(avatar)
            elif use_sessions == "use sessions" and logout:
                session.expire()

            result_maps = self.packets2maps(result_packets)

            result_string = self.maps2result(result_maps)
            if self.verbose > 2: print "result_string xmlrpc / soap " + str(result_string)
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
            if 'message' in dir(packet):
                attributes['message'] = getattr(packet, 'message')
            #
            # It is forbiden to set a map key to a numeric (native
            # numeric or string made of digits). Taint the map entries
            # that are numeric and hope the client will figure it out.
            #
	    for (key, value) in packet.__dict__.iteritems():
		if type(value) == DictType:
			for ( subkey, subvalue ) in value.items():
				del value[subkey]
				new_subkey = str(subkey)
				if new_subkey.isdigit():
					new_subkey = "X" + new_subkey
				if self.verbose > 2: print "replace key " + new_subkey
				value[new_subkey] = subvalue
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
                converted_key = convert(str(key))
                tree[converted_key] = self.walk(value, convert)
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

try:
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

            return self.fromutf8(SOAPpy.simplify(args))

        def maps2result(self, maps):
            return SOAPpy.buildSOAP(kw = {'Result': self.toutf8(maps)},
                                    method = 'returnPacket',
                                    encoding = self.encoding)
except:
    print "Python SOAP module not available"
