#
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2006 - 2010 Loic Dachary <loic@dachary.org>
# Copyright (C)       2008, 2009 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C)             2008 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2004, 2005, 2006 Mekensleep
#                                24 rue vieille du temple 75004 Paris
#                                <licensing@mekensleep.com>
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
#  Loic Dachary <loic@gnu.org>
#  Bradley M. Kuhn <bkuhn@ebb.org> (2008)
#  Johan Euphrosine <proppy@aminche.com> (2008)
#  Henry Precheur <henry@precheur.org> (2004)

from string import join
import sets

from twisted.internet import reactor, defer
from traceback import format_exc

from pokernetwork.user import User, checkNameAndPassword, checkAuth
from pokerpackets.networkpackets import *
from pokernetwork.pokerexplain import PokerExplain
from pokernetwork.pokerrestclient import PokerRestClient
from pokernetwork.pokerpacketizer import createCache, history2packets

from pokerengine.pokertournament import TOURNAMENT_STATE_REGISTERING, TOURNAMENT_STATE_CANCELED, TOURNAMENT_STATE_RUNNING

from pokernetwork import log as network_log
log = network_log.get_child('pokeravatar')

DEFAULT_PLAYER_USER_DATA = { 'ready': True }

class PokerAvatar:

    log = log.get_child('PokerAvatar')

    def __init__(self, service):
        self.log = PokerAvatar.log.get_instance(self, refs=[
            ('User', self, lambda avatar: avatar.user.serial if avatar.user else None)
        ])
        self.protocol = None
        self.localeFunc = None
        self.roles = sets.Set()
        self.service = service
        self.tables = {}
        self.user = User()
        self._packets_queue = []
        self.warnedPacketExcess = False
        self.tourneys = []
        self.setExplain(0)
        self.bugous_processing_hand = False
        self.noqueuePackets()
        self._block_longpoll_deferred = False
        self._longpoll_deferred = None
        self.game_id2rest_client = {}
        self.distributed_uid = None
        self.distributed_auth = None
        self.distributed_args = '?explain=no'
        self.longPollTimer = None
        self._flush_next_longpoll = False

    def setDistributedArgs(self, uid, auth):
        self.distributed_uid = uid
        self.distributed_auth = auth
        self.distributed_args = '?explain=no&uid=%s&auth=%s' % ( uid, auth )
        
    def __str__(self):
        return "PokerAvatar serial = %s, name = %s" % ( self.getSerial(), self.getName() )

    def setExplain(self, what):
        if what:
            if self.explain == None:
                if self.tables:
                    self.log.warn("setExplain must be called when not connected to any table")
                    return False

                self.explain = PokerExplain(dirs = self.service.dirs, explain = what)
                self.explain.serial = self.getSerial()
        else:
            self.explain = None
        return True

    def _setDefaultLocale(self, locale):
        """Set self.localFunc using locale iff. it is not already set.
        Typically, this method is only used for a locale found for the
        user in the database.  If the client sends a
        PacketPokerSetLocale(), that will always take precedent and should
        not use this method, but self.setLocale() instead."""
        if not self.localeFunc:
            return self.setLocale(locale)
        else:
            return None
            
    def setLocale(self, locale):
        if locale:
            self.localeFunc = self.service.locale2translationFunc(locale, 'UTF-8')
        return self.localeFunc

    def setProtocol(self, protocol):
        self.protocol = protocol

    def isAuthorized(self, type):
        return self.user.hasPrivilege(self.service.poker_auth.GetLevel(type))

    def relogin(self, serial):
        player_info = self.service.getPlayerInfo(serial)
        self.user.serial = serial
        self.user.name = player_info.name
        self.user.privilege = User.REGULAR if serial != 2 else User.ADMIN
        self.user.url = player_info.url
        self.user.outfit = player_info.outfit
        if hasattr(player_info, 'locale'):
            self._setDefaultLocale(player_info.locale)

        if self.explain:
            self.explain.handleSerial(PacketSerial(serial = serial))
        self.service.avatar_collection.add(serial, self)
        self.tourneyUpdates(serial)
        self.loginTableUpdates(serial)
    
    def login(self, info):
        (serial, name, privilege) = info
        self.user.serial = serial
        self.user.name = name
        self.user.privilege = privilege

        player_info = self.service.getPlayerInfo(serial)
        self.user.url = player_info.url
        self.user.outfit = player_info.outfit
        if hasattr(player_info, 'locale'):
            self._setDefaultLocale(player_info.locale)

        self.sendPacketVerbose(PacketSerial(serial = self.user.serial))
        if PacketPokerRoles.PLAY in self.roles:
            self.service.avatar_collection.add(serial, self)
        self.log.debug("user %s/%d logged in", self.user.name, self.user.serial)
            
        if self.explain:
            self.explain.handleSerial(PacketSerial(serial = serial))
        self.service.avatar_collection.add(serial, self)
            
        self.tourneyUpdates(serial)
        self.loginTableUpdates(serial)

    def tourneyUpdates(self, serial):
        places = self.service.getPlayerPlaces(serial)
        self.tourneys = places.tourneys

    def loginTableUpdates(self, serial):
        #
        # Send player updates if it turns out that the player was already
        # seated at a known table.
        #
        for table in self.tables.values():
            if table.possibleObserverLoggedIn(self, serial):
                game = table.game
                self.sendPacketVerbose(PacketPokerPlayerCards(
                    game_id = game.id,
                    serial = serial,
                    cards = game.getPlayer(serial).hand.toRawList()
                ))
                self.sendPacketVerbose(PacketPokerPlayerSelf(game_id = game.id, serial = serial))
                pending_blind_request = game.isBlindRequested(serial)
                pending_ante_request = game.isAnteRequested(serial)
                if pending_blind_request or pending_ante_request:
                    if pending_blind_request:
                        (amount, dead, state) = game.blindAmount(serial)
                        self.sendPacketVerbose(PacketPokerBlindRequest(
                            game_id = game.id,
                            serial = serial,
                            amount = amount,
                            dead = dead,
                            state = state
                        ))
                    if pending_ante_request:
                        self.sendPacketVerbose(PacketPokerAnteRequest(
                            game_id = game.id,
                            serial = serial,
                            amount = game.ante_info["value"]
                        ))

    def logout(self):
        if self.user.serial:
            if PacketPokerRoles.PLAY in self.roles:
                self.service.avatar_collection.remove(self.user.serial, self)
            self.user.logout()
        
    def auth(self, packet):
        if packet.type == PACKET_LOGIN:
            status = checkNameAndPassword(packet.name, packet.password)
        elif packet.type == PACKET_AUTH:
            status = checkAuth(packet.auth)
        if status[0]:
            auth_args = None
            if packet.type == PACKET_LOGIN:
                auth_args = (packet.name,packet.password)
            elif packet.type == PACKET_AUTH:
                auth_args = (packet.auth,)
            ( info, reason ) = self.service.auth(packet.type,auth_args,self.roles)
            code = 0
        else:
            self.log.debug("auth: failure %s", status)
            reason = status[2]
            code = status[1]
            info = False
        if info:
            self.sendPacketVerbose(PacketAuthOk())
            self.login(info)
        else:
            self.sendPacketVerbose(PacketAuthRefused(
                message = reason,
                code = code,
                other_type = PACKET_LOGIN
            ))
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

    def extendPacketsQueue(self, newPackets):
        """takes PokerAvatar object and a newPackets as arguments, and
        extends the self._queue_packets variable by that packet.  Checking
        is done to make sure we haven't exceeded server-wide limits on
        packet queue length.  PokerAvatar will be force-disconnected if
        the packets exceed the value of
        self.service.getClientQueuedPacketMax().  A warning will be
        printed when the packet queue reaches 75% of the limit imposed by
        self.service.getClientQueuedPacketMax()"""
        # This method was introduced when we added the force-disconnect as
        # the stop-gap.
        self._packets_queue.extend(newPackets)
        self.flushLongPollDeferred()
        warnVal = int(.75 * self.service.getClientQueuedPacketMax())
        if len(self._packets_queue) >= warnVal:
            # If we have not warned yet that packet queue is getting long, warn now.
            if not self.warnedPacketExcess:
                self.warnedPacketExcess = True
                self.log.inform("user %d has more than %d packets queued; will force-disconnect when %d are queued",
                    self.getSerial(),
                    warnVal,
                    self.service.getClientQueuedPacketMax()
                )
            if len(self._packets_queue) >= self.service.getClientQueuedPacketMax():
                self.service.forceAvatarDestroy(self)

    def resetPacketsQueue(self):
        self.warnedPacketExcess = False
        queue = self._packets_queue
        self._packets_queue = []
        return queue

    def removeGamePacketsQueue(self, game_id):
        self._packets_queue = filter(lambda packet: not hasattr(packet, "game_id") or packet.game_id != game_id, self._packets_queue)

    def sendPacket(self, packet):
        from pokerengine.pokergame import init_i18n as pokergame_init_i18n
        # Note on special processing of locales on packet send:
        #    Ideally, clients would do their own locale work.  However, in
        #    particular when PokerExplain is in effect, some clients are
        #    requiring explanation strings coming from the server about
        #    what is happening in the game.  (Indeed, PokerExplain exists
        #    for precisely that scenario.)  Therefore, every time we send a
        #    packet via PokerAvatar, we need to make sure the local in
        #    poker-engine's pokergame localization is set properly to the
        #    localization requested by the client (iff. they have
        #    requested one via PacketPokerSetLocale).  Note that because
        #    global variables are effectively only file-wide, the _() that
        #    we create here propagates only as wide as this file.  the
        #    call to pokergame_init_i18n() is what actually changes the
        #    _() defined in pokergame.py.
        #
        #    It is in some ways overkill to redefine our own _() here,
        #    particularly because at the time of writing, we don't
        #    actually have localization strings in the functions in this
        #    file.  However, should we have them later, we'd obviously
        #    want those strings to be localized for the client, at least
        #    during packet sending.
        #
        #    Note that _ default value depends of locale installation
        #    by pokerservice, as
        #    http://docs.python.org/library/gettext.html point out,
        #    gettext.install installs the function _() in Pythons
        #    builtins namespace. Assigning it to self.localeFunc
        #    convert it to a global that is file wise (as pointed
        #    above).

        global _
        if self.localeFunc:
            # First, if our _() has never been defined, we simply set it to None
            try:
                self._avatarSavedUnder = _
            except NameError:
                self._avatarSavedUnder = None
            _ = self.localeFunc
            pokergameSavedUnder = pokergame_init_i18n('', self.localeFunc)
        if self.explain and not isinstance(packet, defer.Deferred) and packet.type != PACKET_ERROR:
            try:
                self.explain.explain(packet)
                packets = self.explain.forward_packets
            except Exception:
                explain_error_message = format_exc()
                packets = [ PacketError(other_type=PACKET_NONE, message=explain_error_message) ]
                self.log.warn('%s', explain_error_message)
                
                # disabling the explain instance that issued the exception, as it
                # may be in an inconsistent state, and used before the avatar destruction
                self.explain = None
                self.service.forceAvatarDestroy(self)
        else:
            packets = [ packet ]
        if self._queue_packets:
            self.extendPacketsQueue(packets)
        else:
            for packet in packets:
                self.protocol.sendPacket(packet)
        if self.localeFunc:
            _ = self._avatarSavedUnder
            pokergame_init_i18n('', pokergameSavedUnder)

    # Below, we assign the method queueDeferred() is the same as
    # sendPacket().  Be careful not to indent the line below; if you
    # aren't paying attention, you might think it belongs inside the
    # previous function.  It doesn't. ...  Ok, so I never got over the
    # "whitespace indentation matters" thing in Python, and I get careless
    # sometimes, then after I do I proceed to write warning comments that
    # normal Python programmers probably don't need. :-p -- bkuhn
    queueDeferred = sendPacket
    
    def sendPacketVerbose(self, packet):
        if hasattr(packet, 'type') and packet.type != PACKET_PING:
            self.log.debug("sendPacket: %s", packet)
        self.sendPacket(packet)
        
    def packet2table(self, packet):
        if hasattr(packet, "game_id") and packet.game_id in self.tables:
            return self.tables[packet.game_id]
        else:
            return False

    def longpollDeferred(self):
        self._longpoll_deferred = defer.Deferred()
        d = self.flushLongPollDeferred()
        if not d.called:
            def longPollDeferredTimeout():
                self.longPollTimer = None
                self._longpoll_deferred = None
                packets = self.resetPacketsQueue()
                self.log.debug("longPollDeferredTimeout(%s)", packets)
                d.callback(packets)
            self.longPollTimer = reactor.callLater(self.service.long_poll_timeout, longPollDeferredTimeout)
        return d

    def blockLongPollDeferred(self):
        self._block_longpoll_deferred = True
        
    def unblockLongPollDeferred(self):
        self._block_longpoll_deferred = False
        self.flushLongPollDeferred()

    def flushLongPollDeferred(self):
        if self._block_longpoll_deferred == False and self._longpoll_deferred and (len(self._packets_queue) > 0 or self._flush_next_longpoll):
            self._flush_next_longpoll = False
            packets = self.resetPacketsQueue()
            self.log.debug("flushLongPollDeferred(%s)", packets)
            d = self._longpoll_deferred
            self._longpoll_deferred = None
            d.callback(packets)
            if self.longPollTimer and self.longPollTimer.active():
                self.longPollTimer.cancel()
            return d
        return self._longpoll_deferred

    def longPollReturn(self):
        if self._longpoll_deferred:
            packets = self.resetPacketsQueue()
            self.log.debug("longPollReturn(%s)", packets)
            d = self._longpoll_deferred
            self._longpoll_deferred = None
            d.callback(packets)
            if self.longPollTimer and self.longPollTimer.active():
                self.longPollTimer.cancel()
        else:
            self._flush_next_longpoll = True
            
    def handleDistributedPacket(self, request, packet, data):
        resthost, game_id = self.service.packet2resthost(packet)
        
        for packet_state in self.handlePokerState(packet, resthost, game_id): 
            self.sendPacket(packet_state)
        
        if resthost and packet.type != PACKET_POKER_LONG_POLL:
            return self.distributePacket(packet, data, resthost, game_id)
        else:
            return self.handlePacketDefer(packet)

    def handlePokerState(self,packet,resthost,game_id):
        packets = []
        if not self.explain: return packets
         
        explain_client_existing = game_id in self.game_id2rest_client and self.explain.games.gameExists(game_id)
        if packet.type != PACKET_POKER_TABLE_JOIN and not resthost and game_id and game_id not in self.tables:
            packets.append(PacketPokerStateInformation(
                message = 'local connection ephemeral',
                code = PacketPokerStateInformation.LOCAL_TABLE_EPHEMERAL,
                game_id = game_id
            ))
        elif packet.type != PACKET_POKER_TABLE_JOIN and resthost and not explain_client_existing:
            packets.append(PacketPokerStateInformation(
                message = 'distributed connection ephemeral',
                code = PacketPokerStateInformation.REMOTE_TABLE_EPHEMERAL,
                game_id = game_id
            ))
        return packets
        
    def getOrCreateRestClient(self, resthost, game_id):
        #
        # no game_id means the request must be delegated for tournament
        # registration or creation. Not for table interaction.
        #
        ( host, port, path ) = resthost
        path += self.distributed_args
        self.log.debug("getOrCreateRestClient(%s, %d, %s, %s)", host, port, path, game_id)
        if game_id:
            if game_id not in self.game_id2rest_client:
                self.game_id2rest_client[game_id] = PokerRestClient(host, port, path, longPollCallback = lambda packets: self.incomingDistributedPackets(packets, game_id))
            client = self.game_id2rest_client[game_id]
        else:
            client = PokerRestClient(host, port, path, longPollCallback = None)
        return client
            
    def distributePacket(self, packet, data, resthost, game_id):
        ( host, port, path ) = resthost
        client = self.getOrCreateRestClient(resthost, game_id)
        d = client.sendPacket(packet, data)
        d.addCallback(lambda packets: self.incomingDistributedPackets(packets, game_id))
        d.addCallback(lambda x: self.resetPacketsQueue())
        return d
            
    def incomingDistributedPackets(self, packets, game_id,block=True):
        self.log.debug("incomingDistributedPackets(%s, %s)", packets, game_id)
        
        if block: self.blockLongPollDeferred()
        for packet in packets:
            self.sendPacket(packet)

        if game_id:
            if game_id not in self.tables and (not(self.explain) or not(self.explain.games.gameExists(game_id))):
                #
                # discard client if nothing pending and not in the list
                # of active tables
                #
                client = self.game_id2rest_client.get(game_id,None)
                if client and (len(client.queue.callbacks) <= 0 or client.pendingLongPoll):
                    restclient = self.game_id2rest_client.pop(game_id)
                    restclient.cancel()
                    
        if block: self.unblockLongPollDeferred()            

    def handlePacketDefer(self, packet):
        self.log.debug("handlePacketDefer: %s", packet)

        self.queuePackets()

        if packet.type == PACKET_POKER_LONG_POLL:
            return self.longpollDeferred()

        if packet.type == PACKET_POKER_LONG_POLL_RETURN:
            self.longPollReturn()
            return []

        self.handlePacketLogic(packet)
        packets = self.resetPacketsQueue()
        if len(packets) == 1 and isinstance(packets[0], defer.Deferred):
            d = packets[0]
            #
            # turn the return value into an List if it is not
            #
            def packetList(result):
                if type(result) == list:
                    return result
                else:
                    return [ result ]
            d.addCallback(packetList)
            return d
        else:
            return packets

    def handlePacket(self, packet):
        self.queuePackets()
        self.handlePacketLogic(packet)
        self.noqueuePackets()
        return self.resetPacketsQueue()

    def handlePacketLogic(self, packet):
        if packet.type != PACKET_PING:
            self.log.debug("handlePacketLogic: %s", packet)

        if packet.type == PACKET_POKER_EXPLAIN:
            if self.setExplain(packet.value):
                self.sendPacketVerbose(PacketAck())
            else:
                self.sendPacketVerbose(PacketError(other_type = PACKET_POKER_EXPLAIN))
            return
        
        if packet.type == PACKET_POKER_SET_LOCALE:
            if self.setLocale(packet.locale):
                self.sendPacketVerbose(PacketAck())
            else:
                self.sendPacketVerbose(PacketPokerError(
                     serial = self.getSerial(), 
                     other_type = PACKET_POKER_SET_LOCALE
                ))
            return

        if packet.type == PACKET_POKER_STATS_QUERY:
            self.sendPacketVerbose(self.service.stats(packet.string))
            return
        
        if packet.type == PACKET_POKER_MONITOR:
            self.sendPacketVerbose(self.service.monitor(self))
            return
        
        if packet.type == PACKET_PING:
            return
        
        if not self.isAuthorized(packet.type):
            self.sendPacketVerbose(PacketAuthRequest())
            return

        if packet.type in (PACKET_LOGIN,PACKET_AUTH):
            if self.isLogged():
                self.sendPacketVerbose(PacketError(
                    other_type = PACKET_LOGIN,
                    code = PacketLogin.LOGGED,
                    message = "already logged in"
                ))
            else:
                self.auth(packet)
            return

        if packet.type == PACKET_POKER_GET_PLAYER_PLACES:
            if packet.serial != 0:
                self.sendPacketVerbose(self.service.getPlayerPlaces(packet.serial))
            else:
                self.sendPacketVerbose(self.service.getPlayerPlacesByName(packet.name))
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
                self.log.inform("attempt to get user info for user %d by user %d", packet.serial, self.getSerial())
            return

        elif packet.type == PACKET_POKER_GET_PERSONAL_INFO:
            if self.getSerial() == packet.serial:
                self.getPersonalInfo(packet.serial)
            else:
                self.log.inform("attempt to get personal info for user %d by user %d", packet.serial, self.getSerial())
                self.sendPacketVerbose(PacketAuthRequest())
            return

        elif packet.type == PACKET_POKER_PLAYER_INFO:
            if self.getSerial() == packet.serial:
                if self.setPlayerInfo(packet):
                    self.sendPacketVerbose(packet)
                else:
                    self.sendPacketVerbose(PacketError(
                        other_type = PACKET_POKER_PLAYER_INFO,
                        code = PACKET_POKER_PLAYER_INFO,
                        message = "Failed to save set player information"
                    ))
            else:
                self.log.inform("attempt to set player info for player %d by player %d", packet.serial, self.getSerial())
            return
                
        elif packet.type == PACKET_POKER_PLAYER_IMAGE:
            if self.getSerial() == packet.serial:
                if self.service.setPlayerImage(packet):
                    self.sendPacketVerbose(PacketAck())
                else:
                    self.sendPacketVerbose(PacketError(
                        other_type = PACKET_POKER_PLAYER_IMAGE,
                        code = PACKET_POKER_PLAYER_IMAGE,
                        message = "Failed to save set player image"
                    ))
            else:
                self.log.inform("attempt to set player image for player %d by player %d", packet.serial, self.getSerial())
            return
                
        elif packet.type == PACKET_POKER_PERSONAL_INFO:
            if self.getSerial() == packet.serial:
                self.setPersonalInfo(packet)
            else:
                self.log.inform("attempt to set player info for player %d by player %d", packet.serial, self.getSerial())
            return

        elif packet.type == PACKET_POKER_CASH_IN:
            if self.getSerial() == packet.serial:
                self.queueDeferred(self.service.cashIn(packet))
            else:
                self.log.inform("attempt to cash in for user %d by user %d", packet.serial, self.getSerial())
                self.sendPacketVerbose(PacketPokerError(serial = self.getSerial(), other_type = PACKET_POKER_CASH_IN))
            return

        elif packet.type == PACKET_POKER_CASH_OUT:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.service.cashOut(packet))
            else:
                self.log.inform("attempt to cash out for user %d by user %d", packet.serial, self.getSerial())
                self.sendPacketVerbose(PacketPokerError(serial = self.getSerial(), other_type = PACKET_POKER_CASH_OUT))
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

        elif packet.type in (PACKET_POKER_SET_ACCOUNT,PACKET_POKER_CREATE_ACCOUNT):
            if self.getSerial() != packet.serial:
                packet.serial = 0
            self.sendPacketVerbose(self.service.setAccount(packet))
            return

        if packet.type == PACKET_POKER_TOURNEY_SELECT:
            (playerCount, tourneyCount) = self.service.tourneyStats()
            tourneys = self.service.tourneySelect(packet.string)
            
            self.sendPacketVerbose(PacketPokerTourneyList(
                players = playerCount,
                tourneys = tourneyCount,
                packets = [PacketPokerTourney(**tourney) for tourney in tourneys]
            ))
            tourneyInfo = self.service.tourneySelectInfo(packet, tourneys)
            if tourneyInfo:
                self.sendPacketVerbose(tourneyInfo)
            return
        
        elif packet.type == PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST:
            self.sendPacketVerbose(self.service.tourneyPlayersList(packet.tourney_serial))
            return

        elif packet.type == PACKET_POKER_GET_TOURNEY_MANAGER:
            self.sendPacketVerbose(self.service.tourneyManager(packet.tourney_serial))
            return
        
        elif packet.type == PACKET_POKER_GET_TOURNEY_PLAYER_STATS:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.service.tourneyPlayerStats(packet.tourney_serial,packet.serial))
            else:
                self.log.inform("attempt to receive stats in tournament %d for player %d by player %d",
                    packet.tourney_serial, packet.serial, self.getSerial()
                )
            return
        
        elif packet.type == PACKET_POKER_TOURNEY_REGISTER:
            if self.getSerial() == packet.serial:
                self.service.autorefill(packet.serial)
                self.service.tourneyRegister(packet)
                self.tourneyUpdates(packet.serial)
            else:
                self.log.inform("attempt to register in tournament %d for player %d by player %d",
                    packet.tourney_serial, packet.serial, self.getSerial()
                )
            return
            
        elif packet.type == PACKET_POKER_TOURNEY_UNREGISTER:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.service.tourneyUnregister(packet))
                self.tourneyUpdates(packet.serial)
            else:
                self.log.inform("attempt to unregister from tournament %d for player %d by player %d",
                    packet.tourney_serial, packet.serial, self.getSerial()
                )
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
                self.log.inform("attempt to get history of player %d by player %d", packet.serial, self.getSerial())
            return

        elif packet.type == PACKET_POKER_HAND_SELECT_ALL:
            self.listHands(packet, None)
            return

        elif packet.type == PACKET_POKER_TABLE_JOIN:
            self.performPacketPokerTableJoin(packet)
            return

        elif packet.type == PACKET_POKER_TABLE_PICKER:
            self.performPacketPokerTablePicker(packet)
            return

        table = self.packet2table(packet)
            
        if table:
            self.log.debug("packet for table %s", table.game.id)
            game = table.game

            if packet.type == PACKET_POKER_READY_TO_PLAY:
                if self.getSerial() == packet.serial:
                    self.sendPacketVerbose(table.readyToPlay(packet.serial))
                else:
                    self.log.inform("attempt to set ready to play for player %d by player %d",
                        packet.serial,
                        self.getSerial()
                    )

            elif packet.type == PACKET_POKER_PROCESSING_HAND:
                if self.getSerial() == packet.serial:
                    if not self.bugous_processing_hand:
                        self.sendPacketVerbose(table.processingHand(packet.serial))
                    else:
                        self.sendPacketVerbose(PacketPokerError(
                            game_id = game.id,
                            serial = self.getSerial(),
                            other_type = PACKET_POKER_PROCESSING_HAND
                        ))
                else:
                    self.log.inform("attempt to set processing hand for player %d by player %d",
                        packet.serial,
                        self.getSerial()
                    )

            elif packet.type == PACKET_POKER_START:
                if not game.isEndOrNull():
                    self.log.inform("player %d tried to start a new game while in game", self.getSerial())
                    self.sendPacketVerbose(PacketPokerStart(game_id = game.id))
                elif self.service.shutting_down:
                    self.log.inform("server shutting down")
                elif table.owner != 0:
                    if self.getSerial() != table.owner:
                        self.log.inform("player %d tried to start a new game but is not the owner of the table", self.getSerial())
                        self.sendPacketVerbose(PacketPokerStart(game_id = game.id))
                    else:
                        table.beginTurn()
                else:
                    self.log.inform("player %d tried to start a new game but is not the owner of the table", self.getSerial())

            elif packet.type == PACKET_POKER_SEAT:
                self.performPacketPokerSeat(packet, table, game)

            elif packet.type == PACKET_POKER_BUY_IN:
                self.performPacketPokerBuyIn(packet, table, game)

            elif packet.type == PACKET_POKER_REBUY:
                if self.getSerial() == packet.serial:
                    self.service.autorefill(packet.serial)
                    if not table.rebuyPlayerRequest(self, packet.amount):
                        self.sendPacketVerbose(PacketPokerError(
                            game_id = game.id,
                            serial = packet.serial,
                            other_type = PACKET_POKER_REBUY
                        ))
                else:
                    self.log.inform("attempt to rebuy for player %d by player %d", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_CHAT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.chatPlayer(self, packet.serial, packet.message[:128])
                else:
                    self.log.inform("attempt to chat for player %d by player %d", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_PLAYER_LEAVE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.leavePlayer(self, packet.serial)
                else:
                    self.log.inform("attempt to leave for player %d by player %d", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_SIT:
                self.performPacketPokerSit(packet, table)
                
            elif packet.type == PACKET_POKER_SIT_OUT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.sitOutPlayer(self, packet.serial)
                else:
                    self.log.inform("attempt to sit out for player %d by player %d", packet.serial, self.getSerial())
                
            elif packet.type == PACKET_POKER_AUTO_BLIND_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.autoBlindAnte(self, packet.serial, True)
                else:
                    self.log.inform("attempt to set auto blind/ante for player %d by player %d", packet.serial, self.getSerial())
                
            elif packet.type == PACKET_POKER_NOAUTO_BLIND_ANTE:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.autoBlindAnte(self, packet.serial, False)
                else:
                    self.log.inform("attempt to set auto blind/ante for player %d by player %d",packet.serial, self.getSerial())
            
            elif packet.type == PACKET_POKER_AUTO_MUCK:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.getPlayer(packet.serial):
                    game.autoMuck(packet.serial, packet.auto_muck)
                else:
                    self.log.inform("attempt to set auto muck for player %d by player %d, or player is not in game", packet.serial, self.getSerial())
                
            elif packet.type == PACKET_POKER_MUCK_ACCEPT:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.muckAccept(self, packet.serial)
                else:
                    self.log.inform("attempt to accept muck for player %d by player %d", packet.serial, self.getSerial())
                    
            elif packet.type == PACKET_POKER_MUCK_DENY:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    table.muckDeny(self, packet.serial)
                else:
                    self.log.inform("attempt to deny muck for player %d by player %d", packet.serial, self.getSerial())
                
            elif packet.type == PACKET_POKER_AUTO_PLAY:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.getPlayer(packet.serial):
                    table.game.autoPlay(packet.serial, packet.auto_muck)
                else:
                    self.log.inform("attempt to set auto play for player %d by player %d, or player is not in game", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_BLIND:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.isPlaying(packet.serial):
                    game.blind(packet.serial)
                else:
                    self.log.inform("attempt to pay the blind of player %d by player %d, or player is not not playing", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_WAIT_BIG_BLIND:
                if self.getSerial() == packet.serial or self.getSerial() == table.owner:
                    game.waitBigBlind(packet.serial)
                else:
                    self.log.inform("attempt to wait for big blind of player %d by player %d", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_ANTE:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.isPlaying(packet.serial):
                    game.ante(packet.serial)
                else:
                    self.log.inform("attempt to pay the ante of player %d by player %d, or player is not not playing", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_LOOK_CARDS:
                table.broadcast(packet)
                
            elif packet.type == PACKET_POKER_FOLD:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.isPlaying(packet.serial):
                    game.fold(packet.serial)
                else:
                    self.log.inform("attempt to fold player %d by player %d, or player is not not playing", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_CALL:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.isPlaying(packet.serial):
                    game.call(packet.serial)
                else:
                    self.log.inform("attempt to call for player %d by player %d, or player is not not playing", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_RAISE:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.isPlaying(packet.serial):
                    game.callNraise(packet.serial, packet.amount)
                else:
                    self.log.inform("attempt to raise for player %d by player %d, or player is not not playing", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_CHECK:
                if (self.getSerial() == packet.serial or self.getSerial() == table.owner) and game.isPlaying(packet.serial):
                    game.check(packet.serial)
                else:
                    self.log.inform("attempt to check for player %d by player %d, or player is not not playing", packet.serial, self.getSerial())

            elif packet.type == PACKET_POKER_TABLE_QUIT:
                table.quitPlayer(self, self.getSerial())

            elif packet.type == PACKET_POKER_HAND_REPLAY and packet.serial==table.game.hand_serial and table.game.isRunning():
                self.sendPacketVerbose(PacketPokerError(
                    game_id = game.id,
                    serial = self.getSerial(),
                    other_type = PACKET_POKER_HAND_REPLAY,
                    message = 'game is still running'
                ))
            
            table.update()
    
        elif packet.type == PACKET_POKER_HAND_REPLAY:
            self.handReplay(packet.game_id, packet.serial)

        elif packet.type == PACKET_POKER_TABLE: # can only be done by User.ADMIN
            table = self.createTable(packet)
            
        elif packet.type == PACKET_POKER_CREATE_TOURNEY: # can only be done by User.ADMIN
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.performPacketPokerCreateTourney(packet))
            else:
                self.log.inform("attempt to create tourney for player %d by player %d", packet.serial, self.getSerial())
                self.sendPacketVerbose(PacketAuthRequest())
        
        elif packet.type == PACKET_POKER_TOURNEY_START:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.performPacketPokerTourneyStart(packet))
            else:
                self.log.inform("attempt to start tournament %d for player %d by player %d",
                    packet.tourney_serial, packet.serial, self.getSerial()
                )
                
        elif packet.type == PACKET_POKER_TOURNEY_CANCEL:
            if self.getSerial() == packet.serial:
                self.sendPacketVerbose(self.performPacketPokerTourneyCancel(packet))
            else:
                self.log.inform("attempt to cancel tournament %d for player %d by player %d",
                    packet.tourney_serial, packet.serial, self.getSerial()
                )
                
        
        elif packet.type == PACKET_QUIT:
            for table in self.tables.values():
                table.quitPlayer(self, self.getSerial())

        elif packet.type == PACKET_LOGOUT:
            if self.isLogged():
                for table in self.tables.values():
                    table.quitPlayer(self, self.getSerial())
                self.logout()
            else:
                self.sendPacketVerbose(PacketError(
                    code = PacketLogout.NOT_LOGGED_IN,
                    message = "Not logged in",
                    other_type = PACKET_LOGOUT
                ))
        else:
            pass

    # The "perform" methods below are designed so that the a minimal
    # amount of code related to receiving a packet that appears in the
    # handlePacketLogic() giant if statement above.  The primary motive
    # for this is for things like PacketTablePicker(), that need to
    # perform operations *as if* the client has sent additional packets.
    # The desire is to keep completely parity between what the individual
    # packets do by themselves, and what "super-packets" like
    # PacketTablePicker() do.  A secondary benefit is that it makes that
    # giant if statement in handlePacketLogic() above a bit smaller.
    # -------------------------------------------------------------------------
    def performPacketPokerTableJoin(self, packet, table = None,
                                    deprecatedEmptyTableBehavior = True,
                                    requestorPacketType = PACKET_POKER_TABLE_JOIN,
                                    reason = PacketPokerTable.REASON_TABLE_JOIN):
        """Perform the operations that must occur when a
        PACKET_POKER_TABLE_JOIN is received."""
        
        if not table:
            table = self.service.getTable(packet.game_id)
        if table:
            self.removeGamePacketsQueue(packet.game_id)
            if not table.joinPlayer(self, self.getSerial(),reason = reason):
                if deprecatedEmptyTableBehavior:
                    self.sendPacketVerbose(PacketPokerTable(reason = reason))
                self.sendPacketVerbose(PacketPokerError(
                    code = PacketPokerTableJoin.GENERAL_FAILURE,
                    message = "Unable to join table for unknown reason",
                    other_type = requestorPacketType,
                    serial = self.getSerial(),
                    game_id = 0
                ))
            else:
                player = table.game.getPlayer(self.getSerial())
                if player and player.isAuto():
                    self.sendPacketVerbose(PacketPokerAutoFold(serial=packet.serial))
        return table
    # -------------------------------------------------------------------------
    def performPacketPokerSeat(self, packet, table, game):
        """Perform the operations that must occur when a PACKET_POKER_SEAT
        is received."""

        if PacketPokerRoles.PLAY not in self.roles:
            self.sendPacketVerbose(PacketPokerError(
                game_id = game.id,
                serial = packet.serial,
                code = PacketPokerSeat.ROLE_PLAY,
                message = "PACKET_POKER_ROLES must set the role to PLAY before chosing a seat",
                other_type = PACKET_POKER_SEAT
            ))
            return False
        elif self.getSerial() == packet.serial or self.getSerial() == table.owner:
            if not table.seatPlayer(self, packet.serial, packet.seat):
                packet.seat = -1
            else:
                packet.seat = game.getPlayer(packet.serial).seat
            self.getUserInfo(packet.serial)
            self.sendPacketVerbose(packet)
            return (packet.seat != -1)
        else:
            self.log.inform("attempt to get seat for player %d by player %d", packet.serial, self.getSerial())
            return False
    # -------------------------------------------------------------------------
    def performPacketPokerBuyIn(self, packet, table, game):
        if self.getSerial() == packet.serial:
            self.service.autorefill(packet.serial)
            if not table.buyInPlayer(self, packet.amount):
                self.sendPacketVerbose(PacketPokerError(
                    game_id = game.id,
                    serial = packet.serial,
                    other_type = PACKET_POKER_BUY_IN
                ))
                return False
            else:
                return True
        else:
            self.log.inform("attempt to bring money for player %d by player %d", packet.serial, self.getSerial())
            return False
    # -------------------------------------------------------------------------
    def performPacketPokerSit(self, packet, table):
        if self.getSerial() == packet.serial or self.getSerial() == table.owner:
            table.sitPlayer(self, packet.serial)
            return True
        else:
            self.log.inform("attempt to sit back for player %d by player %d", packet.serial, self.getSerial())
            return False
    
    def performPacketPokerCreateTourney(self,packet):
        error = None
        if max(packet.players_quota,len(packet.players)) < 2:
            error = PacketError(
                other_type = PACKET_POKER_CREATE_TOURNEY,
                code = 0,
                message = "Cannot create Tourney with less than 2 people"
            )
        if error:
            self.log.error("%s", error)
            return error
        
        return self.service.tourneyCreate(packet)
        
    def performPacketPokerTourneyStart(self, packet):
        can_perform_changes, error = self.canPerformTourneyChanges(packet.serial, packet.tourney_serial)
        if not can_perform_changes: return error
        tourney = self.service.tourneys[packet.tourney_serial]
        if tourney.registered <= 1:
            return PacketError(
                other_type = PACKET_POKER_TOURNEY,
                code = PacketPokerTourneyStart.NOT_ENOUGH_USERS,
                message = "Tournament %d needs a min. of 2 users" % tourney.serial
            )
        return self.service.tourneyStart(tourney)
        
    def performPacketPokerTourneyCancel(self, packet):
        can_perform_changes, error = self.canPerformTourneyChanges(packet.serial, packet.tourney_serial)
        if not can_perform_changes: return error
        tourney = self.service.tourneys[packet.tourney_serial]
        tourney.changeState(TOURNAMENT_STATE_CANCELED)
        return PacketAck()
    
    def canPerformTourneyChanges(self, serial, tourney_serial):
        tourney = self.service.tourneys.get(tourney_serial,None)
        error = None
        
        if tourney_serial not in self.service.tourneys:
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY,
                code = PacketPokerTourneyStart.DOES_NOT_EXIST,
                message = "Tournament %d does not exist" % tourney_serial
            )
        
        elif tourney.state != TOURNAMENT_STATE_REGISTERING:
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY,
                code = PacketPokerTourneyStart.WRONG_STATE,
                message = "Tournament %d not in state %s" % (tourney_serial,TOURNAMENT_STATE_REGISTERING)
            )
        
        # user has to be the bailor (or an admin) in order to start a tourney
        elif not self.user.hasPrivilege(User.ADMIN) and tourney.bailor_serial != serial:
            error = PacketError(
                other_type = PACKET_POKER_TOURNEY,
                code = PacketPokerTourneyStart.NOT_BAILOR,
                message = "Player %d is not the bailor for Tournament %d" % (serial, tourney_serial)
            )
            
        if error:
            self.log.error("%s", error)
            return (False, error)
        else:
            return (True, None)
                
    # -------------------------------------------------------------------------
    def performPacketPokerTablePicker(self, packet):
        mySerial = self.getSerial()
        if mySerial != packet.serial:
            errMsg = "attempt to run table picker for player %d by player %d" % ( packet.serial, mySerial )
            self.log.warn("%s", errMsg)
            self.sendPacketVerbose(PacketPokerError(
                code = PacketPokerTableJoin.GENERAL_FAILURE,
                message = errMsg,
                other_type = PACKET_POKER_TABLE_PICKER,
                serial = mySerial,
                game_id = 0
            ))
        else:
            # Call autorefill() first before checking for a table,
            # since the amount of money we have left will impact the
            # table selection, and in a play-money scenario, we want
            # to have whatever play-money we can get before picking.
            self.service.autorefill(packet.serial)

            table = self.service.getTableBestByCriteria(
                mySerial,
                min_players = packet.min_players, currency_serial = packet.currency_serial,
                variant = packet.variant, betting_structure = packet.betting_structure
            )

            if not table:
                # If we cannot find a table, tell user we were unable to
                # find a table matching their criteria
                self.sendPacketVerbose(PacketPokerError(
                    code = PacketPokerTableJoin.GENERAL_FAILURE,
                    message = "No table found matching given criteria",
                    other_type = PACKET_POKER_TABLE_PICKER,
                    serial = mySerial,
                    game_id = 0
                ))
            elif not table.game.canAddPlayer(mySerial):
                # If the table we found just can't take us, tell user we
                # could not add them.
                self.sendPacketVerbose(PacketPokerError(
                    code = PacketPokerTableJoin.GENERAL_FAILURE,
                    message = "Found matching table, but unable to join it.",
                    other_type = PACKET_POKER_TABLE_PICKER,
                    serial = mySerial,
                    game_id = table.game.id
                ))
            else:
                # Otherwise, we perform the sequence of operations
                # that is defined by the semantics of this packet in
                # pokerpacket.py.  Basically, we perform:
                #   PacketTableJoin(), and if it succeeds,
                #   PacketPokerSeat(), and if it succeeds,
                #   We figure out our best buy-in choice, buyIn, then perform:
                #   PacketPokerBuyIn(amount = buyIn), and if it succeeds, 
                #   PacketPokerSit()
                if self.performPacketPokerTableJoin(
                    PacketPokerTableJoin(serial = mySerial,game_id = table.game.id), 
                    table,
                    deprecatedEmptyTableBehavior = False,
                    reason = PacketPokerTable.REASON_TABLE_PICKER
                ):

                    # Giving no seat argument at all for the packet should cause
                    # us to get any available seat.
                    if self.performPacketPokerSeat(
                        PacketPokerSeat(serial = mySerial, game_id = table.game.id),
                        table, table.game
                    ):

                        # Next, determine if player can afford the "best"
                        # buy in.  If the player can't, give them the
                        # minimum buyin.

                        buyIn = table.game.bestBuyIn()
                        if self.service.getMoney(mySerial, table.currency_serial) < buyIn:
                            buyIn = table.game.buyIn()
                            # No need to check above if we have that,
                            # since our answer on this table came from
                            # self.service.getTableByBestCriteria(), which
                            # promises us that we have at least minimum.
                        if self.performPacketPokerBuyIn(
                            PacketPokerBuyIn(
                                serial = mySerial, amount = buyIn,
                                game_id = table.game.id
                            ), 
                            table, table.game
                        ):
                            if packet.auto_blind_ante:
                                table.autoBlindAnte(self, packet.serial, True)
                            self.performPacketPokerSit(
                                PacketPokerSit(serial = mySerial, game_id = table.game.id),
                                table
                            )
                            table.update()

    # -------------------------------------------------------------------------
    def setPlayerInfo(self, packet):
        self.user.url = packet.url
        self.user.outfit = packet.outfit
        return self.service.setPlayerInfo(packet)

    def setPersonalInfo(self, packet):
        self.personal_info = packet
        self.service.setPersonalInfo(packet)

    def setRole(self, packet):
        if packet.roles not in PacketPokerRoles.ROLES:
            return PacketError(
                code = PacketPokerSetRole.UNKNOWN_ROLE,
                message = "role %s is unknown (roles = %s)" % ( packet.roles, PacketPokerRoles.ROLES),
                other_type = PACKET_POKER_SET_ROLE
            )

        if packet.roles in self.roles:
            return PacketError(
                code = PacketPokerSetRole.NOT_AVAILABLE,
                message = "another client already has role %s" % packet.roles,
                other_type = PACKET_POKER_SET_ROLE
            )
        self.roles.add(packet.roles)
        return PacketPokerRoles(
            serial = packet.serial,
            roles = join(self.roles, " ")
        )
            
    def getPlayerInfo(self):
        if self.user.isLogged():
            return PacketPokerPlayerInfo(
                serial = self.getSerial(),
                name = self.getName(),
                url = self.user.url,
                outfit = self.user.outfit
            )
        else:
            return PacketError(
                code = PacketPokerGetPlayerInfo.NOT_LOGGED,
                message = "Not logged in",
                other_type = PACKET_POKER_GET_PLAYER_INFO
            )
    
    def listPlayers(self, packet):
        table = self.service.getTable(packet.game_id)
        if table:
            players = table.listPlayers()
            self.sendPacketVerbose(PacketPokerPlayersList(
                game_id = packet.game_id,
                players = players
            ))
        
    def listTables(self, packet):
        packets = []
        for table in self.service.listTables(packet.string, self.getSerial()):
            packet = PacketPokerTable(
                id = int(table['serial']),
                name = table['name'],
                variant = table['variant'],
                betting_structure = table['betting_structure'],
                seats = int(table['seats']),
                players = int(table['players']),
                hands_per_hour = int(table['hands_per_hour']),
                average_pot = int(table['average_pot']),
                percent_flop = int(table['percent_flop']),
                player_timeout = int(table['player_timeout']),
                muck_timeout = int(table['muck_timeout']),
                observers = int(table['observers']),
                waiting = int(table['waiting']),
                skin = table['skin'],
                currency_serial = int(table['currency_serial']),
                player_seated = int(table.get('player_seated',-1)),
                tourney_serial = int(table['tourney_serial']),
                reason = PacketPokerTable.REASON_TABLE_LIST,
            )            
            packets.append(packet)
            
        (players, tables) = self.service.statsTables()
        self.sendPacketVerbose(PacketPokerTableList(
            players = players,
            tables = tables,
            packets = packets
        ))
        
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
        self.sendPacketVerbose(PacketPokerHandList(
            string = packet.string,
            start = start,
            count = count,
            hands = hands,
            total = total
        ))

    def createTable(self, packet):
        table = self.service.createTable(self.getSerial(), {
            "seats": packet.seats,
            "name": packet.name,
            "variant": packet.variant,
            "betting_structure": packet.betting_structure,
            "player_timeout": packet.player_timeout,
            "muck_timeout": packet.muck_timeout,
            "currency_serial": packet.currency_serial,
            "skin": packet.skin,
            "reason" : packet.reason
        })
        if not table:
            self.sendPacketVerbose(PacketError(
                message = PacketPokerTable.REASON_TABLE_CREATE,
                other_type = PACKET_POKER_TABLE
            ))
        else:
            self.sendPacketVerbose(PacketAck())
        return table            

    def join(self, table, reason = ""):
        game = table.game
        self.tables[game.id] = table

        packet = table.toPacket()
        packet.reason = reason
        self.sendPacketVerbose(packet)
        self.sendPacketVerbose(PacketPokerBuyInLimits(
            game_id = game.id,
            min = game.buyIn(),
            max = game.maxBuyIn(),
            best = game.bestBuyIn(),
            rebuy_min = game.minMoney()
        ))
        self.sendPacketVerbose(PacketPokerBatchMode(game_id = game.id))
        nochips = 0
        for player in game.serial2player.values():
            player_info = table.getPlayerInfo(player.serial)
            self.sendPacketVerbose(PacketPokerPlayerArrive(
                game_id = game.id,
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
                seat = player.seat,
                buy_in_payed = player.buy_in_payed
            ))
            if self.service.has_ladder:
                packet = self.service.getLadder(game.id, table.currency_serial, player.serial)
                if packet.type == PACKET_POKER_PLAYER_STATS:
                    self.sendPacketVerbose(packet)
            if not game.isPlaying(player.serial):
                self.sendPacketVerbose(PacketPokerPlayerChips(
                    game_id = game.id,
                    serial = player.serial,
                    bet = nochips,
                    money = player.money
                ))
                if game.isSit(player.serial):
                    self.sendPacketVerbose(PacketPokerSit(
                        game_id = game.id,
                        serial = player.serial
                    ))
                if player.isAuto():
                    self.sendPacketVerbose(PacketPokerAutoFold(
                        game_id = game.id,
                        serial = player.serial
                    ))

        self.sendPacketVerbose(PacketPokerSeats(game_id = game.id, seats = game.seats()))
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
            packets, previous_dealer, errors = history2packets(game.historyGet(), game.id, -1, createCache()) #@UnusedVariable
            for error in errors: table.log.error("%s", error)
            timeout_packet = table.getCurrentTimeoutWarning()
            if timeout_packet:
                packets.append(timeout_packet)
            for past_packet in packets:
                self.sendPacketVerbose(table.private2public(past_packet, self.getSerial()))
        self.sendPacketVerbose(PacketPokerStreamMode(game_id = game.id))

    def addPlayer(self, table, seat):
        serial = self.getSerial()
        player = table.game.addPlayer(serial, seat, name=self.getName())
        if player:
            player.setUserData(DEFAULT_PLAYER_USER_DATA.copy())
        table.sendNewPlayerInformation(serial)
        
    def connectionLost(self, reason):
        self.log.debug("connection lost for %s/%d", self.getName(), self.getSerial())
        self.blockLongPollDeferred()
        for table in self.tables.values():
            table.disconnectPlayer(self, self.getSerial())
        self.logout()
        for game_id, restclient in self.game_id2rest_client.iteritems():
            restclient.cancel()
            self.sendPacket(PacketPokerStateInformation(
                message = 'connection closed',
                code = PacketPokerStateInformation.REMOTE_CONNECTION_LOST,
                game_id = game_id,
                serial = self.getSerial()
            ))
        self.game_id2rest_client = {}
        self._flush_next_longpoll = True
        self.unblockLongPollDeferred()
        
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
        avatars = table.avatar_collection.get(serial)
        self_is_last_avatar = len(avatars) == 1 and avatars[0] == self
        if self_is_last_avatar and game.removePlayer(serial):
            #
            # If the player is not in a game, the removal will be effective
            # immediately and can be announced to all players, including
            # the one that will be removed.
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
            packets = [
                PacketPokerPlayerChips(
                    game_id = game.id,
                    serial = serial,
                    bet = game.getPlayer(serial).bet,
                    money = game.getPlayer(serial).money
                ),
                PacketPokerSit(
                    game_id = game.id,
                    serial = serial
                )
            ]
            table.broadcast(packets)

    def sitOutPlayer(self, table, serial):
        game = table.game
        if table.isOpen():
            if game.sitOutNextTurn(serial):
                table.broadcast(PacketPokerSitOut(
                    game_id = game.id,
                    serial = serial
                ))
        else:
            game.autoPlayer(serial)
            table.broadcast(PacketPokerAutoFold(
                game_id = game.id,
                serial = serial
            ))

    def autoBlindAnte(self, table, serial, auto):
        game = table.game
        if game.isTournament():
            return
        game.getPlayer(serial).auto_blind_ante = auto
        if auto:
            self.sendPacketVerbose(PacketPokerAutoBlindAnte(
                game_id = game.id,
                serial = serial
            ))
        else:
            self.sendPacketVerbose(PacketPokerNoautoBlindAnte(
                game_id = game.id,
                serial = serial
            ))
                                                              
    def setMoney(self, table, amount):
        game = table.game
        if game.payBuyIn(self.getSerial(), amount):
            player = game.getPlayer(self.getSerial())
            nochips = 0
            table.broadcast(PacketPokerPlayerChips(
                game_id = game.id,
                serial = self.getSerial(),
                bet = nochips,
                money = player.money)
            )
            return True
        else:
            return False
        
    def handReplay(self, game_id, hand_serial):
        history = self.service.loadHand(hand_serial)
        cache = createCache()
        if not history:
            self.sendPacketVerbose(PacketError(
                serial = self.getSerial(),
                other_type = PACKET_POKER_HAND_REPLAY,
                message = 'hand not existing'
            ))
            return False
        
        event_type, level, hand_serial, hands_count, time, variant, betting_structure, player_list, dealer, serial2chips = history[0]  # @UnusedVariable
        serial2name = dict(self.service.getNames(player_list))
        packets = []
        packets.append(PacketPokerTable(
            id = game_id,
            seats = 10,
            name = '*REPLAY*',
            variant = variant,
            betting_structure = betting_structure,
            reason  = PacketPokerTable.REASON_HAND_REPLAY
        ))
        for seat,serial in enumerate(player_list):
            packets.append(PacketPokerPlayerArrive(
                serial = serial,
                name = serial2name.get(serial,'player_%d' % serial),
                game_id = game_id,
                seat = seat
            ))
            packets.append(PacketPokerPlayerChips(
                serial = serial,
                game_id = game_id,
                money = serial2chips[serial]
            ))
            packets.append(PacketPokerSit(
                serial = serial,
                game_id = game_id
            ))
        history_packets, previous_dealer, errors = history2packets(history, game_id, -1, cache) #@UnusedVariable
        packets.extend(history_packets)
        packets.append(PacketPokerTableDestroy(
            game_id = game_id
        ))
        
        for packet in packets:
            if packet.type == PACKET_POKER_PLAYER_CARDS and packet.serial == self.getSerial():
                packet.cards = cache["pockets"][self.getSerial()].toRawList()
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                continue
            self.sendPacketVerbose(packet)
        
        
