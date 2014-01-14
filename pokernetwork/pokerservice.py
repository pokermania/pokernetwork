#
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2006, 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C)       2008, 2009 Bradley M. Kuhn <bkuhn@ebb.org>
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
#  Cedric Pinson <cpinson@freesheep.org> (2004-2006)

from os.path import exists
import re
import locale
import gettext

from contextlib import closing

try:
    from collections import OrderedDict
except ImportError:
    from pokernetwork.util.ordereddict import OrderedDict


from pokernetwork import log as network_log
log = network_log.get_child('pokerservice')

from twisted.application import service
from twisted.internet import protocol, reactor, defer
from pokernetwork.lockcheck import LockChecks
from twisted.python.runtime import seconds
from twisted.web import client

# disable noisy on HTTPClientFactory
client.HTTPClientFactory.noisy = False

try:
    __import__('OpenSSL.SSL')
    HAS_OPENSSL = True
except ImportError:
    HAS_OPENSSL = False

from zope.interface import Interface
from zope.interface import implements

from pokernetwork.util.sql import TimingDictCursor as DictCursor

from twisted.python import components

from pokernetwork.util.sql import lex

from pokerengine.pokertournament import *
from pokerengine.pokergame import GAME_STATE_NULL
from pokerengine.pokercards import PokerCards
from pokerengine import pokerprizes

from pokernetwork.server import PokerServerProtocol
from pokernetwork.user import checkName, checkPassword
from pokernetwork.pokerdatabase import PokerDatabase
from pokerpackets.packets import *
from pokerpackets.networkpackets import *
from pokernetwork.pokersite import PokerTourneyStartResource, PokerResource
from pokernetwork.pokertable import PokerTable, PokerAvatarCollection
from pokernetwork import pokeravatar
from pokernetwork.user import User
from pokernetwork import pokercashier
from pokernetwork import pokernetworkconfig
from pokernetwork import pokermemcache
from pokernetwork import pokerpacketizer
from pokerauth import get_auth_instance
from datetime import date

CANCEL_INACTIVE_TOURNEY_TIMEOUT = 60 * 60 * 3
INACTIVE_TOURNEY_CANCEL_POLL_DEALAY = 60 * 5
UPDATE_TOURNEYS_SCHEDULE_DELAY = 2 * 60
CHECK_TOURNEYS_SCHEDULE_DELAY = 60
DELETE_OLD_TOURNEYS_DELAY = 1 * 60 * 60


def _import(path):
    module = __import__(path)
    for i in path.split(".")[1:]:
        module = getattr(module, i)
    return module

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

    def createAvatar(self):
        """ """
        return self.service.createAvatar()

    def destroyAvatar(self, avatar):
        """ """
        return self.service.destroyAvatar(avatar)

    def setProtocol(self, protocol):
        self.protocol = protocol

components.registerAdapter(PokerFactoryFromPokerService, IPokerService, IPokerFactory)

class PokerService(service.Service):

    implements(IPokerService)
    _spawnTourney_currency_from_date_format_re = re.compile('(%[dHIjmMSUwWyY])+')

    STATE_OFFLINE = 0
    STATE_ONLINE = 1
    STATE_SHUTTING_DOWN = 2

    log = log.get_child('PokerService')
    
    def __init__(self, settings):
        if isinstance(settings, basestring):
            settings_object = pokernetworkconfig.Config(['.'])
            settings_object.loadFromString(settings)
            settings = settings_object
        self.settings = settings
        
        self.joined_max = self.settings.headerGetInt("/server/@max_joined")
        if self.joined_max <= 0: self.joined_max = 4000
        
        self.sng_timeout = self.settings.headerGetInt("/server/@sng_timeout")
        if self.sng_timeout <= 0: self.sng_timeout = 3600
        
        self.missed_round_max = self.settings.headerGetInt("/server/@max_missed_round")
        if self.missed_round_max <= 0: self.missed_round_max = 10
        
        self.client_queued_packet_max = self.settings.headerGetInt("/server/@max_queued_client_packets")
        if self.client_queued_packet_max <= 0: self.client_queued_packet_max = 500
        
        self.throttle = settings.headerGet('/server/@throttle') == 'yes'
        self.delays = settings.headerGetProperties("/server/delays")[0]
        
        refill = settings.headerGetProperties("/server/refill")
        self.refill = refill[0] if len(refill) > 0 else None
        self.db = None
        self.memcache = None
        self.cashier = None
        self.poker_auth = None
        self.timer = {}
        self.down = True
        self.shutdown_deferred = None
        self.resthost_serial = 0
        self.has_ladder = None
        self.monitor_plugins = [
            _import(path.content).handle_event
            for path in settings.header.xpathEval("/server/monitor")
        ]
        self.chat_filter = None
        self.remove_completed = settings.headerGetInt("/server/@remove_completed")
        self.getPage = client.getPage
        self.long_poll_timeout = settings.headerGetInt("/server/@long_poll_timeout")
        if self.long_poll_timeout <= 0: self.long_poll_timeout = 20
        #
        #
        self.temporary_users_cleanup = self.settings.headerGet("/server/@cleanup") == "yes" 
        self.temporary_users_pattern = '^'+settings.headerGet("/server/users/@temporary")+'$'
        self.temporary_serial_min = settings.headerGetInt("/server/users/@temporary_serial_min")
        self.temporary_serial_max = settings.headerGetInt("/server/users/@temporary_serial_max")

        #
        #badwords list
        chat_filter_filepath = settings.headerGet("/server/badwordschatfilter/@file")
        if chat_filter_filepath:
            self.setupChatFilter(chat_filter_filepath)
        #
        # tourney lock check
        self._lock_check_locked = False
        self._lock_check_running = None
        self._lock_check_break = None
        #
        # hand cache
        self.hand_cache = OrderedDict()

        self.timer_remove_player = {}

        # pubsub
        self.pub = None

    def setupLadder(self):
        with closing(self.db.cursor()) as c:
            c.execute("SHOW TABLES LIKE 'rank'")
            self.has_ladder = c.rowcount == 1
        return self.has_ladder

    def getLadder(self, game_id, currency_serial, user_serial):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT rank,percentile FROM rank WHERE currency_serial = %s AND user_serial = %s", ( currency_serial, user_serial ))
            if c.rowcount == 1:
                row = c.fetchone()
                packet = PacketPokerPlayerStats(
                    currency_serial = currency_serial,
                    serial = user_serial,
                    rank = row[0],
                    percentile = row[1]
                )
            else:
                packet = PacketPokerError(
                    serial = user_serial,
                    other_type = PACKET_POKER_PLAYER_STATS,
                    code = PacketPokerPlayerStats.NOT_FOUND,
                    message = "no ladder entry for player %d and currency %d" % ( user_serial, currency_serial )
                )
            if game_id:
                packet.game_id = game_id
            else:
                packet.game_id = 0
        return packet
        
    def setupTourneySelectInfo(self):
        #
        # load module that provides additional tourney information
        #
        self.tourney_select_info = None
        settings = self.settings
        for path in settings.header.xpathEval("/server/tourney_select_info"):
            self.log.inform("Trying to load '%s'", path.content)
            module = _import(path.content)
            path = settings.headerGet("/server/tourney_select_info/@settings")
            if path:
                s = pokernetworkconfig.Config(settings.dirs)
                s.load(path)
            else:
                s = None
            self.tourney_select_info = module.Handle(self, s)
            getattr(self.tourney_select_info, '__call__')

    def setupChatFilter(self, chat_filter_filepath):
        try:
            regExp = "(%s)" % "|".join(i.strip() for i in open(chat_filter_filepath,'r'))
            self.chat_filter = re.compile(regExp,re.IGNORECASE)
        except IOError, e:
            self.log.error("Could not access '%s': %s. Chat messages will not be filtered.", chat_filter_filepath, e.strerror)
        
    def startService(self):
        self.monitors = []
        self.db = PokerDatabase(self.settings)
        memcache_address = self.settings.headerGet("/server/@memcached")
        if memcache_address:
            self.memcache = pokermemcache.memcache.Client([memcache_address])
            pokermemcache.checkMemcacheServers(self.memcache)
        else:
            self.memcache = pokermemcache.MemcacheMockup.Client([])
        self.setupTourneySelectInfo()
        self.setupLadder()
        self.setupResthost()
        
        self.cashier = pokercashier.PokerCashier(self.settings)
        self.cashier.setDb(self.db)
        self.poker_auth = get_auth_instance(self.db, self.memcache, self.settings)
        self.dirs = self.settings.headerGet("/server/path").split()
        self.avatar_collection = PokerAvatarCollection("service")
        self.avatars = []
        self.tables = {}
        self.joined_count = 0
        self.tourney_table_serial = 1
        self.shutting_down = False
        self.simultaneous = self.settings.headerGetInt("/server/@simultaneous")
        self._keepalive_delay = self.settings.headerGetInt("/server/@ping")
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
                self.log.error('Unable to restore original locale: %s', le)

        self.cleanupCrashedTables()
        self.cleanupTourneys()
        if self.temporary_users_cleanup: self.cleanUpTemporaryUsers()
        
        self.updateTourneysSchedule()
        self.poker_auth.SetLevel(PACKET_POKER_SEAT, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_GET_USER_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_GET_PERSONAL_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_PLAYER_INFO, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_TOURNEY_REGISTER, User.REGULAR)
        self.poker_auth.SetLevel(PACKET_POKER_HAND_SELECT_ALL, User.ADMIN)
        self.poker_auth.SetLevel(PACKET_POKER_CREATE_TOURNEY, User.ADMIN)
        self.poker_auth.SetLevel(PACKET_POKER_TABLE, User.ADMIN)
        self.poker_auth.SetLevel(PACKET_POKER_CREATE_ACCOUNT, User.ADMIN)
        self.poker_auth.SetLevel(PACKET_POKER_SET_ACCOUNT, User.ADMIN)
        service.Service.startService(self)
        self.down = False

        self.timer['cancel_inactive_tourneys'] = reactor.callLater(INACTIVE_TOURNEY_CANCEL_POLL_DEALAY, self.cancelInactiveTourneys)

        # Setup Lock Check
        self._lock_check_running = LockChecks(5 * 60 * 60, self._warnLock)
        player_timeout = max(t.playerTimeout for t in self.tables.itervalues()) if self.tables else 20
        max_players = max(t.game.max_players for t in self.tables.itervalues()) if self.tables else 9
        len_rounds = (max(len(t.game.round_info) for t in self.tables.itervalues()) + 3) if self.tables else 8
        self._lock_check_break = LockChecks(
            player_timeout * max_players * len_rounds,
            self._warnLock
        )
        
    def loadTableConfig(self, serial):
        with closing(self.db.cursor()) as c:
            c.execute(lex(
                """ SELECT
                        c.name,
                        c.seats,
                        c.variant,
                        c.betting_structure,
                        c.currency_serial,
                        c.skin,
                        c.player_timeout,
                        c.muck_timeout
                    FROM tables as t
                    INNER JOIN tableconfigs as c
                        ON t.tableconfig_serial = c.serial
                    WHERE t.serial = %s AND t.resthost_serial = %s
                """),
                (serial, self.resthost_serial)
            )
            if c.rowcount == 1:
                return dict(zip([
                    'name',
                    'seats',
                    'variant',
                    'betting_structure',
                    'currency_serial',
                    'skin',
                    'player_timeout',
                    'muck_timeout'
                ], c.fetchone()))

    def despawnTable(self, serial):
        self.log.inform("Despawning table: %d", serial, refs=[('Game', self, lambda x: serial)])
        self.tables[serial].destroy()

    def spawnTable(self, serial, **kw):
        self.log.inform("Spawning table: %d", serial, refs=[('Game', self, lambda x: serial)])
        table = PokerTable(self, serial, kw)
        self.tables[serial] = table
        return table

    def createTable(self, owner, description):
        with closing(self.db.cursor()) as c:
            tourney = description.get('tourney')
            c.execute(lex(
                """ INSERT INTO tables
                    SET
                        resthost_serial = %s,
                        tourney_serial = %s
                """),
                (
                    self.resthost_serial,
                    tourney.serial if tourney else None
                )
            )
            if c.rowcount != 1:
                self.log.error("createTable: insert failed\n%s", c._executed)
                return None
            table = self.spawnTable(c.lastrowid, **description)
            table.owner = owner
            return table

    def stopServiceFinish(self):
        self.monitors = []
        if self.cashier: self.cashier.close()
        if self.db:
            self.cleanupCrashedTables()
            self.abortRunningTourneys()
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
        deferred.addCallback(lambda x: self.stopServiceFinish())
        return deferred

    def cancelTimer(self, key):
        if key in self.timer:
            self.log.debug("cancelTimer %s", key)
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

    def getClientQueuedPacketMax(self):
        return self.client_queued_packet_max

    def _separateCodesetFromLocale(self, lang_with_codeset):
        lang = lang_with_codeset
        codeset = ""
        dotLoc = lang.find('.')
        if dotLoc > 0:
            lang = lang_with_codeset[:dotLoc]
            codeset = lang_with_codeset[dotLoc+1:]

        if len(codeset) <= 0:
            self.log.error('Unable to find codeset string in language value: %s', lang_with_codeset)
        if len(lang) <= 0:
            self.log.error('Unable to find locale string in language value: %s', lang_with_codeset)
        return (lang, codeset)

    def _lookupTranslationFunc(self, lang_with_codeset):
        # Start by defaulting to just returning the string...
        myGetTextFunc = lambda text:text

        (lang, codeset) = self._separateCodesetFromLocale(lang_with_codeset)

# I now believe that changing the locale in this way for each language is
# completely uneeded given the set of features we are looking for.
# Ultimately, we aren't currently doing localization operations other than
# gettext() string lookup, so the need to actually switch locales does not
# exist.  Long term, we may want to format numbers properly for remote
# users, and then we'll need more involved locale changes, probably
# handled by avatar and stored in the server object.  In the meantime,
# this can be commented out and makes testing easier.  --bkuhn, 2008-11-28

#         try:
#             locale.setlocale(locale.LC_ALL, lang)
#         except locale.Error, le:
#             self.error('Unable to support locale, "%s", due to locale error: %s'
#                        % (lang_with_codeset, le))
#             return myGetTextFunc

        outputStr = "Aces"
        try:
            # I am not completely sure poker-engine should be hardcoded here like this...
            transObj = gettext.translation('poker-engine', languages=[lang], codeset=codeset)
            transObj.install()
            myGetTextFunc = transObj.gettext
            # This test call of the function *must* be a string in the
            # poker-engine domain.  The idea is to force a throw of
            # LookupError, which will be thrown if the codeset doesn't
            # exist.  Unfortunately, gettext doesn't throw it until you
            # call it with a string that it can translate (gibberish
            # doesn't work!).  We want to fail to support this
            # language/encoding pair here so the server can send the error
            # early and still support clients with this codec, albeit by
            # sending untranslated strings.
            outputStr = myGetTextFunc("Aces")
        except IOError, e:
            self.log.error("No translation for language %s for %s in "
                "poker-engine; locale ignored: %s",
                lang,
                lang_with_codeset,
                e
            )
            myGetTextFunc = lambda text:text
        except LookupError, l:
            self.log.error("Unsupported codeset %s for %s in poker-engine; locale ignored: %s",
                codeset,
                lang_with_codeset,
                l
            )
            myGetTextFunc = lambda text:text

        if outputStr == "Aces" and lang[0:2] != "en":
            self.log.error("Translation setup for %s failed.  Strings for clients "
                "requesting %s will likely always be in English",
                lang_with_codeset,
                lang
            )
        return myGetTextFunc

    def locale2translationFunc(self, locale, codeset = ""):
        if len(codeset) > 0:
            locale += "." + codeset
        if locale in self.gettextFuncs:
            return self.gettextFuncs[locale]
        else:
            self.log.warn("Locale, '%s' not available. %s must not have been "
                "provide via <language/> tag in settings, or errors occured during loading.",
                locale,
                locale
            )
            return None

    def shutdownLockChecks(self):
        if self._lock_check_break:
            self._lock_check_break.stopall()
        if self._lock_check_running:
            self._lock_check_running.stopall()
        
    def shutdownGames(self):
        #
        # happens when the service is not started and to accomodate tests 
        if not hasattr(self, "tables"):
            return
        
        tables = [t for t in self.tables.itervalues() if not t.game.isEndOrNull()]
        for table in tables:
            table.broadcast(PacketPokerStateInformation(
                game_id = table.game.id,
                code = PacketPokerStateInformation.SHUTTING_DOWN,
                message = "shutting down"
            ))
            for serial,avatars in table.avatar_collection.serial2avatars.items():
                for avatar in avatars:
                    #
                    # if the avatar uses a non-persistent connection, disconnect
                    # it, since it is impossible establish new connections while
                    # shutting down
                    if avatar._queue_packets:
                        table.quitPlayer(avatar)
                        
    
    def shutdown(self):
        self.shutting_down = True
        self.cancelTimer('checkTourney')
        self.cancelTimer('updateTourney')
        self.cancelTimer('messages')
        self.cancelTimers('tourney_breaks')
        self.cancelTimers('tourney_delete_route')
        self.cancelTimers('cancel_inactive_tourneys')

        if self.resthost_serial: self.setResthostOnShuttingDown()
        self.shutdownGames()
        self.shutdown_deferred = defer.Deferred()
        self.shutdown_deferred.addCallback(lambda res: self.shutdownLockChecks())
        reactor.callLater(0.01, self.shutdownCheck)
        return self.shutdown_deferred

    def shutdownCheck(self):
        if self.down:
            if self.shutdown_deferred:
                self.shutdown_deferred.callback(True)
            return

        playing = sum(1 for table in self.tables.itervalues() if not table.game.isEndOrNull())
        if playing > 0:
            self.log.warn('Shutting down, waiting for %d games to finish', playing)
        if playing <= 0:
            self.log.warn("Shutdown immediately")
            self.down = True
            self.shutdown_deferred.callback(True)
            self.shutdown_deferred = False
        else:
            reactor.callLater(2.0, self.shutdownCheck)

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
        for avatar in self.monitors:
            if hasattr(avatar, "protocol") and avatar.protocol:
                avatar.sendPacketVerbose(event)
        for plugin in self.monitor_plugins:
            plugin(self, event)

    def stats(self, query):
        return PacketPokerStats(
            players = len(self.avatars)
        )

    def createAvatar(self):
        avatar = pokeravatar.PokerAvatar(self)
        self.avatars.append(avatar)
        return avatar

    def forceAvatarDestroy(self, avatar):
#        self.destroyAvatar(avatar)
        reactor.callLater(0.1, self.destroyAvatar, avatar)

    def destroyAvatar(self, avatar):
        if avatar in self.avatars:
            self.avatars.remove(avatar)
        # if serial is 0 this avatar is already obsolete and may have been 
        # already removed from self.avatars in a distributed scenario
        elif avatar.getSerial() != 0: 
            self.log.warn("avatar %s is not in the list of known avatars", avatar)
        if avatar in self.monitors:
            self.monitors.remove(avatar)
        avatar.connectionLost("disconnected")

    def auth(self, auth_type, auth_args, roles):
        info, reason = self.poker_auth.auth(auth_type,auth_args)
        if info:
            self.autorefill(info[0])
        return info, reason

    def autorefill(self, serial):
        if not self.refill:
            return
        user_info = self.getUserInfo(serial)
        if int(self.refill['serial']) in user_info.money:
            money = user_info.money[int(self.refill['serial'])]
            missing = int(self.refill['amount']) - ( int(money[0]) + int(money[1]) )
            refill = int(money[0]) + missing if missing > 0 else 0
        else:
            refill = int(self.refill['amount'])
        if refill > 0:
            with closing(self.db.cursor()) as c:
                c.execute(lex(
                    """ INSERT INTO user2money (user_serial, currency_serial, amount)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE amount = %s
                    """),
                    (serial, self.refill['serial'], refill, refill)
                )
            self.databaseEvent(event = PacketPokerMonitorEvent.REFILL, param1 = serial, param2 = int(self.refill['serial']), param3 = refill)
        return refill

    def updateTourneysSchedule(self):
        self.log.debug("updateTourneysSchedule. (%s)" % self.resthost_serial)
        with closing(self.db.cursor(DictCursor)) as c:
            c.execute(lex(
                """ SELECT * FROM tourneys_schedule
                    WHERE
                        resthost_serial = %s AND
                        active = 'y' AND
                        (respawn = 'y' OR register_time < %s)
                """),
                (self.resthost_serial, seconds())
            )
            self.tourneys_schedule, tourneys_schedule_old = dict((schedule['serial'], schedule) for schedule in c.fetchall()), self.tourneys_schedule
            self.deleteObsoleteTourneys(set(tourneys_schedule_old) - set(self.tourneys_schedule))
            self.checkTourneysSchedule()
            self.cancelTimer('updateTourney')
            self.timer['updateTourney'] = reactor.callLater(UPDATE_TOURNEYS_SCHEDULE_DELAY, self.updateTourneysSchedule)

    def deleteObsoleteTourneys(self, tourneys_schedule_serials_obsolete):
        '''delete all tourneys that are associated with an obsolete tourney schedule serial'''
        
        if not tourneys_schedule_serials_obsolete: return
        
        with closing(self.db.cursor()) as c:
            format_in = ", ".join(["%s"] * len(tourneys_schedule_serials_obsolete))
            sql = \
                "SELECT serial FROM tourneys_schedule " \
                "WHERE resthost_serial != %%s " \
                "AND serial IN (%s)" % (format_in,)
            c.execute(sql, (self.resthost_serial,) + tuple(tourneys_schedule_serials_obsolete))
            for (schedule_serial,) in c.fetchall():
                for tourney in self.schedule2tourneys[schedule_serial]:
                    self.deleteTourney(tourney)
    
    def checkTourneysSchedule(self):
        self.log.debug("checkTourneysSchedule")
        now = seconds()

        # Cancel sng that stayed in registering state for too long
        for tourney in filter(lambda tourney: tourney.sit_n_go == 'y', self.tourneys.values()):
            if tourney.state == TOURNAMENT_STATE_REGISTERING and tourney.last_registered is not None and now - tourney.last_registered > self.sng_timeout:
                tourney.changeState(TOURNAMENT_STATE_CANCELED)

        # Respawning sit'n'go tournaments
        for schedule in filter(lambda schedule: schedule['respawn'] == 'y' and schedule['sit_n_go'] == 'y', self.tourneys_schedule.values()):
            schedule_serial = schedule['serial']
            if (
                schedule_serial not in self.schedule2tourneys or
                not filter(lambda tourney: tourney.state == TOURNAMENT_STATE_REGISTERING, self.schedule2tourneys[schedule_serial])
            ):
                self.spawnTourney(schedule)

        # Update tournaments with time clock
        for tourney in filter(lambda tourney: tourney.sit_n_go == 'n', self.tourneys.values()):
            tourney.updateRunning()
            
        # Forget about old tournaments
        for tourney in filter(lambda tourney: tourney.state in (TOURNAMENT_STATE_COMPLETE, TOURNAMENT_STATE_CANCELED), self.tourneys.values()):
            if now - tourney.finish_time > DELETE_OLD_TOURNEYS_DELAY:
                self.deleteTourney(tourney)
                self.tourneyDeleteRoute(tourney)

        # Restore tournaments
        self.restoreTourneys()
        
        # One time tournaments
        one_time = []
        for schedule in filter(lambda schedule: schedule['respawn'] == 'n' and int(schedule['register_time']) < now, self.tourneys_schedule.values()):
            one_time.append(schedule)
            del self.tourneys_schedule[schedule['serial']]
        for schedule in one_time:
            self.spawnTourney(schedule)
        
        # Respawning regular tournaments
        for schedule in filter(
            lambda schedule: schedule['respawn'] == 'y' and int(schedule['respawn_interval']) > 0 and schedule['sit_n_go'] == 'n',
            self.tourneys_schedule.values()
        ):
            schedule_serial = schedule['serial']
            schedule = schedule.copy()
            if schedule['start_time'] < now:
                start_time = int(schedule['start_time'])
                respawn_interval = int(schedule['respawn_interval'])
                intervals = max(0, int(1+(now-start_time)/respawn_interval))
                schedule['start_time'] += schedule['respawn_interval']*intervals
                schedule['register_time'] += schedule['respawn_interval']*intervals
            if schedule['register_time'] < now and (
                schedule_serial not in self.schedule2tourneys or
                not filter(
                    lambda tourney: tourney.start_time >= schedule['start_time'] 
                    ,self.schedule2tourneys[schedule_serial]
                )
            ):
                self.spawnTourney(schedule)
        
        self.cancelTimer('checkTourney')
        self.timer['checkTourney'] = reactor.callLater(CHECK_TOURNEYS_SCHEDULE_DELAY, self.checkTourneysSchedule)

    def today(self):
        return date.today()
    
    def spawnTourney(self, schedule):
        with closing(self.db.cursor()) as c:
            #
            # buy-in currency
            #
            currency_serial = schedule['currency_serial']
            currency_serial_from_date_format = schedule['currency_serial_from_date_format']
            if currency_serial_from_date_format:
                if not self._spawnTourney_currency_from_date_format_re.match(currency_serial_from_date_format):
                    raise UserWarning, "tourney_schedule.currency_serial_from_date_format format string %s does not match %s" % ( currency_serial_from_date_format, self._spawnTourney_currency_from_date_format_re.pattern )
                currency_serial = long(self.today().strftime(currency_serial_from_date_format))
            #
            # prize pool currency
            #
            prize_currency = schedule['prize_currency']
            prize_currency_from_date_format = schedule['prize_currency_from_date_format']
            if prize_currency_from_date_format:
                if not self._spawnTourney_currency_from_date_format_re.match(prize_currency_from_date_format):
                    raise UserWarning, "tourney_schedule.prize_currency_from_date_format format string %s does not match %s" % ( prize_currency_from_date_format, self._spawnTourney_currency_from_date_format_re.pattern )
                prize_currency = long(self.today().strftime(prize_currency_from_date_format))
            c.execute("INSERT INTO tourneys SET " + ", ".join("%s = %s" % (key, self.db.literal(val)) for key, val in {
                'resthost_serial': schedule['resthost_serial'],
                'schedule_serial': schedule['serial'],
                'name': schedule['name'],
                'description_short': schedule['description_short'],
                'description_long': schedule['description_long'],
                'players_quota': schedule['players_quota'],
                'players_min': schedule['players_min'],
                'variant': schedule['variant'],
                'betting_structure': schedule['betting_structure'],
                'skin': schedule['skin'],
                'seats_per_game': schedule['seats_per_game'],
                'player_timeout': schedule['player_timeout'],
                'currency_serial': currency_serial,
                'prize_currency': prize_currency,
                'prize_min': schedule['prize_min'],
                'bailor_serial': schedule['bailor_serial'],
                'buy_in': schedule['buy_in'],
                'rake': schedule['rake'],
                'sit_n_go': schedule['sit_n_go'],
                'breaks_first': schedule['breaks_first'],
                'breaks_interval': schedule['breaks_interval'],
                'breaks_duration': schedule['breaks_duration'],
                'rebuy_delay': schedule['rebuy_delay'],
                'add_on': schedule['add_on'],
                'add_on_delay': schedule['add_on_delay'],
                'inactive_delay': schedule['inactive_delay'],
                'start_time': schedule['start_time'],
                'via_satellite': schedule['via_satellite'],
                'satellite_of': schedule['satellite_of'],
                'satellite_player_count': schedule['satellite_player_count']
            }.iteritems()))
            self.log.debug("spawnTourney: %s", schedule)
            #
            # Accomodate with MySQLdb versions < 1.1
            #
            tourney_serial = c.lastrowid
            if schedule['respawn'] == 'n':
                c.execute("UPDATE tourneys_schedule SET active = 'n' WHERE serial = %s", (int(schedule['serial']),))
            c.execute("REPLACE INTO route VALUES (0,%s,%s,%s)", ( tourney_serial, int(seconds()), self.resthost_serial))
            return self.spawnTourneyInCore(schedule, tourney_serial, schedule['serial'], currency_serial, prize_currency)

    def spawnTourneyInCore(self, tourney_map, tourney_serial, schedule_serial, currency_serial, prize_currency):
        tourney_map['start_time'] = int(tourney_map['start_time'])
        if tourney_map['sit_n_go'] == 'y':
            tourney_map['register_time'] = int(seconds()) - 1
        else:
            tourney_map['register_time'] = int(tourney_map.get('register_time', 0))
        tourney = PokerTournament(dirs = self.dirs, **tourney_map)
        tourney.serial = tourney_serial
        tourney.schedule_serial = schedule_serial
        tourney.currency_serial = currency_serial
        tourney.prize_currency = prize_currency
        tourney.bailor_serial = tourney_map['bailor_serial']
        tourney.player_timeout = int(tourney_map['player_timeout'])
        tourney.via_satellite = int(tourney_map['via_satellite'])
        tourney.satellite_of = int(tourney_map['satellite_of'])
        tourney.satellite_of = self.tourneySatelliteLookup(tourney)[0]
        tourney.satellite_player_count = int(tourney_map['satellite_player_count'])
        tourney.satellite_registrations = []
        tourney._kickme_after = seconds() + CANCEL_INACTIVE_TOURNEY_TIMEOUT
        tourney.callback_new_state = self.tourneyNewState
        tourney.callback_create_game = self.tourneyCreateTable
        tourney.callback_game_filled = self.tourneyGameFilled
        tourney.callback_destroy_game = self.tourneyDestroyGame
        tourney.callback_move_player = self.tourneyMovePlayer
        tourney.callback_remove_player = self.tourneyRemovePlayerLater
        tourney.callback_cancel = self.tourneyCancel
        tourney.callback_reenter_game = self.tourneyReenterGame
        tourney.callback_rebuy_payment = self.tourneyRebuyPayment
        tourney.callback_rebuy = self.tourneyRebuy
        tourney.callback_user_action = self.tourneyIndicateUserAction
        tourney.callback_log_remove_inactive = self.tourneyLogRemoveInactive
        if schedule_serial not in self.schedule2tourneys:
            self.schedule2tourneys[schedule_serial] = []
        self.schedule2tourneys[schedule_serial].append(tourney)
        self.tourneys[tourney.serial] = tourney
        return tourney

    def deleteTourney(self, tourney):
        self.log.debug("deleteTourney: %d", tourney.serial)
        self.schedule2tourneys[tourney.schedule_serial].remove(tourney)
        if len(self.schedule2tourneys[tourney.schedule_serial]) <= 0:
            del self.schedule2tourneys[tourney.schedule_serial]
        del self.tourneys[tourney.serial]

    def tourneyResumeAndDeal(self, tourney):
        self.tourneyBreakResume(tourney)
        self.tourneyDeal(tourney)

    def _warnLock(self, tourney_serial):
        self._lock_check_locked = True
        self.log.warn("Tournament is locked! tourney_serial: %s", tourney_serial)

    def isLocked(self):
        return self._lock_check_locked

    def tourneySetUpLockCheck(self, tourney, old_state, new_state):
        if self._lock_check_running:
            if new_state == TOURNAMENT_STATE_RUNNING:
                if tourney.player_timeout < self._lock_check_running._timeout:
                    self._lock_check_running.start(tourney.serial)
            elif new_state == TOURNAMENT_STATE_COMPLETE:
                self._lock_check_running.stop(tourney.serial)
        if self._lock_check_break:
            if new_state == TOURNAMENT_STATE_BREAK_WAIT:
                self._lock_check_break.start(tourney.serial)
            elif new_state == TOURNAMENT_STATE_BREAK:
                self._lock_check_break.stop(tourney.serial)
    
    def tourneyIsRelevant(self, tourney):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT TRUE FROM tourneys WHERE serial = %s and resthost_serial = %s", (tourney.serial, self.resthost_serial))
            return c.rowcount > 0
    
    def tourneyDeleteWithSchedule(self, tourney):
        self.deleteTourney(tourney)
        if tourney.schedule_serial in self.tourneys_schedule:
            del self.tourneys_schedule[tourney.schedule_serial]
            
    def tourneyNewState(self, tourney, old_state, new_state):
        
        # if the tourney is not relevant for this resthost anymore, delete it and its schedule
        if old_state == TOURNAMENT_STATE_REGISTERING and not self.tourneyIsRelevant(tourney):
            self.tourneyDeleteWithSchedule(tourney)
            return
        #
        # set up lock check
        self.tourneySetUpLockCheck(tourney, old_state, new_state)
        
        updates = []
        updates.append("state = %s" % self.db.literal(new_state))
        if old_state != TOURNAMENT_STATE_BREAK and new_state == TOURNAMENT_STATE_RUNNING:
            updates.append("start_time = %s" % self.db.literal(tourney.start_time))

        params = (", ".join(updates), self.db.literal(tourney.serial)) 
        sql = "UPDATE tourneys SET %s WHERE serial = %s" % params
        self.log.debug("tourneyNewState: %s", sql)
        with closing(self.db.cursor()) as c:
            c.execute(sql)
            if c.rowcount != 1:
                self.log.error("modified %d rows (expected 1): %s", c.rowcount, c._executed)
        
        if new_state == TOURNAMENT_STATE_BREAK:
            # When we are entering BREAK state for the first time, which
            # should only occur here in the state change operation, we
            # send the PacketPokerTableTourneyBreakBegin.  Note that this
            # code is here and not in tourneyBreakCheck() because that
            # function is called over and over again, until the break
            # finishes.  Note that tourneyBreakCheck() also sends a
            # PacketPokerGameMessage() with the time remaining, too.
            secsLeft = tourney.remainingBreakSeconds()
            if secsLeft is None: secsLeft = tourney.breaks_duration
            resume_time = seconds() + secsLeft
            for game_id in tourney.id2game.iterkeys():
                table = self.getTable(game_id)
                table.broadcast(PacketPokerTableTourneyBreakBegin(game_id = game_id, resume_time = resume_time))
            self.tourneyBreakCheck(tourney)
        elif old_state == TOURNAMENT_STATE_BREAK and new_state == TOURNAMENT_STATE_RUNNING:
            wait = int(self.delays.get('extra_wait_tourney_break', 0))
            if wait > 0:
                reactor.callLater(wait, self.tourneyResumeAndDeal, tourney)
            else:
                self.tourneyResumeAndDeal(tourney)
        elif old_state == TOURNAMENT_STATE_REGISTERING and new_state == TOURNAMENT_STATE_RUNNING:
            tourney._kickme_after = seconds() + CANCEL_INACTIVE_TOURNEY_TIMEOUT
            self.databaseEvent(event = PacketPokerMonitorEvent.TOURNEY_START, param1 = tourney.serial)            
            reactor.callLater(0.01, self.tourneyBroadcastStart, tourney.serial)
            #
            # Only obey extra_wait_tourney_start if we had been registering and are now running,
            # since we only want this behavior before the first deal.
            wait_type = 'tourney' if tourney.sit_n_go != 'y' else 'sng'
            wait = int(self.delays.get('extra_wait_%s_start' % wait_type, 0))
            wait_msg_interval = 20
            if wait > 0:
                for remaining in range(wait-int(wait_msg_interval/2), 0, -wait_msg_interval):
                    reactor.callLater(remaining, self.tourneyStartingMessage, tourney, wait-remaining)
                reactor.callLater(wait, self.tourneyDeal, tourney)
            else:
                self.tourneyDeal(tourney)
        elif new_state == TOURNAMENT_STATE_RUNNING:
            self.tourneyDeal(tourney)
        elif new_state == TOURNAMENT_STATE_BREAK_WAIT:
            self.tourneyBreakWait(tourney)
        
    def tourneyStartingMessage(self,tourney,remaining):
        for game_id in tourney.id2game.keys():
            table = self.getTable(game_id)
            table.broadcastMessage(PacketPokerGameMessage, "Waiting for players.\nNext hand will be dealt shortly.\n(maximum %d seconds)" % remaining)
            
    def tourneyBreakCheck(self, tourney):
        key = 'tourney_breaks_%d' % id(tourney)
        self.cancelTimer(key)
        tourney.updateBreak()
        if tourney.state == TOURNAMENT_STATE_BREAK:
            self.timer[key] = reactor.callLater(int(self.delays.get('breaks_check', 30)), self.tourneyBreakCheck, tourney)

    def tourneyDeal(self, tourney):
        for game_id in tourney.id2game.keys():
            table = self.getTable(game_id)
            table.autodeal = self.getTableAutoDeal()
            table.scheduleAutoDeal()

    def tourneyBreakWait(self, tourney):
        return

    def tourneyBreakResume(self, tourney):
        for game in tourney.games:
            table = self.getTable(game.id)
            table.broadcast(PacketPokerTableTourneyBreakDone(game_id=game.id))

    def tourneyEndTurn(self, tourney, game_id):
        tourney.endTurn(game_id)
        self.tourneyFinishHandler(tourney, game_id)

    def tourneyUpdateStats(self,tourney,game_id):
        tourney.stats.update(game_id)

    def tourneyFinishHandler(self, tourney, game_id):
        if not tourney.tourneyEnd(game_id):
            self.tourneyFinished(tourney)
            self.tourneySatelliteWaitingList(tourney)

    def tourneyFinished(self, tourney):
        prizes = tourney.prizes()
        winners = tourney.winners[:len(prizes)]
        with closing(self.db.cursor()) as c:
            #
            # If prize_currency is non zero, use it instead of currency_serial
            #
            if tourney.prize_currency > 0:
                prize_currency = tourney.prize_currency
            else:
                prize_currency = tourney.currency_serial
            #
            # Guaranteed prize pool is withdrawn from a given account if and only if
            # the buy in of the players is not enough.
            #
            bail = tourney.prize_min - ( tourney.buy_in * tourney.registered )
            if bail > 0 and tourney.bailor_serial > 0:
                sql = "UPDATE user2money SET amount = amount - %s WHERE user_serial = %s AND currency_serial = %s AND amount >= %s"
                params = (bail,tourney.bailor_serial,prize_currency,bail)
                c.execute(sql,params)
                self.log.debug("tourneyFinished: bailor pays %s", c._executed)
                if c.rowcount != 1:
                    self.log.error("tourneyFinished: bailor failed to provide "
                        "requested money modified %d rows (expected 1): %s",
                        c.rowcount,
                        c._executed
                    )
                    return False

            while prizes:
                prize = prizes.pop(0)
                serial = winners.pop(0)
                if prize <= 0:
                    continue
                c.execute(
                    "UPDATE user2money SET amount = amount + %s WHERE user_serial = %s AND currency_serial = %s",
                    (prize,serial, prize_currency)
                )
                self.log.debug("tourneyFinished: %s", c._executed)
                if c.rowcount == 0:
                    c.execute(
                        "INSERT INTO user2money (user_serial, currency_serial, amount) VALUES (%s, %s, %s)",
                        (serial, prize_currency, prize)
                    )
                    self.log.debug("tourneyFinished: %s", c._executed)
                self.databaseEvent(event = PacketPokerMonitorEvent.PRIZE, param1 = serial, param2 = tourney.serial, param3 = prize)

            # FIXME added the following so that it wont break tests where the tournament mockup doesn't contain a finish_time
            if not hasattr(tourney, "finish_time"):
                tourney.finish_time = seconds()
            c.execute("UPDATE tourneys SET finish_time = %s WHERE serial = %s", (tourney.finish_time, int(tourney.serial)))
            self.databaseEvent(event = PacketPokerMonitorEvent.TOURNEY, param1 = tourney.serial)
            self.tourneyDeleteRoute(tourney)
            return True

    def tourneyDeleteRoute(self, tourney):
        key = 'tourney_delete_route_%d' % tourney.serial
        if key in self.timer: return
        wait = int(self.delays.get('extra_wait_tourney_finish', 0))
        def doTourneyDeleteRoute():
            self.cancelTimer(key)
            for serial in tourney.players:
                for player in self.avatar_collection.get(serial):
                    if tourney.serial in player.tourneys:
                        player.tourneys.remove(tourney.serial)
            self.tourneyDeleteRouteActual(tourney.serial)
        self.timer[key] = reactor.callLater(max(self._keepalive_delay*2, wait*2), doTourneyDeleteRoute)
        
    def tourneyDeleteRouteActual(self, tourney_serial):
        with closing(self.db.cursor()) as c:
            c.execute("DELETE FROM route WHERE tourney_serial = %s", tourney_serial)
    
    def tourneyGameFilled(self, tourney, game):
        table = self.getTable(game.id)
        with closing(self.db.cursor()) as c:
            for player in game.playersAll():
                serial = player.serial
                player.setUserData(pokeravatar.DEFAULT_PLAYER_USER_DATA.copy())
                self.seatPlayer(serial, game.id, game.buyIn())

                c.execute(lex(
                    """ UPDATE user2tourney SET table_serial = %s
                        WHERE
                            user_serial = %s AND
                            tourney_serial = %s
                    """),
                    (game.id, serial, tourney.serial)
                )
                self.log.debug("tourneyGameFilled: %s", c._executed)
                if c.rowcount != 1:
                    self.log.error("modified %d rows (expected 1): %s", c.rowcount, c._executed)
        table.update()

    def tourneyCreateTable(self, tourney):
        table = self.createTable(0, {
            'name': "%s (%s)" % (
                tourney.name,
                self.tourney_table_serial
            ),
            'variant': tourney.variant,
            'betting_structure': tourney.betting_structure,
            'skin': tourney.skin,
            'seats': tourney.seats_per_game,
            'currency_serial': 0,
            'player_timeout': tourney.player_timeout,
            'transient': True,
            'tourney': tourney
        })
        self.tourney_table_serial += 1
        table.autodeal = False
        return table.game

    def tourneyDestroyGameActual(self, game):
        table = self.getTable(game.id)
        tourney = table.tourney
        table.destroy()
        self.tourneyUpdateStats(tourney,game.id)

    def tourneyDestroyGame(self, tourney, game):
        wait = int(self.delays.get('extra_wait_tourney_finish', 0))
        if wait > 0: reactor.callLater(wait, self.tourneyDestroyGameActual, game)
        else: self.tourneyDestroyGameActual(game)

    def tourneyMovePlayer(self, tourney, from_game_id, to_game_id, serial):
        with closing(self.db.cursor()) as c:
            from_table = self.getTable(from_game_id)
            from_table.movePlayer(
                serial,
                to_game_id,
                reason = PacketPokerTable.REASON_TOURNEY_MOVE
            )
            c.execute(
                "UPDATE user2tourney SET table_serial = %s " \
                "WHERE user_serial = %s " \
                "AND tourney_serial = %s",
                (to_game_id, serial, tourney.serial)
            )
            self.log.debug("tourneyMovePlayer: %s", c._executed)
            if c.rowcount != 1:
                self.log.error("modified %d row (expected 1): %s", c.rowcount, c._executed)
                return False
            return True

    def tourneyReenterGame(self, tourney_serial, serial):
        self.log.debug('tourneyReenterGame tourney_serial(%d) serial(%d)', tourney_serial, serial)
        self.tourneyRemovePlayerTimer(tourney_serial, serial)

    def tourneyRemovePlayerLater(self, tourney, game_id, serial, now=False):
        table = self.getTable(game_id)
        avatars_seated = [avatar for avatar in self.avatar_collection.get(serial) if table.isSeated(avatar)]
        timeout_key = "%s_%s" % (tourney.serial,serial)
        for avatar in avatars_seated:
            table.sitOutPlayer(avatar)

        wait = 0 if now else max(0,int(self.delays.get('tourney_kick', 20)))
        
        if not wait and timeout_key in self.timer_remove_player:
            if self.timer_remove_player[timeout_key].active():
                self.timer_remove_player[timeout_key].cancel()
            del self.timer_remove_player[timeout_key]

        if wait: self.timer_remove_player[timeout_key] = reactor.callLater(wait, self.tourneyRemovePlayer, tourney, serial, now)
        else: self.tourneyRemovePlayer(tourney, serial, now)
    
    def tourneyRemovePlayer(self, tourney, serial, now=False):
        self.log.debug('remove now tourney(%d) serial(%d)', tourney.serial, serial)
        
        # if the player issued a rebuy, he will be removed at some later point in time
        if tourney.isRebuying(serial):
            return

        # delete the timer_remove_player entry
        if not now:
            self.tourneyRemovePlayerTimer(tourney.serial, serial)
        
        # the following line causes an IndexError if the player is not in any game. this is a good thing. 
        table = self.getTourneyTable(tourney, serial)
        
        table.kickPlayer(serial)
        tourney.finallyRemovePlayer(serial, now)
        
        with closing(self.db.cursor()) as c:
            prizes = tourney.prizes()
            rank = tourney.getRank(serial)
            players = len(tourney.players)
            money = 0
            if 0 <= rank-1 < len(prizes):
                money = prizes[rank-1]
            avatars = self.avatar_collection.get(serial)
            if avatars:
                packet = PacketPokerTourneyRank(
                    serial = tourney.serial,
                    game_id = table.game.id,
                    players = players,
                    rank = rank,
                    money = money
                )
                for avatar in avatars:
                    avatar.sendPacketVerbose(packet)
            self.databaseEvent(event = PacketPokerMonitorEvent.RANK, param1 = serial, param2 = tourney.serial, param3 = rank)
            c.execute(
                "UPDATE user2tourney " \
                "SET rank = %s, table_serial = -1 " \
                "WHERE user_serial = %s " \
                "AND tourney_serial = %s",
                (rank, serial, tourney.serial)
            )
            self.log.debug("tourneyRemovePlayer: %s", c._executed)
            if c.rowcount != 1:
                self.log.error("modified %d rows (expected 1): %s", c.rowcount, c._executed)
            self.tourneySatelliteSelectPlayer(tourney, serial, rank)
            self.tourneyUpdateStats(tourney,0)
        
        #
        # a player was removed - the tourney needs balancing.
        # if the table is not moving forward (i.e. only one player is sit on the table),
        # call the tourneyFinishHandler if the removal happened out of a normal call stack
        # and if the table is stationary
        tourney.need_balance = True
        if not now and table.isStationary():
            self.tourneyFinishHandler(tourney, table.game.id)

    def tourneyRemovePlayerTimer(self, tourney_serial, serial):
        timeout_key = "%s_%s" % (tourney_serial,serial)
        timer = self.timer_remove_player[timeout_key]
        if timer.active(): timer.cancel()
        del self.timer_remove_player[timeout_key]
    
    def tourneySatelliteLookup(self, tourney):
        if tourney.satellite_of == 0:
            return (0, None)
        found = None
        for candidate in self.tourneys.values():
            if candidate.schedule_serial == tourney.satellite_of:
                found = candidate
                break
        if found:
            if found.state != TOURNAMENT_STATE_REGISTERING:
                self.log.error(
                   "tourney %d is a satellite of %d but %d is in state %s instead of the expected state %s", 
                   tourney.serial,
                   found.schedule_serial,
                   found.schedule_serial,
                   found.state,
                   TOURNAMENT_STATE_REGISTERING 
                )
                return (0, TOURNAMENT_STATE_REGISTERING)
            return (found.serial, None)
        else:
            return (0, False)
                
    def tourneySatelliteSelectPlayer(self, tourney, serial, rank):
        if tourney.satellite_of == 0:
            return False
        if rank <= tourney.satellite_player_count:
            packet = PacketPokerTourneyRegister(serial = serial, tourney_serial = tourney.satellite_of)
            if self.tourneyRegister(packet = packet, via_satellite = True):
                tourney.satellite_registrations.append(serial)
        return True

    def tourneySatelliteWaitingList(self, tourney):
        """If the satellite did not register enough players, presumably because of a registration error
         for some of the winners (for instance if they were already registered), register the remaining
         players with winners that are not in the top satellite_player_count."""
        if tourney.satellite_of == 0:
            return False
        registrations = tourney.satellite_player_count - len(tourney.satellite_registrations)
        if registrations <= 0:
            return False
        serials = (serial for serial in tourney.winners if serial not in tourney.satellite_registrations)
        for serial in serials:
            packet = PacketPokerTourneyRegister(serial = serial, tourney_serial = tourney.satellite_of)
            if self.tourneyRegister(packet = packet, via_satellite = True):
                tourney.satellite_registrations.append(serial)
                registrations -= 1
                if registrations <= 0:
                    break
        return True

    def tourneyCreate(self, packet):
        #
        # I am using 'schedule' for the variable name of the tourney description to make it easier
        # to find and update this place when the structure of a tourney_schedule is changed in the
        # future.
        schedule = {
            'resthost_serial': self.resthost_serial,
            'serial': packet.schedule_serial, # this is infact the schedule serial
            'name': packet.name,
            'description_short': packet.description_short,
            'description_long': packet.description_long,
            'players_quota': packet.players_quota if packet.players_quota > len(packet.players) else len(packet.players),
            'players_min': 2,
            'variant': packet.variant,
            'betting_structure': packet.betting_structure,
            'skin': packet.skin,
            'seats_per_game': packet.seats_per_game,
            'player_timeout': packet.player_timeout,
            'currency_serial': packet.currency_serial,
            'prize_currency': packet.prize_currency,
            'prize_min': packet.prize_min,
            'bailor_serial': packet.bailor_serial,
            'buy_in': packet.buy_in,
            'rake': packet.rake,
            'sit_n_go': packet.sit_n_go,
            'breaks_first': packet.breaks_first,
            'breaks_interval': packet.breaks_interval,
            'breaks_duration': packet.breaks_duration,
            'rebuy_delay': 0,
            'add_on': 0,
            'add_on_delay': 0,
            'inactive_delay': 0,
            'start_time': int(seconds()),
            'via_satellite': 0,
            'satellite_of': 0,
            'satellite_player_count': 0,
            'currency_serial_from_date_format': "",
            'prize_currency_from_date_format': "",
            'respawn': "", # the tourney schedule row should not be updated, it might be possible that it doesn't even exist 
        }
        tourney = self.spawnTourney(schedule)
        tourney.updateRunning()
        register_packet = PacketPokerTourneyRegister(tourney_serial = tourney.serial)
        serial_failed = []
        for serial in packet.players:
            register_packet.serial = serial
            if not self.tourneyRegister(register_packet):
                serial_failed.append(serial)
            elif self.pub:
                # ugly, i know22
                def pub_create_tourney(serial, tourney):
                    for game in tourney.games:
                        if serial in game.serial2player:
                            self.pub.publish('user.%d.create_tourney' % (serial,), {'name': tourney.name, 'table_id': game.id})
                            break
                            
                reactor.callLater(1, pub_create_tourney, serial, tourney)

        if len(serial_failed) > 0:
            self.tourneyCancel(tourney)
            return PacketPokerError(
                game_id = packet.schedule_serial,
                serial = tourney.serial,
                other_type = PACKET_POKER_CREATE_TOURNEY,
                code = PacketPokerCreateTourney.REGISTRATION_FAILED,
                message = "registration failed for players %s in tourney %d" % (serial_failed, tourney.serial)
            )
        else:
            return PacketPokerTourney(**tourney.__dict__)

    def tourneyBroadcastStart(self, tourney_serial):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT host,port FROM resthost WHERE state = %s",(self.STATE_ONLINE))
            for host,port in c.fetchall():
                self.getPage('http://%s:%d/TOURNEY_START?tourney_serial=%d' % (host,long(port),tourney_serial))
        
    def tourneyNotifyStart(self, tourney_serial):
        manager = self.tourneyManager(tourney_serial)
        if manager.type != PACKET_POKER_TOURNEY_MANAGER:
            raise UserWarning, str(manager)
        user2properties = manager.user2properties
        
        calls = []
        def send(avatar_serial,table_serial):
            # get all avatars that are logged in and having an explain instance
            avatars = [a for a in self.avatar_collection.get(avatar_serial) if a.isLogged()]
            for avatar in avatars:
                avatar.sendPacket(PacketPokerTourneyStart(tourney_serial = tourney_serial,table_serial = table_serial))
                
        for avatar_serial,properties in user2properties.iteritems():
            avatar_serial = long(avatar_serial)
            table_serial = properties['table_serial']
            calls.append(reactor.callLater(0.1,send,avatar_serial,table_serial))
            
        return calls
    
    #TODO kill me! the implementation is pure hell, PacketPokerTourneyManager is a
    # dummy without attributes AND it's most likely not used since ages (pre binary protocol for shure)
    # so please make shure it's not used and beat it to death with a rusty hammer
    def tourneyManager(self, tourney_serial):
        packet = PacketPokerTourneyManager()
        packet.tourney_serial = tourney_serial
        with closing(self.db.cursor(DictCursor)) as c:
            c.execute("SELECT user_serial, table_serial, rank FROM user2tourney WHERE tourney_serial = %d" % tourney_serial)
            user2tourney = c.fetchall()

            table2serials = {}
            for row in user2tourney:
                table_serial = row['table_serial']
                if table_serial == None or table_serial == -1:
                    continue
                if table_serial not in table2serials:
                    table2serials[table_serial] = []
                table2serials[table_serial].append(row['user_serial'])
            packet.table2serials = table2serials
            user2money = {}
            if len(table2serials) > 0:
                c.execute("SELECT user_serial, money FROM user2table WHERE table_serial IN ( " + ",".join(map(str, table2serials.keys())) + " )")
                for row in c.fetchall():
                    user2money[row['user_serial']] = row['money']

            c.execute("SELECT user_serial, name FROM user2tourney, users WHERE user2tourney.tourney_serial = " + str(tourney_serial) + " AND user2tourney.user_serial = users.serial")
            user2name = dict((entry["user_serial"], entry["name"]) for entry in c.fetchall())

            c.execute("SELECT * FROM tourneys WHERE serial = %s",(tourney_serial,));
            if c.rowcount > 1:
                # This would be a bizarre case; unlikely to happen, but worth
                # logging if it happens.
                self.log.error("tourneyManager: tourney_serial(%d) has more than one "
                    "row in tourneys table, using first row returned",
                    tourney_serial
                )
            elif c.rowcount <= 0:
                # More likely to happen, so don't log it unless some verbosity
                # is requested.
                self.log.debug("tourneyManager: tourney_serial(%d) requested not "
                    "found in database, returning error packet",
                    tourney_serial
                )
                # Construct and return an error packet at this point.  I
                # considered whether it made more sense to return "None"
                # here and have avatar construct the Error packet, but it
                # seems other methods in pokerservice also construct error
                # packets already, so it seemed somewhat fitting.
                return PacketError(
                    other_type = PACKET_POKER_GET_TOURNEY_MANAGER,
                    code = PacketPokerGetTourneyManager.DOES_NOT_EXIST,
                    message = "Tournament %d does not exist" % tourney_serial
                )
            # Now we know we can proceed with taking the first row returned in
            # the cursor; there is at least one there.
            packet.tourney = c.fetchone()
            packet.tourney["registered"] = len(user2tourney)
            packet.tourney["rank2prize"] = None
            if tourney_serial in self.tourneys:
                packet.tourney["rank2prize"] = self.tourneys[tourney_serial].prizes()
            else:
                player_count = packet.tourney["players_quota"] \
                    if packet.tourney["sit_n_go"] == 'y' \
                    else packet.tourney["registered"]
                packet.tourney["rank2prize"] = pokerprizes.PokerPrizesTable(
                    buy_in_amount = packet.tourney['buy_in'],
                    guarantee_amount = packet.tourney['prize_min'],
                    player_count = player_count,
                    config_dirs = self.dirs
                ).getPrizes()

        user2properties = {}
        for row in user2tourney:
            user_serial = row["user_serial"]
            money = user_serial in user2money and user2money[user_serial] or -1
            user2properties[str(user_serial)] = {
                "name": user2name[user_serial],
                "money": money,
                "rank": row["rank"],
                "table_serial": row["table_serial"]
            }
        packet.user2properties = user2properties

        return packet

    def tourneyPlayersList(self, tourney_serial):
        if tourney_serial not in self.tourneys:
            return PacketError(
                other_type = PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST,
                code = PacketPokerTourneyRegister.DOES_NOT_EXIST,
                message = "Tournament %d does not exist" % tourney_serial
            )
        tourney = self.tourneys[tourney_serial]
        players = [(name,-1,0) for name in tourney.players.itervalues()]
        return PacketPokerTourneyPlayersList(tourney_serial = tourney_serial, players = players)

    def tourneyPlayerStats(self, tourney_serial, user_serial):
        tourney = self.tourneys.get(tourney_serial,None)
        if tourney is None:
            return PacketError(
                other_type = PACKET_POKER_GET_TOURNEY_PLAYER_STATS,
                code = PacketPokerGetTourneyPlayerStats.DOES_NOT_EXIST,
                message = "Tournament %d does not exist" % tourney_serial
            )
        stats = tourney.stats(user_serial)
        return PacketPokerTourneyPlayerStats(**stats)
    
    def tourneySelect(self, query_string):
        """ tourneySelect() takes one argument:
                query_string: a string that describes how the tourneys should be filtered

            1. If the string is empty, all tourneys are returned that are not completed
                or finished less than one hour agoi.
            2. If the string starts with filter, the string is splited at white space and 
                are interpreted as arguments as follows:
                    "-no-sng" will just show regular tourneys
                    "-sng" will just show sit and gos (ignoring strip poker games and challenges)
                    "-p<MINIMUM MINUTES>" e.g. -p5 sets the lower time limit to 5 minutes ago (defaul 0)
                    "-n<MAXIMUM MINUTES>" e.g. -n60 sets the upper time limit to one hour (default to 1440 =24h)

                    the time limit is used to find tournes that start between those minutes or start to
                    register between those values.
                    "-limit<MAX TOURNEYS>" limit the returned packets to this value
            3. Otherwise the tourneys with the name of the query_string are returned
        """
        cursor = self.db.cursor(DictCursor)
        try:
            criterion = query_string.split()
            if not criterion:
                criterion = ["__all__"]
            tourney_sql = \
                "SELECT t.*,COUNT(user2tourney.user_serial) AS registered FROM tourneys AS t " \
                "LEFT JOIN user2tourney ON (t.serial = user2tourney.tourney_serial) WHERE " 
            schedule_sql = "SELECT * FROM tourneys_schedule AS t WHERE "
            job = 'both'

            now = seconds()
            parameters = {
                "currency_serial": 1,
                "min_time": now,
                "max_time": now+24*3600,
                "limit": None
            }
            if criterion[0] == "filter":
                pass
            elif criterion[0] == "__all__":
                cursor.execute(tourney_sql + "(state != 'complete' OR (state = 'complete' AND finish_time > UNIX_TIMESTAMP(NOW() - INTERVAL 1 HOUR))) GROUP BY t.serial")
                return cursor.fetchall()
            else:
                cursor.execute(tourney_sql + "(state NOT IN ('complete', 'canceled') OR (state = 'complete' AND finish_time > UNIX_TIMESTAMP(NOW() - INTERVAL 1 HOUR))) AND name = %s  GROUP BY t.serial", (query_string))
                return cursor.fetchall()

            try:
                for option in criterion[1:]:
                    if option.startswith("-no-sng"):
                        job = "tourneys"
                    elif option.startswith("-sng"):
                        job = "sng"
                    elif option.startswith("-p"):
                        _seconds = int(option[2:])*60
                        parameters["min_time"] = now - _seconds
                    elif option.startswith("-n"):
                        _seconds = int(option[2:])*60
                        parameters["max_time"] = now + _seconds
                    elif option.startswith("-limit"):
                        parameters["limit"] = int(option[6:])
            except Exception as e:
                self.log.error("tourneySelect: can't handle query_string:%r")
                return []

            # getSchedules (Tourneys that will start registerin in ... minutes)
            # TODO: We need to catch all tourneys that are available to register now
            ret = []
            if job in ("both", "tourneys"):
                where_clause = lex("""
                    t.active = 'y' AND
                    t.respawn = 'n' AND
                    t.currency_serial = %(currency_serial)s AND
                    t.sit_n_go = 'n' AND
                    t.register_time BETWEEN %(min_time)s AND %(max_time)s
                    GROUP BY t.serial ORDER BY register_time
                """)
                self.log.inform("tourneySelect: %s", schedule_sql + where_clause % parameters)
                cursor.execute(schedule_sql + where_clause, parameters)
                ret.extend(cursor.fetchall())

                where_clause = lex("""
                    t.active = 'y' AND
                    t.respawn = 'y' AND
                    t.currency_serial = %(currency_serial)s AND
                    t.sit_n_go = 'n' AND
                    t.respawn_interval > 0
                    GROUP BY t.serial ORDER BY register_time 
                """)

                self.log.inform("tourneySelect: %s", schedule_sql + where_clause % parameters)
                cursor.execute(schedule_sql + where_clause, parameters)
                tourneys_schedules_respawn = cursor.fetchall()

                for schedule in tourneys_schedules_respawn:
                    if (schedule["start_time"] is not None and schedule["start_time"] < now):
                        time_delta = max(0, (1 + (now-schedule["start_time"]))//(schedule["respawn_interval"])) * schedule["respawn_interval"]
                        schedule["start_time"] += time_delta
                        schedule["register_time"] += time_delta

                    if (schedule["register_time"] is not None and schedule["register_time"] >= parameters["min_time"] and schedule["register_time"] <= parameters["max_time"]):
                        ret.append(schedule)

            # getTourneys (that are in registering/running/break/breakt wait, or ended x min ago)
            # sng stuff
            sng_y = lex("""
                t.sit_n_go="y" AND
                t.bailor_serial=0 AND
                t.state NOT IN ("complete","canceled","aborted","moved") AND
                t.name NOT LIKE "Strippoker%%"
            """)
            # $crit->addBetweenCondition('t.start_time', strtotime('-3 hours'), $tsInterval['max']);
            sng_n =  lex("""
                t.sit_n_go="n" AND (
                    t.state NOT IN ("complete","canceled","aborted") OR
                    (t.state = "complete" AND t.finish_time > UNIX_TIMESTAMP(NOW() - INTERVAL 12 HOUR))
                ) AND 
                t.currency_serial = 1 AND
                t.start_time BETWEEN %(min_time)s AND %(max_time)s
            """)
            # even if we want to select all tourneys and sngs, we still don't want to select challenges or Strippoker games
            sng_both = " (%s) OR (%s) " % (sng_y, sng_n)

            sql = {
                'sng': sng_y,
                'tourneys': sng_n,
                'both': sng_both
            }[job] + " GROUP BY t.serial"


            self.log.inform("tourneySelect: %s", tourney_sql + sql%parameters)
            cursor.execute(tourney_sql + sql, parameters)
            ret.extend(cursor.fetchall())
            ret = [e for e in ret if e['serial'] is not None]
            sortfn = lambda x:(x.get("register_time"), x["start_time"])
            if job == "sng":
                sortfn = lambda x:(x['buy_in'], x['rake'], x['players_quota'])
            tourneys_schedules = sorted(ret, key=sortfn)
            return tourneys_schedules[:parameters["limit"]]
        finally:
            cursor.close()
    def tourneySelectInfo(self, packet, tourneys):
        if self.tourney_select_info:
            return self.tourney_select_info(self, packet, tourneys)
        else:
            return None
    
    def tourneyRegister(self, packet, via_satellite=False):
        serial = packet.serial
        tourney_serial = packet.tourney_serial
        avatars = self.avatar_collection.get(serial)
        tourney = self.tourneys.get(tourney_serial,None)
        if tourney is None:
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY_REGISTER,
                code = PacketPokerTourneyRegister.DOES_NOT_EXIST,
                message = "Tournament %d does not exist" % tourney_serial
            )
            self.log.error("%s", error)
            for avatar in avatars:
                avatar.sendPacketVerbose(error)
            return False
        
        if tourney.via_satellite and not via_satellite:
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY_REGISTER,
                code = PacketPokerTourneyRegister.VIA_SATELLITE,
                message = "Player %d must register to %d via a satellite" % ( serial, tourney_serial ) 
            )
            self.log.error("%s", error)
            for avatar in avatars:
                avatar.sendPacketVerbose(error)
            return False
            
        if tourney.isRegistered(serial):
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY_REGISTER,
                code = PacketPokerTourneyRegister.ALREADY_REGISTERED,
                message = "Player %d already registered in tournament %d" % ( serial, tourney_serial )
            )
            self.log.inform("%s", error)
            for avatar in avatars:
                avatar.sendPacketVerbose(error)
            return False

        if not tourney.canRegister(serial):
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY_REGISTER,
                code = PacketPokerTourneyRegister.REGISTRATION_REFUSED,
                message = "Registration refused in tournament %d" % tourney_serial
            )
            self.log.inform("%s", error)
            for avatar in avatars:
                avatar.sendPacketVerbose(error)
            return False

        if not self.tourneyIsRelevant(tourney):
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY_REGISTER,
                code = PacketPokerTourneyRegister.REGISTRATION_REFUSED,
                message = "Registration refused in tournament %d (may be moved to another resthost)" % tourney_serial
            )
            for avatar in avatars:
                avatar.sendPacketVerbose(error)
            return False

        with closing(self.db.cursor()) as c:

            # Buy in
            currency_serial = tourney.currency_serial or 0
            withdraw = tourney.buy_in + tourney.rake
            if withdraw > 0:
                c.execute(lex(
                    """ UPDATE user2money
                        SET amount = amount - %s
                        WHERE
                            user_serial = %s AND
                            currency_serial = %s AND
                            amount >= %s
                    """),
                    (withdraw, serial, currency_serial, withdraw)
                )
                self.log.debug("tourneyRegister: %s" % (c._executed,))
                if c.rowcount == 0:
                    error = PacketError(
                        other_type = PACKET_POKER_TOURNEY_REGISTER,
                        code = PacketPokerTourneyRegister.NOT_ENOUGH_MONEY,
                        message = "Not enough money to enter the tournament %d" % tourney_serial
                    )
                    self.log.inform("%s", error)
                    for avatar in avatars:
                        avatar.sendPacketVerbose(error)
                    return False
                if c.rowcount != 1:
                    error = PacketError(
                        other_type = PACKET_POKER_TOURNEY_REGISTER,
                        code = PacketPokerTourneyRegister.SERVER_ERROR,
                        message = "Server error"
                    )
                    self.log.error("modified %d rows (expected 1): %s", c.rowcount, c._executed)
                    for avatar in avatars:
                        avatar.sendPacketVerbose(error)
                    return False
            self.databaseEvent(event = PacketPokerMonitorEvent.REGISTER, param1 = serial, param2 = tourney_serial, param3 = withdraw)

            # Register
            sql = "INSERT INTO user2tourney (user_serial, currency_serial, tourney_serial) VALUES (%s, %s, %s)"
            params = (serial, currency_serial, tourney_serial)
            c.execute(sql,params)
            self.log.debug("tourneyRegister: %s", c._executed)
            if c.rowcount != 1:
                error = PacketError(
                    other_type = PACKET_POKER_TOURNEY_REGISTER,
                    code = PacketPokerTourneyRegister.SERVER_ERROR,
                    message = "Server error"
                )
                self.log.error("insert %d rows (expected 1): %s", c.rowcount, c._executed)
                for avatar in avatars:
                    avatar.sendPacketVerbose(error)
                return False

        # Notify success
        for avatar in avatars:
            avatar.sendPacketVerbose(packet)

        tourney.register(serial,self.getName(serial))
        info_packet = PacketPokerTourneyInfo(**tourney.__dict__)
        for avatar in avatars:
            avatar.sendPacketVerbose(info_packet)

        return True

    def tourneyUnregister(self, packet, force=False):
        serial = packet.serial
        tourney_serial = packet.tourney_serial
        if tourney_serial not in self.tourneys:
            return PacketError(
                other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                code = PacketPokerTourneyUnregister.DOES_NOT_EXIST,
                message = "Tournament %d does not exist" % tourney_serial
            )
        tourney = self.tourneys[tourney_serial]

        if not tourney.isRegistered(serial):
            return PacketError(
                other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                code = PacketPokerTourneyUnregister.NOT_REGISTERED,
                message = "Player %d is not registered in tournament %d " % (serial, tourney_serial) 
            )

        if not tourney.canUnregister(serial, force):
            return PacketError(
                other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                code = PacketPokerTourneyUnregister.TOO_LATE,
                message = "It is too late to unregister player %d from tournament %d " % (serial, tourney_serial) 
            )

        with closing(self.db.cursor()) as c:
            #
            # Refund registration fees
            #
            currency_serial = tourney.currency_serial
            refund = tourney.buy_in + tourney.rake
            if refund > 0:
                c.execute(
                    "UPDATE user2money SET amount = amount + %s " \
                    "WHERE user_serial = %s " \
                    "AND currency_serial = %s",
                    (refund,serial,currency_serial)
                )
                self.log.debug("tourneyUnregister: %s", c._executed)
                if c.rowcount != 1:
                    self.log.error("modified no rows (expected 1): %s", c._executed)
                    return PacketError(
                        other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                        code = PacketPokerTourneyUnregister.SERVER_ERROR,
                        message = "Server error : user_serial = %d and currency_serial = %d was not in user2money" % (serial,currency_serial)
                    )
                self.databaseEvent(event = PacketPokerMonitorEvent.UNREGISTER, param1 = serial, param2 = tourney_serial, param3 = refund)
            #
            # unregister
            c.execute("DELETE FROM user2tourney WHERE user_serial = %s AND tourney_serial = %s", (serial,tourney_serial))
            self.log.debug("tourneyUnregister: %s", c._executed)
            if c.rowcount != 1:
                self.log.error("delete no rows (expected 1): %s", c._executed)
                return PacketError(
                    other_type = PACKET_POKER_TOURNEY_UNREGISTER,
                    code = PacketPokerTourneyUnregister.SERVER_ERROR,
                    message = "Server error : user_serial = %d and tourney_serial = %d was not in user2tourney" % (serial, tourney_serial)
                )

        tourney.unregister(serial)

        return packet

    def tourneyStart(self, tourney):
        '''start a registering tourney immediately.
        
        if more than one player is registered, players_min and quota is set to the
        amount of the currently registered players.
        '''
        now = int(seconds())
        with closing(self.db.cursor()) as c:
            c.execute(
                "UPDATE tourneys SET start_time=%s, players_min=%s, players_quota=%s WHERE serial=%s",
                (now, tourney.registered, tourney.registered, tourney.serial)
            )
        tourney.start_time = now
        tourney.players_min = tourney.players_quota = tourney.registered
        tourney.updateRunning()
        return PacketAck()

    def tourneyCancel(self, tourney, force=False):
        players = list(tourney.players.iterkeys())
        self.log.debug("tourneyCancel: %s", players)
        self.databaseEvent(event = PacketPokerMonitorEvent.TOURNEY_CANCELED, param1 = tourney.serial)
        for serial in players:
            avatars = self.avatar_collection.get(serial)
            if force:
                table = self.getTourneyTable(tourney, serial)
                # since the game will be destroyed shortly we can mess with the internal state
                table.game.state = GAME_STATE_NULL
                self.tourneyRemovePlayer(tourney, serial, now=True)
                for avatar in avatars:
                    table.quitPlayer(avatar)
            packet = self.tourneyUnregister(PacketPokerTourneyUnregister(
                tourney_serial = tourney.serial,
                serial = serial
            ), force)
            if packet.type == PACKET_ERROR:
                self.log.debug("tourneyCancel: %s", packet)
            for avatar in avatars:
                avatar.sendPacketVerbose(packet)

    
    def tourneyRebuyPayment(self, tournament, serial, table_serial, player_chips, tourney_chips):
        """decrements the bank money of a player
        amount is the number of chips which the player has to pay to get a new set of tourney chips

        returns the amount of tourney chips that the player should get additionally on the table
        if error is False, the reason indicates the problem
        """
        with closing(self.db.cursor()) as c:
            currency_serial = tournament.currency_serial
            c.execute(
               "UPDATE user2money,user2table,user2tourney SET " \
               "user2table.money = user2table.money + %s, " \
               "user2money.amount = user2money.amount - %s, " \
               "user2tourney.rebuy_count = user2tourney.rebuy_count + 1 " \
               "WHERE user2table.user_serial = %s " \
               "AND user2table.table_serial = %s " \
               "AND user2tourney.user_serial = %s " \
               "AND user2tourney.tourney_serial = %s " \
               "AND user2money.user_serial = %s " \
               "AND user2money.currency_serial = %s " \
               "AND user2money.amount >= %s",
               (tourney_chips, player_chips, serial, table_serial, serial, tournament.serial, serial, currency_serial, player_chips)
            )

            if c.rowcount not in (0,3): 
                self.log.warn("modified %d rows (expected 3): %s", c.rowcount, c._executed)
                return -1
            
            return tourney_chips if c.rowcount == 3 else -1

    def tourneySerialsRebuying(self, tournament, game_id):
        return tournament.serialsRebuying(game_id)
    
    def tourneyRebuyRequest(self, tourney_serial, serial):
        tourney = self.tourneys.get(tourney_serial)
        
        if tourney is None:
            self.log.warn("tourney_serial %d does not exist" % tourney_serial)
            return False, None

        table = self.getTourneyTable(tourney, serial)
        success, error = tourney.rebuyPlayerRequest(table.game.id, serial)
        return success, pokerpacketizer.tourneyErrorToPacketError(error) if error else 0
    
    def tourneyRebuyAllPlayers(self, tournament, game_id):
        tournament.rebuyAllPlayers(game_id)
        
    def tourneyRebuy(self, tournament, serial, table_serial, success, error):
        table = self.tables[table_serial]
        
        if not success:
            timeout_key = "%s_%s" % (tournament.serial, serial)
            timer = self.timer_remove_player.get(timeout_key, None)
            if not timer or not timer.active():
                # timer is not there anymore or was already called
                self.tourneyRemovePlayer(tournament, serial, now=True)
        
            packet = PacketError(
                serial = serial,
                other_type = PACKET_POKER_TOURNEY_REBUY,
                code = pokerpacketizer.tourneyErrorToPacketError(error) if error else 0                                 
            )
            
            avatars = table.avatar_collection.get(serial)
            for avatar in avatars:
                avatar.sendPacket(packet)
                
        else:
            table.update()

    def tourneyLogRemoveInactive(self, tournament, serials):
        with closing(self.db.cursor()) as c:
            c.execute("UPDATE tourneys SET removed_inactive_count = removed_inactive_count + %(num_serials)s WHERE serial = %(tourney_serial)s",
                { "tourney_serial": tournament.serial, "num_serials": len(serials)})
    
    def tourneyIndicateUserAction(self, tournament, serial):
        if not self.isTemporaryUser(serial):
            tournament._kickme_after = seconds() + CANCEL_INACTIVE_TOURNEY_TIMEOUT
            self.log.debug("tourneyIndicateUserAction: %s, new kickmeafter %s", serial, tournament._kickme_after)

    def cancelInactiveTourneys(self):
        now = seconds()
        for tourney in self.tourneys.values():
            if tourney.state == TOURNAMENT_STATE_RUNNING and now > tourney._kickme_after:
                self.log.inform("cancelInactiveTourneys: force cancel tourney %s", tourney.serial)
                tourney.changeState(TOURNAMENT_STATE_CANCELED, force=True)
                with closing(self.db.cursor()) as c:
                    c.execute("UPDATE tourneys SET state = 'canceled' WHERE serial = %s", (tourney.serial,))
                # destroy tourney tables
                for table in self.tables.values():
                    if table.tourney is tourney:
                        table.destroy()

        self.timer['cancel_inactive_tourneys'] = reactor.callLater(INACTIVE_TOURNEY_CANCEL_POLL_DEALAY, self.cancelInactiveTourneys)

    def createHand(self, game_id, tourney_serial=None):
        with closing(self.db.cursor()) as c:
            c.execute("INSERT INTO hands (description, game_id, tourney_serial) VALUES ('[]', %s, %s)",
                (game_id, tourney_serial))
            serial = c.lastrowid
        return int(serial)

    def getHandHistory(self, hand_serial, serial):
        history = self.loadHand(hand_serial)

        if not history:
            return PacketPokerError(
                game_id = hand_serial,
                serial = serial,
                other_type = PACKET_POKER_HAND_HISTORY,
                code = PacketPokerHandHistory.NOT_FOUND,
                message = "Hand %d was not found in history of player %d" % ( hand_serial, serial ) 
            )

        (type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips) = history[0]

        if serial not in player_list:
            return PacketPokerError(
                game_id = hand_serial,
                serial = serial,
                other_type = PACKET_POKER_HAND_HISTORY,
                code = PacketPokerHandHistory.FORBIDDEN,
                message = "Player %d did not participate in hand %d" % ( serial, hand_serial ) 
            )

        serial2name = dict(self.getNames(player_list))
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

        return PacketPokerHandHistory(
            game_id = hand_serial,
            serial = serial,
            history = str(history),
            serial2name = str(serial2name)
        )

    def loadHand(self, hand_serial, load_from_cache=True):
        #
        # load from hand_cache if needed and available
        if load_from_cache and hand_serial in self.hand_cache:
            return self.hand_cache[hand_serial]
        #
        # else fetch the hand from the database
        with closing(self.db.cursor()) as c:
            c.execute("SELECT description FROM hands WHERE serial = %s", (hand_serial,))
            if c.rowcount != 1:
                self.log.error("loadHand(%d) expected one row got %d", hand_serial, c.rowcount)
                return None
            (description,) = c.fetchone()
        history = None
        try:
            history = eval(description.replace("\r",""), {'PokerCards':PokerCards})
        except Exception:
            self.log.error("loadHand(%d) eval failed for %s", hand_serial, description, exc_info=1)
        return history

    def saveHand(self, description, hand_serial, save_to_cache=True):
        hand_type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips = description[0] #@UnusedVariable
        #
        # save the value to the hand_cache if needed
        if save_to_cache:
            for obsolete_hand_serial in self.hand_cache.keys()[:-3]:
                del self.hand_cache[obsolete_hand_serial]
            self.hand_cache[hand_serial] = description
        
        with closing(self.db.cursor()) as c:
            c.execute("UPDATE hands SET description = %s WHERE serial = %s", (str(description), hand_serial))
            self.log.debug("saveHand: %s" , c._executed)
            if c.rowcount not in (1, 0):
                self.log.error("modified %d rows (expected 1 or 0): %s", c.rowcount, c._executed)
                
            c.execute("INSERT INTO user2hand (user_serial, hand_serial) VALUES " + ", ".join(["(%d, %d)" % (user_serial, hand_serial) for user_serial in player_list]))
            self.log.debug("saveHand: %s", c._executed)
            if c.rowcount != len(player_list):
                self.log.error("inserted %d rows (expected exactly %d): %s", c.rowcount, len(player_list), c._executed)

    def listHands(self, sql_list, sql_total):
        with closing(self.db.cursor()) as c:
            self.log.debug("listHands: %s %s", sql_list, sql_total)
            c.execute(sql_list)
            hands = c.fetchall()
            c.execute(sql_total)
            total = c.fetchone()[0]
        return (total, [x[0] for x in hands])

    def eventTable(self, table):
        self.log.debug("eventTable: %s" % {
            'game_id': table.game.id ,
            'tourney_serial': table.tourney.serial if table.tourney else 0
        })

    def statsTables(self):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT COUNT(*) FROM tables")
            tables = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM user2table")
            players = c.fetchone()[0]
        return (players, tables)

    def listTables(self, query_string, serial):
        """listTables() takes two arguments:

                 query_string : which is the ad-hoc query string for the tables
                                sought (described in detail below), and
                 serial       : which is the user serial, used only when query_string == "my"

           The ad-hoc format of the query string deserves special
           documentation.  It works as follows:

               0. If query_string is the empty string, or exactly 'all', then
                  all tables in the system are returned. If the string is exactly 'all'
                  it will not be filtered by the current resthost.
                  
               1. If query_string is 'my', then all tables that player identified
                  by the argument, 'serial', has joined are returned.

               2. If query_string is 'mytourneys', then all tables that are spawned by tourneys
                  and the player identified by the 'serial' has joined are returned.

               3. If the query_string starts with "filter" there are a few possible parameters
                    "-f" show full tables (default, hide full tables)
                    "-m{min buy-in}" e.g. "-m100", it is important that no space is added between
                        the m and the value
                    "-M{max buy-in}" e.g. "-M1000", the capital M is used for the max buy-in

               4. Otherwise it is assumed to be a specific table name, and only table(s)
                  with the specific name exactly equal to the string are returned.
        """
        default_query =\
        """ SELECT
                t.serial, t.resthost_serial, c.seats, t.average_pot, t.hands_per_hour, t.percent_flop,
                t.players, t.observers, t.waiting, c.player_timeout, c.muck_timeout, c.currency_serial,
                c.name, c.variant, c.betting_structure, c.skin, t.tourney_serial
            FROM tables AS t
            INNER JOIN tableconfigs AS c
                ON c.serial = t.tableconfig_serial
        """
        query_suffix = " ORDER BY t.players desc, t.serial"
        if self.resthost_serial and query_string != 'all': 
            query_suffix = (" AND t.resthost_serial = %d" % self.resthost_serial) + query_suffix
        
        with closing(self.db.cursor(DictCursor)) as c:
            if query_string == '' or query_string == 'all':
                c.execute( default_query + "WHERE 1" + query_suffix )

            elif query_string == 'my':
                c.execute(
                    default_query + \
                    """ INNER JOIN user2table AS u2t
                            ON t.serial = u2t.table_serial
                        WHERE u2t.user_serial = %s
                    """ + query_suffix,
                    serial
                )
            elif query_string == 'mytourneys':
                c.execute(
                    """ SELECT
                            t.serial, t.resthost_serial, tourn.seats_per_game as seats, tourn.name as name, t.average_pot, t.hands_per_hour, t.percent_flop,
                            t.players, t.observers, t.waiting, tourn.player_timeout, 0 AS muck_timeout, tourn.currency_serial,
                            tourn.name, tourn.variant, tourn.betting_structure, tourn.skin, t.tourney_serial
                        FROM tables AS t
                        INNER JOIN user2table AS u2t
                            ON t.serial = u2t.table_serial
                        INNER JOIN tourneys AS tourn
                            ON tourn.serial = t.tourney_serial
                        WHERE u2t.user_serial = %s AND tourn.state in ('registering', 'running')
                    """ + query_suffix,
                    serial
                )
            elif query_string.startswith("filter"):
                params = query_string.split()
                min_buy_in = max_buy_in = None
                hide_full_tables = True
                skin = "pm"
                try:
                    for param in params[1:]:
                        if param.startswith("-m"):
                            min_buy_in = int(param[2:])
                        elif param.startswith("-M"):
                            max_buy_in = int(param[2:])
                        if param == "-f":
                            hide_full_tables = False
                        if param.startswith("-s"):
                            skin = param[2:]
                except ValueError:
                    self.log.inform("Following listTables() query_string is malformed %r", query_string)
                    return []

                sql_select = default_query

                where_clauses = [' c.skin in (%(skin)s,"intl") ']
                if hide_full_tables == True:
                    where_clauses.append(" t.players < c.seats")

                if min_buy_in:
                    where_clauses.append("SUBSTRING_INDEX(SUBSTRING_INDEX(c.betting_structure, '_', 2), '-', -1)+0 >= %d" % min_buy_in) # max
                if max_buy_in:
                    where_clauses.append("SUBSTRING_INDEX(SUBSTRING_INDEX(c.betting_structure, '-', 2), '_', -1)+0 <= %d" % max_buy_in)

                sql_select += " WHERE %s" % " AND ".join(where_clauses)
                sql_select += "\nGROUP BY c.name, t.players * RAND()"
                c.execute(sql_select + query_suffix, {"skin":skin})

            else:
                c.execute( default_query + "WHERE name =  %s " + query_suffix, query_string )

            result = c.fetchall()
        return result

    def searchTables(self, currency_serial = None, variant = None, betting_structure = None, min_players = 0):
        """searchTables() returns a list of tables that match the criteria
        specified in the parameters.  Parameter requirements are:
            currency_serial:    must be a positive integer or None
            variant:            must be a string or None
            betting_structure:  must be a string or None
            min_players:        must be a non-negative integer

        Note that the 'min_players' criterion is a >= setting.  The rest
        are exactly = to setting.

        Note further that min_players and currency_serial *must be*
        integer values in decimal greater than 0.  (Also, if sent in equal
        to 0, no error will be generated, but it will be as if you didn't
        send them at all).

        Finally, the query is sorted such that tables with the most
        players are at the top of the list.  Note that other methods rely
        on this, so don't change it.  The secondary sorting key is the
        ascending table serial.
        """
        
        query_suffix = " ORDER BY t.players desc, t.serial"
        if self.resthost_serial: query_suffix = (" AND t.resthost_serial = %d" % self.resthost_serial) + query_suffix
        
        whereValues = {
            'currency_serial': currency_serial, 
            'variant': variant,
            'betting_structure': betting_structure, 
            'min_players': min_players
        
        }
        with closing(self.db.cursor(DictCursor)) as c:
            # Now build the SQL statement we need.
            sql = \
            """ SELECT
                    t.serial,
                    t.resthost_serial,
                    c.seats,
                    t.average_pot,
                    t.hands_per_hour,
                    t.percent_flop,
                    t.players,
                    t.observers,
                    t.waiting,
                    c.player_timeout,
                    c.muck_timeout,
                    c.currency_serial,
                    c.name,
                    c.variant,
                    c.betting_structure,
                    c.skin,
                    t.tourney_serial
                FROM tables AS t
                INNER JOIN tableconfigs AS c
                    ON c.serial = t.tableconfig_serial
            """
            sqlQuestionMarkParameterList = []
            startLen = len(sql)
            for (kk, vv) in whereValues.iteritems():
                if vv == None or vv == '' or (kk == 'currency_serial' and int(vv) == 0):
                    # We skip any value that is was not given to us (is still
                    # None), was entirely empty when it came in, or, in the
                    # case of currency_serial, is 0, since a 0 currency_serial
                    # is not valid.
                    continue
                # Next, if we have an sql statement already from previous
                # iteration of this loop, add an "AND", otherwise, initialze
                # the sql string with the beginning of the SELECT statement.
                if len(sql) > startLen:
                    sql += " AND "
                else:
                    sql += " WHERE "
                # Next, we handle the fact that min_players is a >= parameter,
                # unlike the others which are = parameters.  Also, note here
                # that currency_serial and min_players are integer values.
                if kk == 'min_players':
                    sql += " players >= " + "%s"
                else:
                    sql += kk + " = " + "%s"
                sqlQuestionMarkParameterList.append(vv)

            sql += query_suffix
            c.execute(sql, sqlQuestionMarkParameterList)
            result = c.fetchall()
        return result

    def setupResthost(self):
        resthost = self.settings.headerGetProperties("/server/resthost")
        
        if resthost:
            self.log.inform('Resthost set: %s', resthost)
            resthost = resthost[0]
            missing = []
            for i in ('serial', 'name', 'host', 'port', 'path'):
                if i not in resthost: missing.append(i)
            if missing:
                self.log.crit('Resthost parameters missing: %s', ', '.join(missing))
                raise Exception('Resthost parameters missing: %s' % ', '.join(missing))
            with closing(self.db.cursor()) as c:
                params = tuple(resthost[i] for i in ('serial', 'name', 'host', 'port', 'path')) + (self.STATE_ONLINE,)
                c.execute(
                    "INSERT INTO resthost (serial, name, host, port, path, state) VALUES (%s, %s, %s, %s, %s, %s) " \
                    "ON DUPLICATE KEY UPDATE name=%s, host=%s, port=%s, path=%s, state=%s", 
                params + params[1:])
                self.resthost_serial = int(resthost['serial'])
                c.execute("DELETE FROM route WHERE resthost_serial = %s", self.resthost_serial)
        else:
            self.log.inform('Resthost not set')
        
    def setResthostOnShuttingDown(self):
        if self.resthost_serial:
            with closing(self.db.cursor()) as c:
                c.execute("UPDATE resthost SET state = %s WHERE serial = %s", (self.STATE_SHUTTING_DOWN,self.resthost_serial))
            
    def cleanupResthost(self):
        if self.resthost_serial:
            with closing(self.db.cursor()) as c:
                c.execute("DELETE FROM route WHERE resthost_serial = %s", (self.resthost_serial,))
                c.execute("UPDATE resthost SET state = %s WHERE serial = %s", (self.STATE_OFFLINE,self.resthost_serial))

    def packet2resthost(self, packet):
        #
        # game_id is only set for packets related to a table and not for
        # packets that are delegated but related to tournaments.
        #
        game_id = None
        result = None
        where = ""
        
        if packet.type in (PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST, PACKET_POKER_TOURNEY_REGISTER, PACKET_POKER_TOURNEY_UNREGISTER):
            where = "tourney_serial = %d" % packet.tourney_serial
        elif packet.type == PACKET_POKER_GET_TOURNEY_MANAGER:
            where = "tourney_serial = %d" % packet.tourney_serial
        elif getattr(packet, "game_id",0) > 0 and packet.game_id in self.tables.iterkeys():
            game_id = packet.game_id
        elif getattr(packet, "game_id",0) > 0:
            where = "table_serial = %d" % packet.game_id
            game_id = packet.game_id
            
        if where:
            with closing(self.db.cursor()) as c:
                c.execute(
                   "SELECT host, port, path FROM route,resthost WHERE route.resthost_serial = resthost.serial " \
                   "AND resthost.serial != %d AND %s" % (self.resthost_serial,where)
                )
                result = c.fetchone() if c.rowcount > 0 else None
            
        return (result, game_id)

    def cleanUpTemporaryUsers(self):
        with closing(self.db.cursor()) as c:
            c.execute(lex(
                """ DELETE user2tourney FROM user2tourney, users
                    WHERE (users.serial BETWEEN %s AND %s OR users.name RLIKE %s) AND users.serial = user2tourney.user_serial
                """),
                (
                    self.temporary_serial_min,
                    self.temporary_serial_max,
                    self.temporary_users_pattern
                )
            )
            c.execute(
                "DELETE FROM users WHERE serial BETWEEN %s AND %s OR name RLIKE %s",
                (
                    self.temporary_serial_min,
                    self.temporary_serial_max,
                    self.temporary_users_pattern
                )
            )

    def abortRunningTourneys(self):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT serial FROM tourneys WHERE state IN ('running', 'break', 'breakwait')")
            if c.rowcount:
                for (tourney_serial,) in c.fetchall():
                    self.databaseEvent(event = PacketPokerMonitorEvent.TOURNEY_CANCELED, param1 = tourney_serial)

                c.execute(
                    "UPDATE tourneys AS t " \
                        "LEFT JOIN user2tourney AS u2t ON u2t.tourney_serial = t.serial " \
                        "LEFT JOIN user2money AS u2m ON u2m.user_serial = u2t.user_serial " \
                    "SET u2m.amount = u2m.amount + (t.buy_in + t.rake)*(1+u2t.rebuy_count), t.state = 'aborted' " \
                    "WHERE " \
                        "t.resthost_serial = %s AND " \
                        "t.state IN ('running', 'break', 'breakwait')",
                    (self.resthost_serial,)
                )
                
                self.log.debug("cleanupTourneys: %s", c._executed)

    def restoreTourneys(self):
        now = seconds()
        restored_info = []
        with closing(self.db.cursor(DictCursor)) as c:
            tourney_serials_sql = "AND serial NOT IN (%s)" % \
                ",".join(self.db.literal(t) for t in self.tourneys.keys()) \
                if self.tourneys else ""
            sql = \
                "SELECT * FROM tourneys " \
                "WHERE resthost_serial = %s " \
                "AND state = 'registering' " \
                "AND (start_time >= %s OR sit_n_go = 'y') " \
                + tourney_serials_sql
            params = (self.resthost_serial, now-2*CHECK_TOURNEYS_SCHEDULE_DELAY)
            c.execute(sql, params)
            self.log.debug("restoreTourneys: %s", c._executed)
            for row in c.fetchall():
                restored_info.append((row['serial'], row['schedule_serial']))
                
                tourney = self.spawnTourneyInCore(row, row['serial'], row['schedule_serial'], row['currency_serial'], row['prize_currency'])
                # When the tourney should have already started:
                # tourney.register would call updateRunning and try to start the tourney because it is already in the 
                # state registering would cancel the tourney since there are not enough players.
                # We cannot set the tourney state (to registering) yet because the we need to register the player first

                old_state, tourney.state = tourney.state, TOURNAMENT_STATE_LOADING
                c.execute(
                    "SELECT u.serial, u.name FROM users AS u " \
                    "JOIN user2tourney AS u2t " \
                    "ON u.serial = u2t.user_serial AND u2t.tourney_serial = %s",
                    (row['serial'],)
                )
                self.log.debug("restoreTourneys: %s", c._executed)
                for user in c.fetchall():
                    tourney.register(user['serial'],user['name'])
                
                c.execute(
                    "REPLACE INTO route VALUES (0, %s, %s, %s)",
                    (row['serial'], now, self.resthost_serial)
                )

                tourney.state = old_state
                if tourney.state == TOURNAMENT_STATE_ANNOUNCED:
                    tourney.updateRegistering()
                if tourney.state == TOURNAMENT_STATE_REGISTERING:
                    tourney.updateRunning()
            
        return restored_info
        
    def cleanupTourneys(self):
        self.tourneys = {}
        self.schedule2tourneys = {}
        self.tourneys_schedule = {}
        now = seconds()
        with closing(self.db.cursor()) as c:
            # abort still running tourneys and refund buyin
            self.abortRunningTourneys()
            
            # trash tourneys and their user2tourney data which
            # are in registering state with a starttime in the past
            c.execute(
                "UPDATE tourneys AS t " \
                "LEFT JOIN user2tourney AS u2t ON u2t.tourney_serial = t.serial " \
                "LEFT JOIN user2money AS u2m ON u2m.user_serial = u2t.user_serial " \
                "SET u2m.amount = u2m.amount + t.buy_in + t.rake, t.state = 'aborted' " \
                "WHERE t.resthost_serial = %s " \
                "AND t.sit_n_go = 'n' AND t.state = 'registering' AND t.start_time < %s",
                (self.resthost_serial, now)
            )
            if c.rowcount:
                self.log.debug("cleanupTourneys: rows: %d, sql: %s", c.rowcount, c._executed)
            
            # get refunds for all players registered in aborted tourneys
            # and delete all associated user2tourney entries
            c.execute(
                "SELECT u2t.user_serial, u2t.tourney_serial, (t.buy_in+t.rake)*(1+u2t.rebuy_count) AS refund " \
                "FROM user2tourney AS u2t " \
                "LEFT JOIN tourneys as t ON t.serial = u2t.tourney_serial "
                "WHERE t.resthost_serial = %s AND t.state = 'aborted'",
                (self.resthost_serial,)
            )
            refunds = c.fetchall()
            if c.rowcount:
                self.log.debug("cleanupTourneys: %s", c._executed)
            c.execute(
                "DELETE u2t FROM user2tourney AS u2t " \
                "LEFT JOIN tourneys AS t ON t.serial = u2t.tourney_serial " \
                "WHERE t.resthost_serial = %s AND t.state = 'aborted'",
                (self.resthost_serial,)
            )
            if c.rowcount:
                self.log.debug("cleanupTourneys: %s", c._executed)
            # communicate all refunds
            for user_serial, tourney_serial, refund in refunds:
                self.databaseEvent(event = PacketPokerMonitorEvent.UNREGISTER, param1 = user_serial, param2 = tourney_serial, param3 = refund)
            
            c.execute(
                "DELETE t FROM tourneys AS t " \
                "WHERE t.resthost_serial = %s AND t.state = 'aborted'",
                (self.resthost_serial,)
            )
            if c.rowcount:
                self.log.debug("cleanupTourneys: %s", c._executed)
            
            # restore registering tourneys
            self.restoreTourneys()

    def getMoney(self, serial, currency_serial):
        with closing(self.db.cursor()) as c:
            c.execute(
                "SELECT amount FROM user2money " \
                "WHERE user_serial = %s " \
                "AND currency_serial = %s",
                (serial,currency_serial)
            )
            self.log.debug("%s", c._executed)

            if c.rowcount > 1:
                self.log.error("getMoney(%d) expected one row got %d", serial, c.rowcount)
                return 0
            elif c.rowcount == 1:
                (money,) = c.fetchone()
            else:
                money = 0
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
            return PacketError(
                code = PacketPokerCashOutCommit.INVALID_TRANSACTION,
                message = "transaction " + packet.transaction_id + " affected " + str(count) + " rows instead of zero or one",
                other_type = PACKET_POKER_CASH_OUT_COMMIT
            )

    def getPlayerInfo(self, serial):
        placeholder = PacketPokerPlayerInfo(
            serial = serial,
            name = "anonymous",
            url= "",
            outfit = "",
            locale = "en_US"
        )
        if serial == 0:
            return placeholder

        with closing(self.db.cursor()) as c:
            c.execute(
                "SELECT locale,name,skin_url,skin_outfit FROM users WHERE serial = %s",
                (serial,)
            )
            if c.rowcount != 1:
                self.log.error("getPlayerInfo(%d) expected one row got %d", serial, c.rowcount)
                return placeholder
            (locale,name,skin_url,skin_outfit) = c.fetchone()
            if skin_outfit == None: skin_outfit = ""
        packet = PacketPokerPlayerInfo(
            serial = serial,
            name = name,
            url = skin_url,
            outfit = skin_outfit
        )
        # pokerservice generally provides playerInfo() internally to
        # methods like pokeravatar.(re)?login.  Since this is the central
        # internal location where the query occurs, we hack in the locale
        # returned from the DB.
        packet.locale = locale
        return packet

    def getPlayerPlaces(self, serial):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT table_serial FROM user2table WHERE user_serial = %s", serial)
            tables = [x[0] for x in c.fetchall()]
            c.execute("SELECT user2tourney.tourney_serial FROM user2tourney,tourneys WHERE user2tourney.user_serial = %s AND user2tourney.tourney_serial = tourneys.serial AND tourneys.state in ('registering', 'running', 'break', 'breakwait')", serial)
            tourneys = [x[0] for x in c.fetchall()]
            return PacketPokerPlayerPlaces(
                serial = serial,
                tables = tables,
                tourneys = tourneys
            )

    def getPlayerPlacesByName(self, name):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT serial FROM users WHERE name = %s", name)
            serial = c.fetchone()
            if serial == None:
                return PacketError(other_type = PACKET_POKER_PLAYER_PLACES)
            else:
                serial = serial[0]
            return self.getPlayerPlaces(serial)

    def isTemporaryUser(self,serial):
        return bool(
            self.temporary_serial_min <= serial <= self.temporary_serial_max or 
            re.match(self.temporary_users_pattern, self.getName(serial))
        )
        
    def getUserInfo(self, serial):
        with closing(self.db.cursor()) as c:
            c.execute("SELECT rating, affiliate, email, name FROM users WHERE serial = %s", (serial,))
            if c.rowcount != 1:
                self.log.error("getUserInfo(%d) expected one row got %d", serial, c.rowcount)
                return PacketPokerUserInfo(serial = serial)
            kw = {'serial': serial}
            kw['rating'], kw['affiliate'], kw['email'], kw['name'] = c.fetchone()
            if not kw['email']: kw['email'] = ''
            packet = PacketPokerUserInfo(**kw)
            c.execute(lex(
                """ SELECT
                        u2m.currency_serial,
                        u2m.amount,
                        COALESCE(u2t.money, 0) AS in_game,
                        u2m.points
                    FROM user2money AS u2m
                    LEFT JOIN (user2table u2t, tables t, tableconfigs c)
                        ON
                            u2t.user_serial = u2m.user_serial AND
                            u2t.table_serial = t.serial AND
                            t.tableconfig_serial = c.serial AND
                            c.currency_serial = u2m.currency_serial
                    WHERE
                        u2m.user_serial = %s
                """),
                (serial,)
            )
            packet.money = dict((row[0], row[1:]) for row in c)
            self.log.debug("getUserInfo %s", packet)
            return packet

    def getPersonalInfo(self, serial):
        user_info = self.getUserInfo(serial)
        self.log.debug("getPersonalInfo %s", user_info)
        packet = PacketPokerPersonalInfo(
            serial = user_info.serial,
            name = user_info.name,
            email = user_info.email,
            rating = user_info.rating,
            affiliate = user_info.affiliate,
            money = user_info.money
        )
        with closing(self.db.cursor()) as c:
            c.execute(lex(
                """ SELECT
                        firstname,
                        lastname,
                        addr_street,
                        addr_street2,
                        addr_zip,
                        addr_town,
                        addr_state,
                        addr_country,
                        phone,
                        gender,
                        birthdate
                    FROM users_private
                    WHERE serial = %s
                """), (serial,)
            )
            if c.rowcount != 1:
                self.log.error("getPersonalInfo(%d) expected one row got %d", serial, c.rowcount)
                return PacketPokerPersonalInfo(serial = serial)
            (packet.firstname, packet.lastname, packet.addr_street, packet.addr_street2, packet.addr_zip, packet.addr_town, packet.addr_state, packet.addr_country, packet.phone, packet.gender, packet.birthdate) = c.fetchone()
        if not packet.gender: packet.gender = ''
        if not packet.birthdate: packet.birthdate = ''
        packet.birthdate = str(packet.birthdate)
        return packet

    def setPersonalInfo(self, info):
        with closing(self.db.cursor()) as c:
            c.execute(lex(
                """ UPDATE users_private
                    SET
                        firstname = %s,
                        lastname = %s,
                        addr_street = %s,
                        addr_street2 = %s,
                        addr_zip = %s,
                        addr_town = %s,
                        addr_state = %s,
                        addr_country = %s,
                        phone = %s,
                        gender = %s,
                        birthdate = %s
                    WHERE
                        serial = %s
                """),
                (
                    info.firstname,
                    info.lastname,
                    info.addr_street,
                    info.addr_street2,
                    info.addr_zip,
                    info.addr_town,
                    info.addr_state,
                    info.addr_country,
                    info.phone,
                    info.gender,
                    info.birthdate or None,
                    info.serial
                )
            )
            self.log.debug("setPersonalInfo: %s", c._executed)
            if c.rowcount != 1 and c.rowcount != 0:
                self.log.error("setPersonalInfo: modified %d rows (expected 1 or 0): %s", c.rowcount, c._executed)
                return False
            return True

    def setAccount(self, packet):
        #
        # name constraints check
        status = checkName(packet.name)
        if not status[0]:
            return PacketError(
                code = status[1],
                message = status[2],
                other_type = packet.type
            )
        #
        # look for user
        with closing(self.db.cursor()) as c:
            c.execute("SELECT serial FROM users WHERE name = %s", (packet.name,))
            numrows = int(c.rowcount)
            #
            # password constraints check
            if ( numrows == 0 or ( numrows > 0 and packet.password != "" )):
                status = checkPassword(packet.password)
                if not status[0]:
                    return PacketError(
                        code = status[1],
                        message = status[2],
                        other_type = packet.type
                    )
            #
            # email constraints check
            email_regexp = ".*.@.*\..*$"
            if not re.match(email_regexp, packet.email):
                return PacketError(
                    code = PacketPokerSetAccount.INVALID_EMAIL,
                    message = "email %s does not match %s " % ( packet.email, email_regexp ),
                    other_type = packet.type
                )
            if numrows == 0:
                c.execute("SELECT serial FROM users WHERE email = %s", (packet.email,))
                numrows = int(c.rowcount)
                if numrows > 0:
                    return PacketError(
                        code = PacketPokerSetAccount.EMAIL_ALREADY_EXISTS,
                        message = "there already is another account with the email %s" % packet.email,
                        other_type = packet.type
                    )
                #
                # user does not exists, create it
                c.execute(lex(
                    """ INSERT INTO users (created, name, password, email, affiliate)
                        VALUES (%s, %s, %s, %s, %s)
                    """),
                    (seconds(), packet.name, packet.password, packet.email, str(packet.affiliate))
                )
                if c.rowcount != 1:
                    #
                    # impossible except for a sudden database corruption, because of the
                    # above SQL statements
                    self.log.error("setAccount: insert %d rows (expected 1): %s", c.rowcount, c._executed)
                    return PacketError(
                        code = PacketPokerSetAccount.SERVER_ERROR,
                        message = "inserted %d rows (expected 1)" % c.rowcount,
                        other_type = packet.type
                    )
                packet.serial = c.lastrowid
                c.execute("INSERT INTO users_private (serial) VALUES (%s)", (packet.serial,))
            else:
                #
                # user exists, update name, password and email
                (serial,) = c.fetchone()
                if serial != packet.serial:
                    return PacketError(
                        code = PacketPokerSetAccount.NAME_ALREADY_EXISTS,
                        message = "user name %s already exists" % packet.name,
                        other_type = packet.type
                    )
                c.execute("SELECT serial FROM users WHERE email = %s and serial != %s", ( packet.email, serial ))
                numrows = int(c.rowcount)
                if numrows > 0:
                    return PacketError(
                        code = PacketPokerSetAccount.EMAIL_ALREADY_EXISTS,
                        message = "there already is another account with the email %s" % packet.email,
                        other_type = packet.type
                    )
                set_password = ", password = %s " % self.db.literal(packet.password) if packet.password else ""
                sql = "UPDATE users SET name = %s, email = %s " + set_password + "WHERE serial = %s"
                params = (packet.name,packet.email,packet.serial)
                c.execute(sql, params)
                self.log.debug("setAccount: %s", sql)
                if c.rowcount != 1 and c.rowcount != 0:
                    self.log.error("setAccount: modified %d rows (expected 1 or 0): %s", c.rowcount, c._executed)
                    return PacketError(
                        code = PacketPokerSetAccount.SERVER_ERROR,
                        message = "modified %d rows (expected 1 or 0)" % c.rowcount,
                        other_type = packet.type
                    )
            #
            # set personal information
            if not self.setPersonalInfo(packet):
                    return PacketError(
                        code = PacketPokerSetAccount.SERVER_ERROR,
                        message = "unable to set personal information",
                        other_type = packet.type
                    )
            return self.getPersonalInfo(packet.serial)

    def setPlayerInfo(self, player_info):
        with closing(self.db.cursor()) as c:
            c.execute(
                "UPDATE users SET name = %s, skin_url = %s, skin_outfit = %s WHERE serial = %s",
                (player_info.name, player_info.url, player_info.outfit, player_info.serial)
            )
            self.log.debug("setPlayerInfo: %s", c._executed)
            if c.rowcount != 1 and c.rowcount != 0:
                self.log.error("setPlayerInfo: modified %d rows (expected 1 or 0): %s", c.rowcount, c._executed)
                return False
            return True

    def getName(self, serial):
        """Returns the name to the given serial"""
        avatars = self.avatar_collection.get(serial)
        return avatars[0].getName() if avatars else self.getNameFromDatabase(serial)
    
    def getNameFromDatabase(self, serial):
        if serial == 0:
            return "anonymous"

        with closing(self.db.cursor()) as c:
            c.execute("SELECT name FROM users WHERE serial = %s", (serial,))
            if c.rowcount != 1:
                self.log.error("getName(%d) expected one row got %d", serial, c.rowcount)
                return "UNKNOWN"
            (name,) = c.fetchone()
        return name
        
    def getNames(self, serials):
        with closing(self.db.cursor()) as c:
            sql = "SELECT serial,name FROM users WHERE serial IN (%s)"
            params = ", ".join("%d" % serial for serial in set(serials) if serial > 0)
            c.execute(sql % params)
            return c.fetchall()

    def getTableAutoDeal(self):
        return self.settings.headerGet("/server/@autodeal") == "yes"
    
    def buyInPlayer(self, serial, table_id, currency_serial, amount):
        if amount == None:
            self.log.error("called buyInPlayer with None amount (expected > 0); denying buyin")
            return 0
        # unaccounted money is delivered regardless
        if not currency_serial: return amount

        withdraw = min(self.getMoney(serial, currency_serial), amount)
        with closing(self.db.cursor()) as c:
            c.execute(lex(
                """ UPDATE user2money,user2table
                    SET
                        user2table.money = user2table.money + %s,
                        user2money.amount = user2money.amount - %s
                    WHERE
                        user2money.user_serial = %s AND
                        user2money.currency_serial = %s AND
                        user2table.user_serial = %s AND
                        user2table.table_serial = %s
               """),
                (withdraw, withdraw, serial, currency_serial, serial, table_id)
            )
            self.log.debug("buyInPlayer: %s", c._executed)
            if c.rowcount != 0 and c.rowcount != 2:
                self.log.error("modified %d rows (expected 0 or 2): %s", c.rowcount, c._executed)
            self.databaseEvent(event = PacketPokerMonitorEvent.BUY_IN, param1 = serial, param2 = table_id, param3 = withdraw)
            return withdraw

    def seatPlayer(self, serial, table_id, amount, minimum_amount = None):
        with closing(self.db.cursor()) as c:
            status = True
            if minimum_amount:
                c.execute(lex(
                    """ SELECT COUNT(*) FROM user2money
                        WHERE
                            user_serial = %s AND
                            currency_serial = %s AND
                            amount >= %s
                    """),
                    (serial,) + minimum_amount
                )
                status = (c.fetchone()[0] >= 1)
            if status:
                c.execute(
                    "INSERT INTO user2table (user_serial, table_serial, money) VALUES (%s, %s, %s)",
                    (serial, table_id, amount)
                )
                self.log.debug("seatPlayer: %s", c._executed)
                if c.rowcount != 1:
                    self.log.error("inserted %d rows (expected 1): %s", c.rowcount, c._executed)
                    status = False
                self.databaseEvent(event = PacketPokerMonitorEvent.SEAT, param1 = serial, param2 = table_id)
            return status

    def movePlayer(self, serial, from_table_id, to_table_id):
        with closing(self.db.cursor()) as c:
            c.execute(
                "SELECT money FROM user2table " \
                "WHERE user_serial = %s " \
                "AND table_serial = %s",
                (serial,from_table_id)
            )
            if c.rowcount != 1:
                self.log.error("movePlayer(%d) expected one row got %d", serial, c.rowcount)
                return
            
            (money,) = c.fetchone()
            
            sql = \
                "UPDATE user2table " \
                "SET table_serial = %s " \
                "WHERE user_serial = %s " \
                "AND table_serial = %s"
            params = (to_table_id,serial,from_table_id)
            
            for error_cnt in xrange(3):
                try:
                    c.execute(sql, params)
                    break
                except:
                    self.log.warn("ERROR: couldn't execute %r with params %r for %s times" % (sql, params,error_cnt))
                    if error_cnt >= 2: raise

            self.log.debug("movePlayer: %s", c._executed)
            if c.rowcount != 1:
                self.log.error("modified %d rows (expected 1): %s", c.rowcount, c._executed)
                money = -1

        return money

    def buyOutPlayer(self, serial, table_id, currency_serial):
        with closing(self.db.cursor()) as c:
            if currency_serial:
                c.execute(lex(
                    """ UPDATE user2money AS u2m
                        LEFT JOIN user2table AS u2t
                            ON u2t.user_serial = u2m.user_serial
                        LEFT JOIN tables AS t
                            ON t.serial = u2t.table_serial
                        LEFT JOIN tableconfigs AS c
                            ON c.serial = t.tableconfig_serial
                        SET
                            u2m.amount = u2m.amount + COALESCE(u2t.money, 0),
                            u2t.money = 0
                        WHERE u2m.user_serial = %s AND t.serial = %s AND u2m.currency_serial = %s AND c.currency_serial = %s
                    """),
                    (serial, table_id, currency_serial, currency_serial)
                )
                if c.rowcount not in (0, 2):
                    self.log.error("leavePlayer: modified %d rows (expected 0 or 2)\n%s", c.rowcount, c._executed, refs=[('User', serial, int)])

    def leavePlayer(self, serial, table_id, currency_serial):
        self.buyOutPlayer(serial, table_id, currency_serial)
        with closing(self.db.cursor()) as c:
            c.execute("DELETE FROM user2table WHERE user_serial = %s AND table_serial = %s", (serial , table_id))
            if c.rowcount != 1:
                self.log.error("leavePlayer: modified %d rows (expected 1)\n%s", c.rowcount, c._executed, refs=[('User', serial, int)])
            self.databaseEvent(event = PacketPokerMonitorEvent.LEAVE, param1 = serial, param2 = table_id, param3 = currency_serial)

    def updatePlayerRake(self, currency_serial, serial, amount):
        if amount == 0 or currency_serial == 0:
            return True
        status = True
        with closing(self.db.cursor()) as c:
            c.execute(
                "UPDATE user2money SET rake = rake + %s, points = points + %s WHERE user_serial = %s AND currency_serial = %s",
                (amount, amount, serial, currency_serial)
            )
            self.log.debug("updatePlayerRake: %s", c._executed)
            if c.rowcount != 1:
                self.log.error("modified %d rows (expected 1): %s", c.rowcount, c._executed)
                status = False
        return status

    def updatePlayerMoney(self, serial, table_id, amount):
        if amount == 0:
            return True
        status = True
        with closing(self.db.cursor()) as c:
            c.execute(
                "UPDATE user2table SET money = money + %s WHERE user_serial = %s AND table_serial = %s",
                (amount, serial, table_id)
            )
            self.log.debug("updatePlayerMoney: %s", c._executed)
            if c.rowcount != 1:
                self.log.error("modified %d rows (expected 1): %s", c.rowcount, c._executed)
                status = False
        return status

    def updateTableStats(self, game, observers, waiting):
        with closing(self.db.cursor()) as c:
            c.execute(lex(
                """ UPDATE tables
                    SET
                        average_pot = %s,
                        hands_per_hour = %s,
                        percent_flop = %s,
                        players = %s,
                        observers = %s,
                        waiting = %s
                    WHERE serial = %s
                """),
                (
                    game.stats['average_pot'],
                    game.stats['hands_per_hour'],
                    game.stats['percent_flop'],
                    game.allCount(),
                    observers,
                    waiting,
                    game.id
                )
            )

    def destroyTable(self, table_id):
        with closing(self.db.cursor()) as c:
            c.execute("DELETE FROM user2table WHERE table_serial = %s", (table_id,))
            self.log.debug("destroy: %s", c._executed)
            c.execute("DELETE FROM route WHERE table_serial = %s", table_id)

    def getTable(self, game_id):
        return self.tables.get(game_id, False)

    def getTourneyTable(self, tourney, serial):
        return next(t for t in self.tables.itervalues() if t.tourney is tourney and serial in t.game.serial2player)

    def cleanupCrashedTables(self):
        with closing(self.db.cursor()) as c:
            c.execute(lex(
                """ SELECT t.serial, c.currency_serial, u2t.user_serial, u2t.money
                    FROM user2table AS u2t
                    LEFT JOIN tables AS t
                        ON t.serial = u2t.table_serial
                    LEFT JOIN tableconfigs AS c
                        ON c.serial = t.tableconfig_serial
                    WHERE t.resthost_serial = %s AND c.currency_serial != 0
                """),
                (self.resthost_serial,)
            )
            for table_serial, currency_serial, user_serial, money in c:
                self.log.inform(
                    "cleanupCrashedTables: found zombie in user2table, table: %d, user: %d, currency: %d, money: %d",
                    table_serial, user_serial, currency_serial, money, refs=[
                        ('Game', self, lambda x: table_serial),
                        ('User', self, lambda x: user_serial)
                    ]
                )
                self.leavePlayer(user_serial, table_serial, currency_serial)
            c.execute(lex(
                """ UPDATE tables
                    SET players = 0, observers = 0
                    WHERE resthost_serial = %s
                """),
                (self.resthost_serial,)
            )

    def deleteTable(self, table):
        self.log.debug("table %s/%d removed from server", table.game.name, table.game.id)
        del self.tables[table.game.id]
        if table.transient: self.deleteTableEntry(table)
        
    def deleteTableEntry(self, table):
        self.log.debug("table %s/%d deleting db entry", table.game.name, table.game.id)
        with closing(self.db.cursor()) as c:
            c.execute("DELETE FROM tables WHERE serial = %s", (table.game.id,))
            if c.rowcount != 1:
                self.log.warn("deleteTableEntry: deleted %d rows expected 1: %s", c.rowcount, c._executed)

    def broadcast(self, packet):
        for avatar in self.avatars:
            if hasattr(avatar, "protocol") and avatar.protocol:
                avatar.sendPacketVerbose(packet)
            else:
                self.log.debug("broadcast: avatar %s excluded" % str(avatar))

    def chatMessageArchive(self, player_serial, game_id, message):
        with closing(self.db.cursor()) as c:
            c.execute(
                "INSERT INTO chat_messages (player_serial, game_id, message) VALUES (%s, %s, %s)",
                (player_serial, game_id, message)
            )

if HAS_OPENSSL:
    from twisted.internet.ssl import DefaultOpenSSLContextFactory
    
    class SSLContextFactory(DefaultOpenSSLContextFactory):
        def __init__(self, settings):
            self.pem_file = None
            for path in settings.headerGet("/server/path").split():
                if exists(path + "/poker.pem"):
                    self.pem_file = path + "/poker.pem"
            if self.pem_file is None:
                raise Exception("no poker.pem found in the setting's server path")
            DefaultOpenSSLContextFactory.__init__(self, self.pem_file, self.pem_file)
            

from twisted.web import resource

class PokerRestTree(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.putChild("POKER_REST", PokerResource(self.service))
        self.putChild("TOURNEY_START", PokerTourneyStartResource(self.service))
        self.putChild("", self)

    def render_GET(self, request):
        return "Use /POKER_REST or /TOURNEY_START"

def _getRequestCookie(request):
    if request.cookies:
        return request.cookies[0]
    else:
        return request.getCookie('_'.join(['TWISTED_SESSION'] + request.sitepath))
