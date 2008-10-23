#
# -*- py-indent-offset: 4; coding: iso-8859-1 -*-
#
# Note: this file is copyrighted by multiple entities; some license their
# copyrights under GPLv3-or-later and some under AGPLv3-or-later.  Read
# below for details.
#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep
#                                24 rue vieille du temple 75004 Paris
#                                <licensing@mekensleep.com>
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
#
# Copyright (C)             2008 Bradley M. Kuhn <bkuhn@ebb.org>
#
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation, either version 3 of the License, or (at your
# option) any later version of the AGPL.
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
#  Loic Dachary <loic@gnu.org>
#  Bradley M. Kuhn <bkuhn@ebb.org> (2008-)
#  Henry Precheur <henry@precheur.org> (2004)
#  Cedric Pinson <cpinson@freesheep.org> (2004-2006)

from os.path import exists
from types import *
from string import split, join
import os
import copy
import operator
import re
import locale
import gettext
import libxml2
import simplejson
import imp
from traceback import print_exc

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
    from zope.interface import Interface
    from zope.interface import implements
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

from MySQLdb.cursors import DictCursor
from MySQLdb.constants import ER

from twisted.python import components

from pokerengine.pokertournament import *
from pokerengine.pokercards import PokerCards

from pokernetwork.protocol import UGAMEProtocol
from pokernetwork.server import PokerServerProtocol
from pokernetwork.user import checkName, checkPassword
from pokernetwork.pokerdatabase import PokerDatabase
from pokernetwork.pokerpackets import *
from pokernetwork.pokersite import PokerImageUpload, PokerAvatarResource, PokerResource, packets2maps, args2packets, fromutf8, toutf8
from pokernetwork.pokertable import PokerTable
from pokernetwork import pokeravatar
from pokernetwork.user import User
from pokernetwork import pokercashier
from pokernetwork import pokernetworkconfig
from pokernetwork.userstats import UserStatsFactory
from pokernetwork.tourneyattrs import TourneyAttrsFactory
from pokerauth import get_auth_instance

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
        self.joined_max = self.settings.headerGetInt("/server/@max_joined")
        if self.joined_max <= 0:
            # dachary picked this maximum as a default on 2008-08-16
            # <dachary> because the last stress test show 4000 is the upper limit
            # <dachary> http://pokersource.info/stress-test/2007-08/
            self.joined_max = 4000
        self.missed_round_max = self.settings.headerGetInt("/server/@max_missed_round")
        if self.missed_round_max <= 0:
            # This default for missed_round_max below (for when it is not
            # set in config file) is completely arbitrary and made up by
            # bkuhn.  dachary suggested 3 in #pokersource on 2008-08-24,
            # but bkuhn argued that if someone leaves it out of the config
            # file, it should be somewhat high since they wouldn't be
            # expecting a pick-up if they hadn't configed their server to
            # do it.
            #
            # bkuhn also pointed out that there is some arugment for
            # making the default infinity when it is left out of the
            # config file.  However, this complicates code to test for,
            # say, a negative value every time to see if you should ignore
            # the feature entirely, and it's probably not the case that
            # the user would ever want to configure a server on purpose to
            # have infinite sit-out time.
            #
            # Note that the config file example defaults this to 5, which
            # is probably a much more reasonable default.
            #
            # Finally, note that this is the server-wide default.  In the
            # config file, <table> entries can override this.
            self.missed_round_max = 10
        self.client_queued_packet_max = self.settings.headerGetInt("/server/@max_queued_client_packets")
        if self.client_queued_packet_max <= 0:
            self.client_queued_packet_max = 500
        
        self.delays = settings.headerGetProperties("/server/delays")[0]

        self.lookups = {}

        lookup2factoryClass = { 'stats' : UserStatsFactory, 'tourney_attrs' : TourneyAttrsFactory }
        for lookup in lookup2factoryClass.keys():
            if len(self.settings.headerGetProperties("/server/%s" % lookup)) > 1:
                self.error("settings include multiple <%s> tags; using first one only" % lookup)
            myArgs = []
            if lookup == 'stats': myArgs = [ self ]
            self.lookups[lookup] = lookup2factoryClass[lookup]().getClass(settings.headerGet("/server/%s/@type" % lookup))(*myArgs)

        refill = settings.headerGetProperties("/server/refill")
        if len(refill) > 0:
            self.refill = refill[0]
        else:
            self.refill = None
        self.db = None
        self.cashier = None
        self.poker_auth = None
        self.timer = {}
        self.down = True
        self.shutdown_deferred = None
        self.resthost_serial = 0
        self.monitor_plugins = []
        for monitor in settings.header.xpathEval("/server/monitor"):
            module = imp.load_source("monitor", monitor.content)
            self.monitor_plugins.append(getattr(module, "handle_event"))

    def startService(self):
        self.monitors = []
        self.db = PokerDatabase(self.settings)
        self.setupResthost()
        self.cleanupCrashedTables()
        cleanup = self.settings.headerGet("/server/@cleanup")
        if cleanup != 'no':
            self.cleanUp(temporary_users = self.settings.headerGet("/server/users/@temporary"))
        self.cashier = pokercashier.PokerCashier(self.settings)
        self.cashier.setDb(self.db)
        self.poker_auth = get_auth_instance(self.db, self.settings)
        self.dirs = split(self.settings.headerGet("/server/path"))
        self.serial2client = {}
        self.avatars = []
        self.tables = {}
        self.joined_count = 0
        self.tourney_table_serial = 1
        self.shutting_down = False
        self.simultaneous = self.settings.headerGetInt("/server/@simultaneous")
        self._ping_delay = self.settings.headerGetInt("/server/@ping")
        self.chat = self.settings.headerGet("/server/@chat") == "yes"

        # gettextFuncs is a dict that is indexed by full locale strings,
        # such as fr_FR.UTF-8, and returns a translation function.  If you
        # wanted to apply it directly, you'd do something like:
        # but usually, you will do something like this to change your locale on the fly:
        #   global _
        #   _ = self.gettextFuncs{'fr_FR.UTF-8'}
        #   _("Hello!  I am speaking in French now.")
        #   _ = self.gettextFuncs{'en_US.UTF-8'}
        #   _("Hello!  I am speaking in US-English now.")

        self.gettextFuncs = {}
        langsSupported = self.settings.headerGetProperties("/server/language")
        if (len(langsSupported) > 0):
            # Note, after calling _lookupTranslationFunc() a bunch of
            # times, we must restore the *actual* locale being used by the
            # server itself for strings locally on its machine.  That's
            # why we save it here.
            localLocale = locale.getlocale(locale.LC_ALL)

            for lang in langsSupported:
                self.gettextFuncs[lang['value']] = self._lookupTranslationFunc(lang['value'])
            try:
                locale.setlocale(locale.LC_ALL, localLocale)
            except locale.Error, le:
                self.error('Unable to restore original locale: %s' % le)

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

    def message(self, string):
        print "PokerService: " + str(string)

    def error(self, string):
        self.message("*ERROR* " + str(string))
            
    def stopServiceFinish(self, x):
        self.monitors = []
        if self.cashier: self.cashier.close()
        if self.db:
            self.cleanupCrashedTables()
            if self.resthost_serial: self.cleanupResthost()
            self.db.close()
            self.db = None
        if self.poker_auth: self.poker_auth.db = None
        service.Service.stopService(self)

    def disconnectAll(self):
        reactor.disconnectAll()
        
    def stopService(self):
        deferred = self.shutdown()
        deferred.addCallback(lambda x: self.disconnectAll())
        deferred.addCallback(self.stopServiceFinish)
        return deferred

    def cancelTimer(self, key):
        if self.timer.has_key(key):
           if self.verbose > 3:
               self.message("cancelTimer " + key)
           timer = self.timer[key]
           if timer.active():
              timer.cancel()
           del self.timer[key]

    def cancelTimers(self, what):
        for key in self.timer.keys():
            if what in key:
                self.cancelTimer(key)

    def joinedCountReachedMax(self):
        """Returns True iff. the number of joins to tables has exceeded
        the maximum allowed by the server configuration"""
        return self.joined_count >= self.joined_max

    def joinedCountIncrease(self, num = 1):
        """Increases the number of currently joins to tables by num, which
        defaults to 1."""
        self.joined_count += num
        return self.joined_count

    def joinedCountDecrease(self, num = 1):
        """Decreases the number of currently joins to tables by num, which
        defaults to 1."""
        self.joined_count -= num
        return self.joined_count

    def getMissedRoundMax(self):
        return self.missed_round_max

    def getUserStatsLookup(self):
        return self.lookups['stats']

    def getTourneyAttrsLookup(self):
        return self.lookups['tourney_attrs']

    def getClientQueuedPacketMax(self):
        return self.client_queued_packet_max

    def _lookupTranslationFunc(self, lang):
        # Start by defaulting to just returning the string...
        myGetTextFunc = lambda text:text
        try:
            locale.setlocale(locale.LC_ALL, lang)
        except locale.Error, le:
            self.error('Unable to support locale, "%s", due to locale error: %s'
                       % (lang, le))
            return myGetTextFunc

        # I am not completely sure poker-engine should be hardcoded here like this...
        gettext.bind_textdomain_codeset("poker-engine", lang)
        gettext.install("poker-engine")
        try:
            myGetTextFunc = gettext.translation('poker-engine', languages=[lang]).gettext
        except IOError, e:
            self.error("No translation to locale %s in poker-engine; locale ignored: %s"
                       % (lang, e))
        return myGetTextFunc

    def locale2translationFunc(self, locale):
        if self.gettextFuncs.has_key(locale):
            return self.gettextFuncs[locale]
        else:
            return None

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
        for table in self.tables.values():
            if not table.game.isEndOrNull():
                playing += 1
        if self.verbose and playing > 0:
            self.message("Shutting down, waiting for %d games to finish" % playing)
        if playing <= 0:
            if self.verbose:
                self.message("Shutdown immediately")
            self.down = True
            self.shutdown_deferred.callback(True)
            self.shutdown_deferred = False
        else:
            reactor.callLater(10, self.shutdownCheck)

    def isShuttingDown(self):
        return self.shutting_down

    def stopFactory(self):
        pass

    def monitor(self, avatar):
        if avatar not in self.monitors:
            self.monitors.append(avatar)
        return PacketAck()

    def databaseEvent(self, **kwargs):
        event = PacketPokerMonitorEvent(**kwargs)
        self.db.db.query("INSERT INTO monitor (event, param1, param2, param3) VALUES (%d, %d, %d, %d)" % ( kwargs['event'], kwargs.get('param1', 0), kwargs.get('param2', 0), kwargs.get('param3', 0) ))
        for avatar in self.monitors:
            if hasattr(avatar, "protocol") and avatar.protocol:
                avatar.sendPacketVerbose(event)
        for plugin in self.monitor_plugins:
            plugin(self, event)

    def stats(self, query):
        cursor = self.db.cursor()
        cursor.execute("SELECT MAX(serial) FROM hands")
        (hands,) = cursor.fetchone()
        if hands == None:
            hands = 0
        else:
            hands = int(hands)
        cursor.close()
        return PacketPokerStats(
            players = len(self.avatars),
            hands = hands,
            bytesin = UGAMEProtocol._stats_read,
            bytesout = UGAMEProtocol._stats_write,
            )
    
    def createAvatar(self):
        avatar = pokeravatar.PokerAvatar(self)
        self.avatars.append(avatar)
        return avatar

    def forceAvatarDestroy(self, avatar):
        reactor.callLater(1, self.destroyAvatar, avatar)

    def destroyAvatar(self, avatar):
        if avatar in self.avatars:
            self.avatars.remove(avatar)
        else:
            self.error("avatar %s is not in the list of known avatars" % str(avatar))
        if avatar in self.monitors:
            self.monitors.remove(avatar)
        avatar.connectionLost("Disconnected")

    def sessionStart(self, serial, ip):
        if self.verbose > 2:
            self.message("sessionStart(%d, %s): " % ( serial, ip ))
        cursor = self.db.cursor()
        sql = "insert into session ( user_serial, started, ip ) values ( %d, %d, '%s')" % ( serial, seconds(), ip )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("modified %d rows (expected 1): %s" % ( cursor.rowcount, sql ))
        cursor.close()
        return True

    def sessionEnd(self, serial):
        if self.verbose > 2:
            self.message("sessionEnd(%d): " % ( serial ))
        cursor = self.db.cursor()
        sql = "insert into session_history ( user_serial, started, ended, ip ) select user_serial, started, %d, ip from session where user_serial = %d" % ( seconds(), serial )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("a) modified %d rows (expected 1): %s" % ( cursor.rowcount, sql ))
        sql = "delete from session where user_serial = %d" % serial
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("b) modified %d rows (expected 1): %s" % ( cursor.rowcount, sql ))
        cursor.close()
        return True

    def auth(self, name, password, roles):
        for (serial, client) in self.serial2client.iteritems():
            if client.getName() == name and roles.intersection(client.roles):
                if self.verbose:
                    self.message("auth: %s attempt to login more than once with similar roles %s" % ( name, roles.intersection(client.roles) ))
                return ( False, "Already logged in from somewhere else" )
        ( info, reason ) = self.poker_auth.auth(name, password)
        if info:
            self.autorefill(info[0])
        return ( info, reason )

    def autorefill(self, serial):
        if not self.refill:
            return
        user_info = self.getUserInfo(serial)
        if user_info.money.has_key(int(self.refill['serial'])):
            money = user_info.money[int(self.refill['serial'])]
            missing = int(self.refill['amount']) - ( int(money[0]) + int(money[1]) )
            if missing > 0:
                refill = int(money[0]) + missing
            else:
                refill = 0 
        else:
            refill = int(self.refill['amount'])            
        if refill > 0:
            self.db.db.query("REPLACE INTO user2money (user_serial, currency_serial, amount) values (%d, %s, %s)" % ( serial, self.refill['serial'], refill))
            self.databaseEvent(event = PacketPokerMonitorEvent.REFILL, param1 = serial, param2 = int(self.refill['serial']), param3 = refill)
            
        return refill

    def updateTourneysSchedule(self):
        if self.verbose > 3:
            self.message("updateTourneysSchedule")
        cursor = self.db.cursor(DictCursor)

        sql = ( " SELECT * FROM tourneys_schedule WHERE " + 
                "          active = 'y' AND " + 
                "          resthost_serial = %s AND " + 
                "          ( respawn = 'y' OR " + 
                "            register_time < %s )" ) % self.db.literal((self.resthost_serial, int(seconds()) )
                )
        cursor.execute(sql)
        result = cursor.fetchall()
        self.tourneys_schedule = dict(zip(map(lambda schedule: schedule['serial'], result), result))
        cursor.close()
        self.checkTourneysSchedule()
        self.cancelTimer('updateTourney')
        self.timer['updateTourney'] = reactor.callLater(UPDATE_TOURNEYS_SCHEDULE_DELAY, self.updateTourneysSchedule)

    def checkTourneysSchedule(self):
        if self.verbose > 3:
            self.message("checkTourneysSchedule")
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
                       " (resthost_serial, schedule_serial, name, description_short, description_long, players_quota, players_min, variant, betting_structure, seats_per_game, player_timeout, currency_serial, prize_min, bailor_serial, buy_in, rake, sit_n_go, breaks_first, breaks_interval, breaks_duration, rebuy_delay, add_on, add_on_delay, start_time)"
                       " VALUES "
                       " (%s,              %s,              %s,   %s,                %s,               %s,            %s,          %s,      %s,                %s,             %s,             %s,              %s,        %s,            %s,     %s,   %s,       %s,           %s,              %s,              %s,          %s,     %s,           %s )",
                       ( schedule['resthost_serial'],
                         schedule['serial'],
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
        if self.verbose > 2:
            self.message("spawnTourney: " + str(schedule))
        #
        # Accomodate with MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            tourney_serial = cursor.lastrowid
        else:
            tourney_serial = cursor.insert_id()
        if schedule['respawn'] == 'n':
            cursor.execute("UPDATE tourneys_schedule SET active = 'n' WHERE serial = %s" % schedule['serial'])
        cursor.execute("REPLACE INTO route VALUES (0,%s,%s,%s)", ( tourney_serial, int(seconds()), self.resthost_serial))
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
        if self.verbose > 2:
            self.message("deleteTourney: %d" % tourney.serial)
        self.schedule2tourneys[tourney.schedule_serial].remove(tourney)
        if len(self.schedule2tourneys[tourney.schedule_serial]) <= 0:
            del self.schedule2tourneys[tourney.schedule_serial]
        del self.tourneys[tourney.serial]

    def tourneyResumeAndDeal(self, tourney):
        self.tourneyBreakResume(tourney)
        self.tourneyDeal(tourney)

    def tourneyNewState(self, tourney, old_state, new_state):
        cursor = self.db.cursor()
        updates = [ "state = '" + new_state + "'" ]
        if old_state != TOURNAMENT_STATE_BREAK and new_state == TOURNAMENT_STATE_RUNNING:
            updates.append("start_time = %d" % tourney.start_time)
        sql = "update tourneys set " + ", ".join(updates) + " where serial = " + str(tourney.serial)
        if self.verbose > 2:
            self.message("tourneyNewState: " + sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
        cursor.close()
        if new_state == TOURNAMENT_STATE_BREAK:
            # When we are entering BREAK state for the first time, which
            # should only occur here in the state change operation, we
            # send the PacketPokerTableTourneyBreakBegin.  Note that this
            # code is here and not in tourneyBreakCheck() because that
            # function is called over and over again, until the break
            # finishes.  Note that tourneyBreakCheck() also sends a
            # PacketPokerGameMessage() with the time remaining, too.
            secsLeft = tourney.remainingBreakSeconds()
            if secsLeft == None:
                # eek, should I really be digging down into tourney's
                # member variables in this next assignment?
                secsLeft = tourney.breaks_duration
            resumeTime = time.time() + secsLeft
            # I saw at time of writing the above line that
            # tournament_seconds() returns time.time(), but I think I
            # actually *want* time.time() here since I'm expecting to send
            # the "real world" time.  Perhaps I've however misunderstood
            # the purpose of tournament_seconds()
            for gameId in map(lambda game: game.id, tourney.games):
                table = self.getTable(gameId)
                table.broadcast(PacketPokerTableTourneyBreakBegin(game_id = gameId, resume_time = resumeTime))
            self.tourneyBreakCheck(tourney)
        elif old_state == TOURNAMENT_STATE_BREAK and new_state == TOURNAMENT_STATE_RUNNING:
            wait = int(self.delays.get('extra_wait_tourney_break', 0))
            if wait > 0:
                reactor.callLater(wait, self.tourneyResumeAndDeal, tourney)
            else:
                self.tourneyResumeAndDeal(tourney)
        elif old_state == TOURNAMENT_STATE_REGISTERING and new_state == TOURNAMENT_STATE_RUNNING:
            # Only obey extra_wait_tourney_start if we had been registering and are now running,
            # since we only want this behavior before the first deal. 
            wait = int(self.delays.get('extra_wait_tourney_start', 0))
            if wait > 0:
                reactor.callLater(wait, self.tourneyDeal, tourney)
            else:
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
        for gameId in map(lambda game: game.id, tourney.games):
            table = self.getTable(gameId)
            table.broadcastMessage(PacketPokerGameMessage, "Tournament resumes")
            table.broadcast(PacketPokerTableTourneyBreakDone(game_id = gameId))

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
            if self.verbose > 2:
                self.message("tourneyFinished: bailor pays " + sql)
            cursor.execute(sql)
            if cursor.rowcount != 1: 
                self.error("tourneyFinished: bailor failed to provide requested money modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
                cursor.close()
                return False
            
        while prizes:
            prize = prizes.pop(0)
            serial = winners.pop(0)
            if prize <= 0:
                continue
            sql = "UPDATE user2money SET amount = amount + " + str(prize) + " WHERE user_serial = " + str(serial) + " AND currency_serial = " + str(tourney.currency_serial)
            if self.verbose > 2:
                self.message("tourneyFinished: " + sql)
            cursor.execute(sql)
            if cursor.rowcount == 0:
                sql = ( "INSERT INTO user2money (user_serial, currency_serial, amount) VALUES (%d, %d, %d)" %
                        ( serial, tourney.currency_serial, prize ) )
                if self.verbose > 2:
                    self.message("tourneyFinished: " + sql)
                cursor.execute(sql)
            self.databaseEvent(event = PacketPokerMonitorEvent.PRIZE, param1 = serial, param2 = tourney.currency_serial, param3 = prize)

        cursor.execute("DELETE FROM route WHERE tourney_serial = %s", tourney.serial)
        cursor.close()
        self.databaseEvent(event = PacketPokerMonitorEvent.TOURNEY, param1 = tourney.serial)
        finish = PacketPokerTourneyFinish(tourney_serial = tourney.serial)
        for serial in tourney.winners:
            client = self.serial2client.get(serial, None)
            if client:
                client.sendPacketVerbose(finish)
        return True

    def tourneyGameFilled(self, tourney, game):
        table = self.getTable(game.id)
        cursor = self.db.cursor()
        for player in game.playersAll():
            serial = player.serial
            player.setUserData(pokeravatar.DEFAULT_PLAYER_USER_DATA.copy())
            client = self.serial2client.get(serial, None)
            if client:
                if self.verbose > 2:
                    self.message("tourneyGameFilled: player %d connected" % serial)
                table.serial2client[serial] = client
            else:
                if self.verbose > 2:
                    self.message("tourneyGameFilled: player %d disconnected" % serial)
            self.seatPlayer(serial, game.id, game.buyIn())

            if client:
                # First, force a count increase, since this player will
                # now be at the table, but table.joinPlayer() was never
                # called (which is where the increase usually happens).
                self.joinedCountIncrease()
                client.join(table)
            sql = "update user2tourney set table_serial = %d where user_serial = %d and tourney_serial = %d" % ( game.id, serial, tourney.serial )
            if self.verbose > 4:
                self.message("tourneyGameFilled: " + sql)
            cursor.execute(sql)
            if cursor.rowcount != 1:
                self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
        cursor.close()
        table.update()

    def tourneyCreateTable(self, tourney):
        table = self.createTable(0, { 'name': tourney.name + str(self.tourney_table_serial),
                                      'variant': tourney.variant,
                                      'betting_structure': tourney.betting_structure,
                                      'seats': tourney.seats_per_game,
                                      'currency_serial': 0,
                                      'player_timeout': tourney.player_timeout,
                                      'transient': True,
                                      'tourney': tourney,
                                      })
        self.tourney_table_serial += 1
        table.timeout_policy = "fold"
        return table.game

    def tourneyDestroyGameActual(self, game):
        table = self.getTable(game.id)
        table.destroy()

    def tourneyDestroyGame(self, tourney, game):
        wait = int(self.delays.get('extra_wait_tourney_finish', 0))
        if wait > 0:
            reactor.callLater(wait, self.tourneyDestroyGameActual, game)
        else:
            self.tourneyDestroyGameActual(game)

    def tourneyMovePlayer(self, tourney, from_game_id, to_game_id, serial):
        from_table = self.getTable(from_game_id)
        from_table.movePlayer(from_table.serial2client.get(serial, None), serial, to_game_id)
        cursor = self.db.cursor()
        sql = "UPDATE user2tourney SET table_serial = %d WHERE user_serial = %d AND tourney_serial = %d" % ( to_game_id, serial, tourney.serial )
        if self.verbose > 4:
            self.message("tourneyMovePlayer: " + sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.message("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
            return False
        cursor.close()
        return True

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
        if self.verbose > 4:
            self.message("tourneyRemovePlayer: " + sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
        cursor.close()

    def tourneyManager(self, tourney_serial):
        packet = PacketPokerTourneyManager()
        packet.tourney_serial = tourney_serial
        cursor = self.db.cursor(DictCursor)
        cursor.execute("SELECT user_serial, table_serial, rank FROM user2tourney WHERE tourney_serial = %d" % tourney_serial)
        user2tourney = cursor.fetchall()

        table2serials = {}
        for row in user2tourney:
            table_serial = row['table_serial']
            if table_serial == None or table_serial == -1:
                continue
            if not table2serials.has_key(table_serial):
                table2serials[table_serial] = []
            table2serials[table_serial].append(row['user_serial'])
        packet.table2serials = table2serials
        user2money = {}
        if len(table2serials) > 0:
            cursor.execute("SELECT user_serial, money FROM user2table WHERE table_serial IN ( " + ",".join(map(lambda x: str(x), table2serials.keys())) + " )")
            for row in cursor.fetchall():
                user2money[row['user_serial']] = row['money']
                
        cursor.execute("SELECT user_serial, name FROM user2tourney, users WHERE user2tourney.tourney_serial = " + str(tourney_serial) + " AND user2tourney.user_serial = users.serial")
        user2name = dict((entry["user_serial"], entry["name"]) for entry in cursor.fetchall())

        cursor.execute("SELECT * FROM tourneys WHERE serial = " + str(tourney_serial));
        packet.tourney = cursor.fetchone()
        packet.tourney["registered"] = len(user2tourney)
        packet.tourney["rank2prize"] = None
        if self.tourneys.has_key(tourney_serial):
            packet.tourney["rank2prize"] = self.tourneys[tourney_serial].prizes()

        cursor.close()

        user2properties = {}
        for row in user2tourney:
            user_serial = row["user_serial"]
            money = user2money.has_key(user_serial) and user2money[user_serial] or -1
            user2properties[str(user_serial)] = {"name": user2name[user_serial],
                                                 "money": money,
                                                 "rank": row["rank"],
                                                 "table_serial": row["table_serial"]}
        packet.user2properties = user2properties

        return packet
        
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
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM tourneys WHERE state in ( %s, %s )", ( TOURNAMENT_STATE_RUNNING, TOURNAMENT_STATE_REGISTERING ))
        tourneys = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM user2tourney WHERE rank = -1")
        players = int(cursor.fetchone()[0])
        cursor.close()
        return ( players, tourneys )

    def tourneySelect(self, string):
        cursor = self.db.cursor(DictCursor)
        tourneys = filter(lambda schedule: schedule['respawn'] == 'n', self.tourneys_schedule.values()) + map(lambda tourney: tourney.__dict__, self.tourneys.values() )
        criterion = split(string, "\t")
        if string == '':
            cursor.execute("SELECT tourneys.*,COUNT(user2tourney.user_serial) AS registered FROM tourneys LEFT JOIN(user2tourney) ON(tourneys.serial = user2tourney.tourney_serial) GROUP BY tourneys.serial")
            result = cursor.fetchall()
            cursor.execute("SELECT * FROM tourneys_schedule WHERE respawn = 'n' AND active = 'y'")
            result += cursor.fetchall()
        elif len(criterion) > 1:
            ( currency_serial, type ) = criterion
            sit_n_go = type == 'sit_n_go' and 'y' or 'n'
            if currency_serial:
                cursor.execute("SELECT tourneys.*,COUNT(user2tourney.user_serial) AS registered FROM tourneys LEFT JOIN(user2tourney) ON(tourneys.serial = user2tourney.tourney_serial) WHERE currency_serial = %s AND sit_n_go = %s GROUP BY tourneys.serial", ( currency_serial, sit_n_go ))
                result = cursor.fetchall()
                cursor.execute("SELECT * FROM tourneys_schedule WHERE respawn = 'n' AND active = 'y' AND currency_serial = %s AND sit_n_go = %s", ( currency_serial, sit_n_go ))
                result += cursor.fetchall()
            else:
                cursor.execute("SELECT tourneys.*,COUNT(user2tourney.user_serial) AS registered FROM tourneys LEFT JOIN(user2tourney) ON(tourneys.serial = user2tourney.tourney_serial) WHERE sit_n_go = %s GROUP BY tourneys.serial", sit_n_go)
                result = cursor.fetchall()
                cursor.execute("SELECT * FROM tourneys_schedule WHERE respawn = 'n' AND active = 'y' AND sit_n_go = %s", sit_n_go)
                result += cursor.fetchall()
        else:
            cursor.execute("SELECT tourneys.*,COUNT(user2tourney.user_serial) AS registered FROM tourneys LEFT JOIN(user2tourney) ON(tourneys.serial = user2tourney.tourney_serial) WHERE name = %s GROUP BY tourneys.serial", string)
            result = cursor.fetchall()
            cursor.execute("SELECT * FROM tourneys_schedule WHERE respawn = 'n' AND active = 'y' AND name = %s", string)
            result += cursor.fetchall()
        cursor.close()
        return result

    def tourneyRegister(self, packet):
        serial = packet.serial
        tourney_serial = packet.game_id
        client = self.serial2client.get(serial, None)

        if not self.tourneys.has_key(tourney_serial):
            error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                code = PacketPokerTourneyRegister.DOES_NOT_EXIST,
                                message = "Tournament %d does not exist" % tourney_serial)
            self.error(error)
            if client: client.sendPacketVerbose(error)
            return False
        tourney = self.tourneys[tourney_serial]

        if tourney.isRegistered(serial):
            error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                code = PacketPokerTourneyRegister.ALREADY_REGISTERED,
                                message = "Player %d already registered in tournament %d " % ( serial, tourney_serial ) )
            self.error(error)
            if client: client.sendPacketVerbose(error)
            return False

        if not tourney.canRegister(serial):
            error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                code = PacketPokerTourneyRegister.REGISTRATION_REFUSED,
                                message = "Registration refused in tournament %d " % tourney_serial)
            self.error(error)
            if client: client.sendPacketVerbose(error)
            return False

        cursor = self.db.cursor()
        #
        # Buy in
        #
        currency_serial = tourney.currency_serial or 0
        withdraw = tourney.buy_in + tourney.rake
        if withdraw > 0:
            sql = ( "UPDATE user2money SET amount = amount - " + str(withdraw) +
                    " WHERE user_serial = " + str(serial) + " AND " +
                    "       currency_serial = " + str(currency_serial) + " AND " +
                    "       amount >= " + str(withdraw)
                    )
            if self.verbose > 1:
                self.message("tourneyRegister: %s" % sql)
            cursor.execute(sql)
            if cursor.rowcount == 0:
                error = PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                    code = PacketPokerTourneyRegister.NOT_ENOUGH_MONEY,
                                    message = "Not enough money to enter the tournament %d" % tourney_serial)
                if client: client.sendPacketVerbose(error)
                self.error(error)
                return False
            if cursor.rowcount != 1:
                self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
                if client:
                    client.sendPacketVerbose(PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER,
                                                         code = PacketPokerTourneyRegister.SERVER_ERROR,
                                                         message = "Server error"))
                return False
        self.databaseEvent(event = PacketPokerMonitorEvent.REGISTER, param1 = serial, param2 = currency_serial, param3 = withdraw)
        #
        # Register
        #
        sql = "INSERT INTO user2tourney (user_serial, tourney_serial) VALUES (%d, %d)" % ( serial, tourney_serial )
        if self.verbose > 4:
            self.message("tourneyRegister: " + sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("insert %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
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
        # Refund registration fees
        #
        currency_serial = tourney.currency_serial
        withdraw = tourney.buy_in + tourney.rake
        if withdraw > 0:
            sql = ( "UPDATE user2money SET amount = amount + " + str(withdraw) +
                    " WHERE user_serial = " + str(serial) + " AND " +
                    "       currency_serial = " + str(currency_serial) )
            if self.verbose > 1:
                self.message("tourneyUnregister: %s" % sql)
            cursor.execute(sql)
            if cursor.rowcount != 1:
                self.error("modified no rows (expected 1): %s " % sql)
                return PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                                   code = PacketPokerTourneyUnregister.SERVER_ERROR,
                                   message = "Server error : user_serial = %d and currency_serial = %d was not in user2money" % ( serial, currency_serial ))
            self.databaseEvent(event = PacketPokerMonitorEvent.UNREGISTER, param1 = serial, param2 = currency_serial, param3 = withdraw)
        #
        # Unregister
        #
        sql = "DELETE FROM user2tourney WHERE user_serial = %d AND tourney_serial = %d" % ( serial, tourney_serial )
        if self.verbose > 4:
            self.message("tourneyUnregister: " + sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("delete no rows (expected 1): %s " % sql)
            cursor.close()
            return PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                               code = PacketPokerTourneyUnregister.SERVER_ERROR,
                               message = "Server error : user_serial = %d and tourney_serial = %d was not in user2tourney" % ( serial, tourney_serial ))
        cursor.close()

        tourney.unregister(serial)

        return packet

    def tourneyCancel(self, tourney):
        if self.verbose > 1:
            self.message("tourneyCancel " + str(tourney.players))
        for serial in tourney.players:
            packet = self.tourneyUnregister(PacketPokerTourneyUnregister(game_id = tourney.serial,
                                                                         serial = serial))
            if packet.type == PACKET_ERROR:
                self.message("tourneyCancel: " + str(packet))

    def getHandSerial(self):
        cursor = self.db.cursor()
        cursor.execute("INSERT INTO hands (description) VALUES ('[]')")
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
            self.error("loadHand(%d) expected one row got %d" % ( hand_serial, cursor.rowcount ))
            cursor.close()
            return None
        (description,) = cursor.fetchone()
        cursor.close()
        try:
            history = eval(description.replace("\r",""))
            return history
        except:
            self.error("loadHand(%d) eval failed for %s" % ( hand_serial, description ))
            print_exc()
            return None

    def saveHand(self, description, hand_serial):
        (type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips) = description[0]
        cursor = self.db.cursor()

        sql = ( "update hands set " +
                " description = %s "
                " where serial = " + str(hand_serial) )
        if self.verbose > 1:
            self.message("saveHand: %s" % ( sql % description ))
        cursor.execute(sql, str(description))
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            self.error("modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql ))
            cursor.close()
            return

        sql = "insert into user2hand values "
        sql += ", ".join(map(lambda player_serial: "(%d, %d)" % ( player_serial, hand_serial ), player_list))
        if self.verbose > 1:
            self.message("saveHand: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != len(player_list):
            self.error("inserted %d rows (expected exactly %d): %s " % ( cursor.rowcount, len(player_list), sql ))


        cursor.close()

    def listHands(self, sql_list, sql_total):
        cursor = self.db.cursor()
        if self.verbose > 1:
            self.message("listHands: " + sql_list + " " + sql_total)
        cursor.execute(sql_list)
        hands = cursor.fetchall()
        cursor.execute(sql_total)
        total = cursor.fetchone()[0]
        cursor.close()
        return (total, map(lambda x: x[0], hands))

    def eventTable(self, table):
        table_serial = table.game.id
        if table.tourney:
            tourney_serial = table.tourney.serial
        else:
            tourney_serial = 0
        cursor = self.db.cursor()
        cursor.execute("REPLACE INTO route VALUES (%s,%s,%s,%s)", ( table_serial, tourney_serial, int(seconds()), self.resthost_serial))
        cursor.close()
        
    def statsTables(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM pokertables")
        tables = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user2table")        
        players = cursor.fetchone()[0]
        cursor.close()
        return ( players, tables )

    def listTables(self, string, serial):
        criterion = split(string, "\t")
        cursor = self.db.cursor(DictCursor)
        if string == '' or string == 'all':
            cursor.execute("SELECT * FROM pokertables")
        elif string == 'my':
            cursor.execute("SELECT pokertables.* FROM pokertables,user2table WHERE pokertables.serial = user2table.table_serial AND user2table.user_serial = %s", serial) 
        elif re.match("^[0-9]+$", string):
            cursor.execute("SELECT * FROM pokertables WHERE currency_serial = %s", string) 
        elif len(criterion) > 1:
            ( currency_serial, variant ) = criterion
            if currency_serial:
                cursor.execute("SELECT * FROM pokertables WHERE currency_serial = %s AND variant = %s", (currency_serial, variant)) 
            else:
                cursor.execute("SELECT * FROM pokertables WHERE variant = %s", variant) 
        else:
            cursor.execute("SELECT * FROM pokertables WHERE name = %s", string)
        result = cursor.fetchall()
        cursor.close()
        return result

    def setupResthost(self):
        resthost = self.settings.headerGetProperties("/server/resthost")
        if resthost:
            resthost = resthost[0]
            cursor = self.db.cursor()
            values = ( resthost['host'], resthost['port'], resthost['path'] )
            cursor.execute("SELECT serial FROM resthost WHERE host = %s AND port = %s AND path = %s", values)
            if cursor.rowcount > 0:
                self.resthost_serial = cursor.fetchone()[0]
            else:
                cursor.execute("INSERT INTO resthost (host, port, path) VALUES (%s, %s, %s)", values)
                self.resthost_serial = cursor.lastrowid
            cursor.execute("DELETE FROM route WHERE resthost_serial = %s", self.resthost_serial)
            cursor.close()
            
    def cleanupResthost(self):
        if self.resthost_serial:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM route WHERE resthost_serial = %s", self.resthost_serial)
            cursor.close()

    def packet2resthost(self, packet):
        if packet.type == PACKET_POKER_POLL:
            if packet.game_id <= 0:
                where = "tourney_serial = " + str(packet.tourney_serial)
            else:
                where = "tourney_serial = " + str(packet.tourney_serial) + " AND table_serial = " + str(packet.game_id)
        elif packet.type in ( PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST, PACKET_POKER_TOURNEY_REGISTER, PACKET_POKER_TOURNEY_UNREGISTER ):
            where = "tourney_serial = " + str(packet.game_id)
        elif hasattr(packet, "game_id"):
            where = "table_serial = " + str(packet.game_id)
        else:
            return None
        
        cursor = self.db.cursor()
        cursor.execute("SELECT host, port, path FROM route,resthost WHERE " +
                       " route.resthost_serial = resthost.serial AND " + where)
        if cursor.rowcount > 0:
            result = cursor.fetchone()
        else:
            result = None
        cursor.close()
        return result
        
    def cleanUp(self, temporary_users = ''):
        cursor = self.db.cursor()

        if len(temporary_users) > 2:
            sql = "delete session_history from session_history, users where session_history.user_serial = users.serial and users.name like '" + temporary_users + "%'"
            cursor.execute(sql)
            sql = "delete session from session, users where session.user_serial = users.serial and users.name like '" + temporary_users + "%'"
            cursor.execute(sql)
            sql = "DELETE FROM user2tourney USING user2tourney, users WHERE users.name like '" + temporary_users + "%' AND users.serial = user2tourney.user_serial"
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
        #
        # Trash uncompleted tournaments and refund the buyin but keep the
        # tournaments that are 'complete' or 'registering'n.
        # Tournaments in the 'registering' state for which the start time
        # is in the past are trashed.
        # Sit and go tournaments in the 'registering' state are trashed.
        #
        sql = ( "SELECT * FROM tourneys WHERE " +
                " ( state NOT IN ( 'registering', 'complete' ) OR " +
                "   ( state = 'registering' AND " +
                "     ( sit_n_go = 'y' OR start_time < (%d + 60) ) " +
                "   ) " +
                " ) " +
                " AND resthost_serial = %d" ) % ( seconds(), self.resthost_serial )
        if self.verbose > 2:
            self.message("cleanupTourneys: " + sql)
        cursor.execute(sql)
        for x in xrange(cursor.rowcount):
            row = cursor.fetchone()
            withdraw = row['buy_in']
            cursor1 = self.db.cursor()
            if row['buy_in'] > 0:
                sql = ( "UPDATE user2money,user2tourney SET amount = amount + " + str(row['buy_in']) +
                        " WHERE user2tourney.user_serial = user2money.user_serial AND " +
                        "       user2money.currency_serial = " + str(row['currency_serial']) + " AND " +
                        "       user2tourney.tourney_serial = " + str(row['serial']) )
                if self.verbose > 1:
                    self.message("cleanupTourneys: %s" % sql)
                cursor1.execute(sql)
            sql = "DELETE FROM tourneys WHERE serial = %d" % row['serial']
            if self.verbose > 1:
                self.message("cleanupTourneys: %s" % sql)
            cursor1.execute(sql)
            sql = "DELETE FROM user2tourney WHERE tourney_serial = %d" % row['serial']
            if self.verbose > 1:
                self.message("cleanupTourneys: %s" % sql)
            cursor1.execute(sql)
            cursor1.close()
        #
        # Restore tourney registrations after reboot
        #
        sql = ( "SELECT * FROM tourneys " +
                " WHERE " +
                "  state = 'registering' AND " +
                "  start_time > (%d + 60) AND " +
                "  resthost_serial = %d " ) % ( seconds(), self.resthost_serial )
        if self.verbose > 2:
            self.message("cleanupTourneys: " + sql)
        cursor.execute(sql)
        for x in xrange(cursor.rowcount):
            row = cursor.fetchone()
            if self.verbose >= 0: message = "cleanupTourneys: restoring %s(%s) with players" % ( row['name'], row['serial'],  )
            tourney = self.spawnTourneyInCore(row, row['serial'], row['schedule_serial'])
            cursor1 = self.db.cursor()
            sql = "SELECT user_serial FROM user2tourney WHERE tourney_serial = " + str(row['serial'])
            if self.verbose > 2:
                self.message("cleanupTourneys: " + sql)
            cursor1.execute(sql)
            for y in xrange(cursor1.rowcount):
                (serial,) = cursor1.fetchone()
                if self.verbose >= 0: message += " " + str(serial)
                tourney.register(serial)
                
            cursor1.execute(sql)
            cursor1.close()
            if self.verbose >= 0:
                self.message(message)
        cursor.close()

    def getMoney(self, serial, currency_serial):
        cursor = self.db.cursor()
        sql = ( "SELECT amount FROM user2money " +
                "       WHERE user_serial = " + str(serial) + " AND " +
                "             currency_serial = "  + str(currency_serial) )
        if self.verbose:
            self.message(sql)
        cursor.execute(sql)
        if cursor.rowcount > 1:
            self.error("getMoney(%d) expected one row got %d" % ( serial, cursor.rowcount ))
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
            self.error("getPlayerInfo(%d) expected one row got %d" % ( serial, cursor.rowcount ))
            return placeholder
        (name,skin_url,skin_outfit) = cursor.fetchone()
        if skin_outfit == None:
            skin_outfit = "random"
        cursor.close()
        return PacketPokerPlayerInfo(serial = serial,
                                     name = name,
                                     url = skin_url,
                                     outfit = skin_outfit)

    def getPlayerPlaces(self, serial):
        cursor = self.db.cursor()
        cursor.execute("SELECT table_serial FROM user2table WHERE user_serial = %s", serial)
        tables = map(lambda x: x[0], cursor.fetchall())
        cursor.execute("SELECT user2tourney.tourney_serial FROM user2tourney,tourneys WHERE user2tourney.user_serial = %s AND user2tourney.tourney_serial = tourneys.serial AND (tourneys.state = 'registering' OR tourneys.state = 'running' OR tourneys.state = 'break' OR  tourneys.state = 'breakwait')", serial)
        tourneys = map(lambda x: x[0], cursor.fetchall())
        cursor.close()
        return PacketPokerPlayerPlaces(serial = serial,
                                       tables = tables,
                                       tourneys = tourneys)

    def getPlayerPlacesByName(self, name):
        cursor = self.db.cursor()
        cursor.execute("SELECT serial FROM users WHERE name = %s", name)
        serial = cursor.fetchone()
        if serial == None:
            return PacketError(other_type = PACKET_POKER_PLAYER_PLACES)
        else:
            serial = serial[0]
        return self.getPlayerPlaces(serial)
    
    def getUserInfo(self, serial):
        cursor = self.db.cursor(DictCursor)

        sql = ( "SELECT rating,affiliate,email,name FROM users WHERE serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("getUserInfo(%d) expected one row got %d" % ( serial, cursor.rowcount ))
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
        if self.verbose:
            self.message(sql)
        cursor.execute(sql)
        for row in cursor:
            if not row['in_game']: row['in_game'] = 0
            if not row['points']: row['points'] = 0
            packet.money[row['currency_serial']] = ( row['amount'], row['in_game'], row['points'] )
        if self.verbose > 2:
            self.message("getUserInfo: " + str(packet))
        return packet

    def getPersonalInfo(self, serial):
        user_info = self.getUserInfo(serial)
        self.message("getPersonalInfo %s" % str(user_info))
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
            self.error("getPersonalInfo(%d) expected one row got %d" % ( serial, cursor.rowcount ))
            return PacketPokerPersonalInfo(serial = serial)
        (packet.firstname, packet.lastname, packet.addr_street, packet.addr_street2, packet.addr_zip, packet.addr_town, packet.addr_state, packet.addr_country, packet.phone, packet.gender, packet.birthdate) = cursor.fetchone()
        cursor.close()
        if not packet.gender: packet.gender = ''
        if not packet.birthdate: packet.birthdate = ''
        packet.birthdate = str(packet.birthdate)
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
            self.message("setPersonalInfo: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            self.error("setPersonalInfo: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql ))
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
        cursor.execute("SELECT serial FROM users WHERE name = '%s'" % packet.name)
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
            cursor.execute("SELECT serial FROM users WHERE email = '%s' " % packet.email)
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
                #
                # Impossible except for a sudden database corruption, because of the
                # above SQL statements
                #
                self.error("setAccount: insert %d rows (expected 1): %s " % ( cursor.rowcount, sql )) #pragma: no cover
                return PacketError(code = PacketPokerSetAccount.SERVER_ERROR, #pragma: no cover
                                   message = "inserted %d rows (expected 1)" % cursor.rowcount, #pragma: no cover
                                   other_type = packet.type) #pragma: no cover
            #
            # Accomodate for MySQLdb versions < 1.1
            #
            if hasattr(cursor, "lastrowid"):
                packet.serial = cursor.lastrowid
            else:
                packet.serial = cursor.insert_id()
            cursor.execute("INSERT INTO users_private (serial) VALUES ('%d')" % packet.serial)
        else:
            #
            # User exists, update name, password and email
            #
            (serial,) = cursor.fetchone()
            if serial != packet.serial:
                return PacketError(code = PacketPokerSetAccount.NAME_ALREADY_EXISTS,
                                   message = "user name %s already exists" % packet.name,
                                   other_type = packet.type)
            cursor.execute("SELECT serial FROM users WHERE email = '%s' and serial != %d" % ( packet.email, serial ))
            numrows = int(cursor.rowcount)
            if numrows > 0:
                return PacketError(code = PacketPokerSetAccount.EMAIL_ALREADY_EXISTS,
                                   message = "there already is another account with the email %s" % packet.email,
                                   other_type = packet.type)
            set_password = packet.password and ", password = '" + packet.password + "' " or ""
            sql = ( "UPDATE users SET "
                    " name = '" + packet.name + "', "
                    " email = '" + packet.email + "' " +
                    set_password +
                    " WHERE serial = " + str(packet.serial) )
            if self.verbose > 1:
                self.message("setAccount: %s" % sql)
            cursor.execute(sql)
            if cursor.rowcount != 1 and cursor.rowcount != 0:
                self.error("setAccount: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql ))
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
            self.message("setPlayerInfo: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            self.error("setPlayerInfo: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql ))
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
            self.error("getPlayerImage(%d) expected one row got %d" % ( serial, cursor.rowcount ))
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
            self.message("setPlayerInfo: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1 and cursor.rowcount != 0:
            self.error("setPlayerImage: modified %d rows (expected 1 or 0): %s " % ( cursor.rowcount, sql ))
            return False
        return True

    def getName(self, serial):
        if serial == 0:
            return "anonymous"

        cursor = self.db.cursor()
        sql = ( "select name from users where serial = " + str(serial) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("getName(%d) expected one row got %d" % ( serial, cursor.rowcount ))
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
            self.message("buyInPlayer: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 0 and cursor.rowcount != 2:
            self.error("modified %d rows (expected 0 or 2): %s " % ( cursor.rowcount, sql ))
        self.databaseEvent(event = PacketPokerMonitorEvent.BUY_IN, param1 = serial, param2 = table_id, param3 = withdraw)
        return withdraw

    def seatPlayer(self, serial, table_id, amount):
        status = True
        cursor = self.db.cursor()
        sql = ( "INSERT INTO user2table ( user_serial, table_serial, money) VALUES "
                " ( " + str(serial) + ", " + str(table_id) + ", " + str(amount) + " )" )
        if self.verbose > 1:
            self.message("seatPlayer: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("inserted %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
            status = False
        cursor.close()
        self.databaseEvent(event = PacketPokerMonitorEvent.SEAT, param1 = serial, param2 = table_id)
        return status

    def movePlayer(self, serial, from_table_id, to_table_id):
        money = -1
        cursor = self.db.cursor()
        sql = ( "SELECT money FROM user2table "
                "  WHERE user_serial = " + str(serial) + " AND "
                "        table_serial = " + str(from_table_id) )
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.message("movePlayer(%d) expected one row got %d" % ( serial, cursor.rowcount ))
        (money,) = cursor.fetchone()
        cursor.close()

        if money > 0:
            cursor = self.db.cursor()
            sql = ( "UPDATE user2table "
                    "  SET table_serial = " + str(to_table_id) +
                    "  WHERE user_serial = " + str(serial) + " and"
                    "        table_serial = " + str(from_table_id) )
            if self.verbose > 1:
                self.message("movePlayer: %s" % sql)
            cursor.execute(sql)
            if cursor.rowcount != 1:
                self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
                money = -1
            cursor.close()

        # HACK CHECK
#        cursor = self.db.cursor()
#        sql = ( "select sum(money), sum(bet) from user2table" )
#        cursor.execute(sql)
#        (total_money,bet) = cursor.fetchone()
#        if total_money + bet != 120000:
#            self.message("BUG(6) %d" % (total_money + bet))
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
               self.message("leavePlayer %s" % sql)
           cursor.execute(sql)
           if cursor.rowcount > 1:
                self.error("modified %d rows (expected 0 or 1): %s " % ( cursor.rowcount, sql ))
                status = False
        sql = ( "DELETE from user2table "
                " WHERE user_serial = " + str(serial) + " AND "
                "       table_serial = " + str(table_id) )
        if self.verbose > 1:
            self.message("leavePlayer %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
            status = False
        cursor.close()
        self.databaseEvent(event = PacketPokerMonitorEvent.LEAVE, param1 = serial, param2 = table_id)
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
            self.message("updatePlayerRake: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
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
            self.message("updatePlayerMoney: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("modified %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
            status = False
        cursor.close()

#         # HACK CHECK
#         cursor = self.db.cursor()
#         sql = ( "select sum(money), sum(bet) from user2table" )
#         cursor.execute(sql)
#         (money,bet) = cursor.fetchone()
#         if money + bet != 120000:
#             self.message("BUG(4) %d" % (money + bet))
#             os.abort()
#         cursor.close()

#         cursor = self.db.cursor()
#         sql = ( "select user_serial,table_serial,money from user2table where money < 0" )
#         cursor.execute(sql)
#         if cursor.rowcount >= 1:
#             (user_serial, table_serial, money) = cursor.fetchone()
#             self.message("BUG(11) %d/%d/%d" % (user_serial, table_serial, money))
#             os.abort()
#         cursor.close()
#         # END HACK CHECK

        return status

    def updateTableStats(self, game, observers, waiting):
        cursor = self.db.cursor()
        cursor.execute("UPDATE pokertables SET " +
                       " average_pot = %s, " + 
                       " hands_per_hour = %s, " + 
                       " percent_flop = %s, " + 
                       " players = %s, " + 
                       " observers = %s, " + 
                       " waiting = %s " +
                       " WHERE serial = %s ", (
            game.stats['average_pot'],
            game.stats['hands_per_hour'],
            game.stats['percent_flop'],
            game.allCount(),
            observers,
            waiting,
            game.id
            ))
        cursor.close()
        
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
#             self.message("BUG(10)")
#             os.abort()
#         cursor.close()
#         # END HACK CHECK

        cursor = self.db.cursor()
        sql = ( "delete from user2table "
                "  where table_serial = " + str(table_id) )
        if self.verbose > 1:
            self.message("destroy: %s" % sql)
        cursor.execute(sql)
        cursor.execute("DELETE FROM route WHERE table_serial = %s", table_id)

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
#             self.message("setRating: url = %s" % url + params)
#         content = loadURL(url + params)
#         if self.verbose > 2:
#             self.message("setRating: %s" % content)

    def resetBet(self, table_id):
        status = True
        cursor = self.db.cursor()
        sql = ( "update user2table set bet = 0 "
                " where table_serial = " + str(table_id) )
        if self.verbose > 1:
            self.message("resetBet: %s" % sql)
        cursor.execute(sql)
        cursor.close()

#         # HACK CHECK
#         cursor = self.db.cursor()
#         sql = ( "select sum(money), sum(bet) from user2table" )
#         cursor.execute(sql)
#         (money,bet) = cursor.fetchone()
#         if money + bet != 120000:
#             self.message("BUG(2) %d" % (money + bet))
#             os.abort()
#         cursor.close()
#         # END HACK CHECK

        return status

    def getTable(self, game_id):
        return self.tables.get(game_id, False)

    def createTable(self, owner, description):

        tourney_serial = 0
        if description.has_key('tourney'):
            tourney_serial = description['tourney'].serial

        cursor = self.db.cursor()
        sql = "INSERT pokertables ( resthost_serial, seats, player_timeout, muck_timeout, currency_serial, name, variant, betting_structure, skin, tourney_serial ) VALUES ( %s, %s, %s, %s, %s, %s,  %s, %s, %s, %s ) " % self.db.literal((
            self.resthost_serial,
            description['seats'],
            description.get('player_timeout', 60),
            description.get('muck_timeout', 5),
            description['currency_serial'],
            description['name'],
            description['variant'],
            description['betting_structure'],
            description.get('skin', 'default'),
            tourney_serial ))
        if self.verbose > 1:
            self.message("createTable: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("inserted %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
        if hasattr(cursor, "lastrowid"):
            id = cursor.lastrowid
        else:
            id = cursor.insert_id()
        cursor.execute("REPLACE INTO route VALUES (%s,%s,%s,%s)", ( id, tourney_serial, int(seconds()), self.resthost_serial))
        cursor.close()

        table = PokerTable(self, id, description)
        table.owner = owner

        self.tables[id] = table

        if self.verbose:
            self.message("table created : %s" % table.game.name)

        return table

    def cleanupCrashedTables(self):
        for description in self.settings.headerGetProperties("/server/table"):
            self.cleanupCrashedTable("pokertables.name = %s" % self.db.literal((description['name'],)))
        self.cleanupCrashedTable("pokertables.resthost_serial = %d" % self.resthost_serial)

    def cleanupCrashedTable(self, pokertables_where):
        cursor = self.db.cursor()

        sql = ( "SELECT user_serial,table_serial,currency_serial FROM pokertables,user2table WHERE user2table.table_serial = pokertables.serial AND " + pokertables_where )
        cursor.execute(sql)
        if cursor.rowcount > 0:
            if self.verbose > 1:
                self.message("cleanupCrashedTable found %d players on table %s" % ( cursor.rowcount, pokertables_where ))
            for i in xrange(cursor.rowcount):
                (user_serial, table_serial, currency_serial) = cursor.fetchone()
                self.leavePlayer(user_serial, table_serial, currency_serial)
        cursor.execute("DELETE FROM pokertables WHERE " + pokertables_where)

        cursor.close()

    def deleteTable(self, table):
        if self.verbose:
            self.message("table %s/%d removed from server" % ( table.game.name, table.game.id ))
        del self.tables[table.game.id]
        cursor = self.db.cursor()
        sql = ( "delete from  pokertables where serial = " + str(table.game.id) )
        if self.verbose > 1:
            self.message("deleteTable: %s" % sql)
        cursor.execute(sql)
        if cursor.rowcount != 1:
            self.error("deleted %d rows (expected 1): %s " % ( cursor.rowcount, sql ))
        cursor.close()

    def broadcast(self, packet):
        for avatar in self.avatars:
            if hasattr(avatar, "protocol") and avatar.protocol:
                avatar.sendPacketVerbose(packet)
            else:
                self.message("broadcast: avatar %s excluded" % str(avatar))

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
        self.putChild("REST", PokerREST(self.service))
        try:
            self.putChild("SOAP", PokerSOAP(self.service))
        except:
            print "SOAP service not available"
        self.putChild("", self)

    def render_GET(self, request):
        return "Use /RPC2 or /SOAP or /REST"

components.registerAdapter(PokerTree, IPokerService, resource.IResource)

class PokerRestTree(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.putChild("POKER_REST", PokerResource(self.service))
        self.putChild("UPLOAD", PokerImageUpload(self.service))
        self.putChild("AVATAR", PokerAvatarResource(self.service))
        self.putChild("", self)

    def render_GET(self, request):
        return "Use /POKER_REST"

def _getRequestCookie(request):
    if request.cookies:
        return request.cookies[0]
    else:
        return request.getCookie(join(['TWISTED_SESSION'] + request.sitepath, '_'))

#
# When connecting to the poker server with REST, SOAP or XMLRPC
# the client must chose to use sessions or not. If using session,
# the server will issue a cookie and keep track of it during
# (X == default twisted timeout) minutes.
#
# The session cookie is returned as a regular HTTP cookie and
# the library of the client in charge of the HTTP dialog should
# handle it transparently. To help the developer using a library
# that does a poor job at handling the cookies, it is also sent
# back as the "cookie" field of the PacketSerial packet in response
# to a successfull authentication request. This cookie may then
# be used to manually set the cookie header, for instance:
#
# Cookie: TWISTED_SESSION=a0bb35083c1ed3bef068d39bd29fad52; Path=/
#
# Because this cookie is only sent back in the SERIAL packet following
# an authentication request, it will not help clients observing the
# tables. These clients will have to find a way to properly handle the
# HTTP headers sent by the server.
#
# When the client sends a packet to the server using sessions, it must
# be prepared to receive the backlog of packets accumulated since the
# last request. For instance,
#
#   A client connects in REST session mode
#   The client sends POKER_TABLE_JOIN and the server replies with
#   packets describing the state of the table.
#   A player sitting at the table sends POKER_FOLD.
#   The server broadcasts the action to all players and observers.
#   Because the client does not maintain a persistent connection
#    and is in session mode, the server keeps the POKER_FOLD packet
#    for later.
#   The client sends PING to tell the server that it is still alive.
#   In response the server sends it the cached POKER_FOLD packet and
#    the client is informed of the action.
#
# The tests/test-webservice.py.in tests contain code that will help
# understand the usage of the REST, SOAP and XMLRPC protocols.
#
class PokerXML(resource.Resource):

    encoding = "ISO-8859-1"

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.verbose = service.verbose

    def message(self, string):
        print "PokerXML: " + string

    def error(self, string):
        self.message("*ERROR* " + string)
            
    def sessionExpires(self, session):
        self.service.destroyAvatar(session.avatar)
        del session.avatar

    def render(self, request):
        if self.verbose > 2:
            self.message("render " + request.content.read())
        request.content.seek(0, 0)
        if self.encoding is not None:
            mimeType = 'text/xml; charset="%s"' % self.encoding
        else:
            mimeType = "text/xml"
        request.setHeader("Content-type", mimeType)
        args = self.getArguments(request)
        if self.verbose > 2:
            self.message("args = " + str(args))
        session = None
        use_sessions = args[0]
        args = args[1:]
        if use_sessions == "use sessions":
            if self.verbose > 2:
                self.message("receive session cookie %s " % _getRequestCookie(request))
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
        for packet in args2packets(args):
            if isinstance(packet, PacketError):
                result_packets.append(packet)
                break
            else:
                results = avatar.handlePacket(packet)
                if use_sessions == "use sessions" and len(results) > 1:
                    for result in results:
                        if isinstance(result, PacketSerial):
                            result.cookie = _getRequestCookie(request)
                            if self.verbose > 2:
                                self.message("send session cookie " + result.cookie)
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
                result_maps = packets2maps([packet])

                result_string = self.maps2result(request, result_maps)
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
            elif use_sessions == "use sessions":
                if logout:
                    session.expire()
                else:
                    avatar.queuePackets()

            result_maps = packets2maps(result_packets)

            result_string = self.maps2result(request, result_maps)
            if self.verbose > 2:
                self.message("result_string " + str(result_string))
            request.setHeader("Content-length", str(len(result_string)))
            return result_string

    def getArguments(self, request):
        pass

    def maps2result(self, request, maps):
        pass

import xmlrpclib

class PokerXMLRPC(PokerXML):

    def getArguments(self, request):
        ( args, functionPath ) = xmlrpclib.loads(request.content.read())
        return fromutf8(args, self.encoding)

    def maps2result(self, request, maps):
        return xmlrpclib.dumps((maps, ), methodresponse = 1)

class PokerREST(PokerXML):

    def getArguments(self, request):
        use_sessions = request.args.get('session', ['no'])[0]
        session_name = request.args.get('name', [None])[0]
        if session_name:
            request.sitepath = [ session_name ]
        else:
            request.sitepath = [ ]

        if use_sessions == 'no':
            use_sessions = 'no sessions'
        elif use_sessions in ( 'clear', 'new' ):
            #
            # Force session expiration.
            # 
            # NOTE 1: that request.getSession() will create a session
            # if no session exists. However, since it is a light
            # weight operation that will be canceled by
            # session.expire(), it is ok.
            #
            # NOTE 2: the avatar attached to the session will be destroyed
            # as a side effect, because a callback was attached to the
            # session expiration.
            #
            request.getSession().expire()
            request.session = None
            request.cookies = []
            if use_sessions == 'clear':
                use_sessions = 'no sessions'
            elif use_sessions == 'new':
                use_sessions = 'use sessions'
        elif use_sessions == 'yes':
            use_sessions = 'use sessions'

        jsonp = request.args.get('jsonp', [''])[0]
        if jsonp:
            data = request.args.get('packet', [''])[0]
        else:
            data = request.content.read()
        args = simplejson.loads(data, encoding = 'latin-1')
        if hasattr(Packet.JSON, 'decode_objects'):
            args = Packet.JSON.decode_objects(args)
        return [ use_sessions, fromutf8(args, self.encoding) ]

    def maps2result(self, request, maps):
        jsonp = request.args.get('jsonp', [''])[0]
        if jsonp:
            return jsonp + '(' + str(Packet.JSON.encode(maps)) + ')'
        else:
            return str(Packet.JSON.encode(maps))

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

            return fromutf8(SOAPpy.simplify(args), self.encoding)

        def maps2result(self, request, maps):
            return SOAPpy.buildSOAP(kw = {'Result': toutf8(maps, self.encoding)},
                                    method = 'returnPacket',
                                    encoding = self.encoding)
except:
    print "Python SOAP module not available"
