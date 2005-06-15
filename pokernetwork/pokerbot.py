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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#  Henry Precheur <henry@precheur.org>
#
import sys
sys.path.insert(0, "..")

from os import popen
from string import split
from random import randint
from traceback import print_exc

from twisted.application import internet, service, app
from twisted.python import components
from twisted.persisted import sob
from twisted.internet import reactor, error

from pokerengine.pokerchips import PokerChips
from pokerengine.pokertournament import *

from pokernetwork.config import Config
from pokernetwork.pokerpackets import *
from pokernetwork.pokerclient import PokerClientFactory, PokerClientProtocol
from pokernetwork.user import checkName

LEVEL2ITERATIONS = {
    0: 10,
    1: 1000,
    2: 10000,
    3: 50000,
    4: 100000,
    5: 200000
    }

STATE_RUNNING = 0
STATE_RECONNECTING = 1
STATE_SEARCHING = 2
STATE_BATCH = 3

#
# If name generation is slow use /dev/urandom instead of
# /dev/random. apg will switch to /dev/urandom if it cannot
# open it for reading. chmod go-rw /dev/random will do this
# trick if not running the bots as root.
#
class StringGenerator:

    def __init__(self, name_prefix):
        self.name_prefix = name_prefix
        self.pool = []

    def getName(self):
        return self.name_prefix + self.getString()

    def getPassword(self):
        return self.getString()

    def getString(self):
        while len(self.pool) == 0:
            input = popen("/usr/bin/apg -m 5 -x 10 -M ncl -q -n 500")
            self.pool = filter(lambda string: checkName(string)[0], map(lambda string: string[:-1], input.readlines()))
            input.close()
        return self.pool.pop()

class PokerBot:

    def __init__(self, factory):
        self.factory = factory
        self.state = STATE_RUNNING
        self.batch_end_action = None

    def lookForGame(self, protocol):
            join_info = self.factory.join_info
            if join_info['tournament']:
                protocol.sendPacket(PacketPokerTourneySelect(string = join_info["name"]))
            else:
                protocol.sendPacket(PacketPokerTableSelect(string = "play"))
            self.state = STATE_SEARCHING
            self.factory.can_disconnect = True
            
    def _handleConnection(self, protocol, packet):

        if packet.type == PACKET_BOOTSTRAP:
            user = protocol.user
            protocol.sendPacket(PacketLogin(name = user.name,
                                            password = user.password))
            protocol.sendPacket(PacketPokerTableSelect(string = "my"))
            self.state = STATE_RECONNECTING
            
        elif packet.type == PACKET_POKER_BATCH_MODE:
            self.state = STATE_BATCH
            
        elif packet.type == PACKET_POKER_STREAM_MODE:
            self.state = STATE_RUNNING
            if self.batch_end_action:
                self.batch_end_action()
                self.batch_end_action = None
            
        elif packet.type == PACKET_POKER_TABLE_LIST:
            if self.state == STATE_SEARCHING:
                found = False
                table_info = self.factory.join_info
                for table in packet.packets:
                    if table.name == table_info["name"]:
                        found = True
                        protocol.sendPacket(PacketPokerTableJoin(game_id = table.id,
                                                                 serial = protocol.getSerial()))
                        if self.factory.watch == False:
                            protocol.sendPacket(PacketPokerSeat(game_id = table.id,
                                                                serial = protocol.getSerial()))
                            protocol.sendPacket(PacketPokerBuyIn(game_id = table.id,
                                                                 serial = protocol.getSerial()))
                            protocol.sendPacket(PacketPokerAutoBlindAnte(game_id = table.id,
                                                                         serial = protocol.getSerial()))
                            protocol.sendPacket(PacketPokerSit(game_id = table.id,
                                                               serial = protocol.getSerial()))
                        break

                if not found:
                    print "Unable to find table %s " % table_info["name"]
                    protocol.transport.loseConnection()

            elif self.state == STATE_RECONNECTING:
                tables = packet.packets
                if len(tables) == 0:
                    self.lookForGame(protocol)
                elif len(tables) == 1:
                    table = tables[0]
                    protocol.sendPacket(PacketPokerTableJoin(game_id = table.id,
                                                             serial = protocol.getSerial()))
                    protocol.sendPacket(PacketPokerSit(game_id = table.id,
                                                       serial = protocol.getSerial()))
                    self.state = STATE_RUNNING
                else:
                    print "Unexpected number of tables %d " % len(tables)
                    protocol.transport.loseConnection()

            else:
                print "Unexpected state %d" % self.state
                protocol.transport.loseConnection()

        elif packet.type == PACKET_POKER_TOURNEY_LIST:
            name = self.factory.join_info['name']
            if len(packet.packets) <= 0:
                print "Unable to find tournament %s " % name
            found = None
            for tourney in packet.packets:
                if tourney.state == TOURNAMENT_STATE_REGISTERING:
                    found = tourney.serial
                    break
            if not found:
                print "No %s tournament allows registration, try later " % name
                self.factory.can_disconnect = False
                reactor.callLater(10, lambda: self.lookForGame(protocol))
            else:
                protocol.sendPacket(PacketPokerTourneyRegister(serial = protocol.getSerial(),
                                                               game_id = found))
            self.state = STATE_RUNNING
            
        elif packet.type == PACKET_POKER_SEAT:
            if packet.seat == -1:
                print "Not allowed to get a seat, give up"
                protocol.transport.loseConnection()

        elif packet.type == PACKET_POKER_ERROR or packet.type == PACKET_ERROR:
            giveup = True
            if packet.other_type == PACKET_POKER_TOURNEY_REGISTER:
                if packet.code == PacketPokerTourneyRegister.NOT_ENOUGH_MONEY:
                    self.factory.went_broke = True
                elif packet.code == PacketPokerTourneyRegister.ALREADY_REGISTERED:
                    giveup = False
                else:
                    name = self.factory.join_info['name']
                    print "Registration refused for tournament %s, try later" % name
                    self.factory.can_disconnect = False
                    reactor.callLater(60, lambda: self.lookForGame(protocol))
                    giveup = False
            elif packet.other_type == PACKET_POKER_REBUY or packet.other_type == PACKET_POKER_BUY_IN:
                self.factory.went_broke = True

            if self.factory.verbose or giveup: print "ERROR: %s" % packet
            if giveup:
                protocol.transport.loseConnection()
            
        elif packet.type == PACKET_POKER_BLIND_REQUEST:
            if packet.serial == protocol.getSerial():
                protocol.sendPacket(PacketPokerBlind(game_id = packet.game_id,
                                                     serial = packet.serial))

        elif packet.type == PACKET_POKER_PLAYER_LEAVE:
            if packet.serial == protocol.getSerial():
                if self.factory.join_info['tournament']:
                    self.lookForGame(protocol)

        elif packet.type == PACKET_POKER_WIN:
            if self.state == STATE_RUNNING:
                #
                # Rebuy if necessary
                #
                if not self.factory.join_info['tournament'] and self.factory.watch == False:
                    game = self.factory.packet2game(packet)
                    serial = protocol.getSerial()
                    if ( game and game.isBroke(serial) ):
                        protocol.sendPacket(PacketPokerRebuy(game_id = game.id,
                                                             serial = serial))
                        protocol.sendPacket(PacketPokerSit(game_id = game.id,
                                                           serial = serial))
            
        elif packet.type == PACKET_POKER_SELF_IN_POSITION:
            game = self.factory.packet2game(packet)
            if self.state == STATE_RUNNING:
                self.inPosition(protocol, game)
            elif self.state == STATE_BATCH:
                self.batch_end_action = lambda: self.inPosition(protocol, game)

        elif packet.type == PACKET_POKER_SELF_LOST_POSITION:
            if self.state == STATE_BATCH:
                self.batch_end_action = None
                
    def inPosition(self, protocol, game):
        if not game.isBlindAnteRound():
            if self.factory.wait > 0:
                self.factory.can_disconnect = False
                reactor.callLater(self.factory.wait, lambda: self.play(protocol, game))
            else:
                self.play(protocol, game)

    def eval(self, game, serial):
        if self.factory.level == 0:
            actions = ("check", "call", "raise", "fold")
            return actions[randint(0, 3)]

        ev = game.handEV(serial, LEVEL2ITERATIONS[self.factory.level])
        
        if game.state == "pre-flop":
            if ev < 100:
                action = "check"
            elif ev < 500:
                action = "call"
            else:
                action = "raise"
        elif game.state == "flop" or game.state == "third":
            if ev < 200:
                action = "check"
            elif ev < 600:
                action = "call"
            else:
                action = "raise"
        elif game.state == "turn" or game.state == "fourth":
            if ev < 300:
                action = "check"
            elif ev < 700:
                action = "call"
            else:
                action = "raise"
        else:
            if ev < 400:
                action = "check"
            elif ev < 800:
                action = "call"
            else:
                action = "raise"
            
        return (action, ev)
        
    def play(self, protocol, game):
        serial = protocol.getSerial()
        name = protocol.getName()
        if serial not in game.serialsNotFold():
            print name + ": the server must have decided to play on our behalf before we had a chance to decide (TIMEOUT happening at the exact same time we reconnected), most likely"
            return
        
        (desired_action, ev) = self.eval(game, serial)
        actions = game.possibleActions(serial)
        if self.factory.verbose:
            print "%s serial = %d, hand = %s, board = %s" % (name, serial, game.getHandAsString(serial), game.getBoardAsString())
            print "%s wants to %s (ev = %d)" % (name, desired_action, ev)
        while not desired_action in actions:
            if desired_action == "check":
                desired_action = "fold"
            elif desired_action == "call":
                desired_action = "check"
            elif desired_action == "raise":
                desired_action = "call"

        if desired_action == "fold":
            protocol.sendPacket(PacketPokerFold(game_id = game.id,
                                                serial = serial))
        elif desired_action == "check":
            protocol.sendPacket(PacketPokerCheck(game_id = game.id,
                                                 serial = serial))
        elif desired_action == "call":
            protocol.sendPacket(PacketPokerCall(game_id = game.id,
                                                serial = serial))
        elif desired_action == "raise":
            minimum = PokerChips(game.chips_values)
            protocol.sendPacket(PacketPokerRaise(game_id = game.id,
                                                 serial = serial,
                                                 amount = minimum.chips))
        else:
            print "=> unexpected actions = %s" % actions
        self.factory.can_disconnect = True

class PokerBotProtocol(PokerClientProtocol):

    def protocolEstablished(self):
        PokerClientProtocol.protocolEstablished(self)
        self._prefix = self.user.name + " "
        if self.factory.disconnect_delay:
            delay = randint(*self.factory.disconnect_delay)
            print self.user.name + ": will disconnect in %d seconds (for kicks)" % delay
            reactor.callLater(delay, lambda: self.disconnectMyself(self.user.name))

    def disconnectMyself(self, name):
        if name == self.user.name:
            if self.factory.can_disconnect:
                self.factory.disconnected_volontarily = True
                print self.user.name + ": disconnecting (for kicks)"
                self.transport.loseConnection()
            else:
                delay = randint(*self.factory.disconnect_delay)
                print self.user.name + ": scheduled disconnection not allowed, will try again in %d seconds (for kicks)" % delay
                reactor.callLater(delay, lambda: self.disconnectMyself(self.user.name))
        
class PokerBotFactory(PokerClientFactory):

    string_generator = None

    def __init__(self, *args, **kwargs):
        PokerClientFactory.__init__(self, *args, **kwargs)
        self.protocol = PokerBotProtocol
        self.join_info = kwargs["join_info"]
        settings = kwargs["settings"]
        self.level = settings.headerGetInt("/settings/@level")
        self.reconnect = settings.headerGet("/settings/@reconnect") == "yes"
        self.watch = settings.headerGet("/settings/@watch") == "yes"
        self.wait = settings.headerGetInt("/settings/@wait")
        self.disconnect_delay = settings.headerGet("/settings/@disconnect_delay")
        if self.disconnect_delay:
            self.disconnect_delay = tuple(map(lambda x: int(x), split(self.disconnect_delay, ",")))
        self.reconnect_delay = settings.headerGet("/settings/@reconnect_delay")
        if self.reconnect_delay:
            self.reconnect_delay = tuple(map(lambda x: int(x), split(self.reconnect_delay, ",")))
        self.verbose = settings.headerGetInt("/settings/@verbose")
        self.bot = None
        self.went_broke = False
        self.disconnected_volontarily = False
        self.can_disconnect = True
        self.name = PokerBotFactory.string_generator.getName()
        self.password = PokerBotFactory.string_generator.getPassword()
        
    def buildProtocol(self, addr):
        protocol = PokerClientFactory.buildProtocol(self, addr)
        pokerbot = PokerBot(self)
        protocol._poll = False
        protocol.registerHandler(True, PACKET_BOOTSTRAP, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_ERROR, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_BATCH_MODE, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_STREAM_MODE, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_ERROR, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_TABLE_LIST, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_TOURNEY_LIST, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_WIN, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_PLAYER_LEAVE, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_SEAT, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_BLIND_REQUEST, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_SELF_IN_POSITION, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_POKER_SELF_LOST_POSITION, pokerbot._handleConnection)
        return protocol

    def clientConnectionFailed(self, connector, reason):
        print "Failed to establish connection to table %s" % self.join_info["name"]
        print reason
        self.bot.parent.removeService(self.bot)
        
    def clientConnectionLost(self, connector, reason):
        reconnect = False
        if self.reconnect:
            if self.went_broke:
                self.name = PokerBotFactory.string_generator.getName()
                print "Re-establishing (get more money)."
                self.went_broke = False
                reactor.callLater(self.wait, connector.connect)
            elif self.disconnected_volontarily:
                delay = randint(*self.reconnect_delay)
                print self.name + " Re-establishing in %d seconds." % delay
                self.disconnected_volontarily = False
                reactor.callLater(delay, connector.connect)
                reconnect = True
        else:
            print "The poker3d server connection to %s was closed" % self.join_info["name"]
            if not reason.check(error.ConnectionDone):
                print reason
        if not reconnect:
            self.bot.parent.removeService(self.bot)

class Bots(service.MultiService):

    def setSettings(self, settings):
        self.count = 0
        self.settings = settings
        self.verbose = settings.headerGetInt("/settings/@verbose")

    def addService(self, _service):
        service.MultiService.addService(self, _service)
        self.check()

    def removeService(self, _service):
        service.MultiService.removeService(self, _service)
        self.check()

    def check(self):
        if self.verbose > 1:
            print "%d bots currently active" % len(self.services)
        if len(self.services) <= 0:
            reactor.callLater(0, reactor.stop)

def Application(name, uid=None, gid=None):
    """Return a compound class.

    Return an object supporting the C{IService}, C{IServiceCollection},
    C{IProcess} and C{sob.IPersistable} interfaces, with the given
    parameters. Always access the return value by explicit casting to
    one of the interfaces.
    """
    ret = components.Componentized()
    for comp in (Bots(), sob.Persistent(ret, name), service.Process(uid, gid)):
        ret.addComponent(comp, ignoreClass=1)
    service.IService(ret).setName(name)
    return ret

class Bot(internet.TCPClient):

    def stopService(self):
        #
        # If the connection is still available (i.e. the bots
        # were stopped because of a SIGINT signal), properly
        # close it before exiting.
        #
        if(hasattr(self._connection.transport, "protocol")):
            protocol = self._connection.transport.protocol
            #
            # If the connection fails, the transport exists but
            # the protocol is not set
            #
            if protocol:
                self._connection.transport.protocol.sendPacket(PacketQuit())
        return internet.TCPClient.stopService(self)

def run(argv):
    configuration = sys.argv[-1][-4:] == ".xml" and sys.argv[-1] or "/etc/poker-network/poker.bot.xml"

    settings = Config([''])
    settings.load(configuration)

    PokerBotFactory.string_generator = StringGenerator(settings.headerGet("/settings/@name_prefix"))

    ( host, port ) = split(settings.headerGet("/settings/servers"), ":")
    port = int(port)

    bots = Application('pokerbot')
    bots.verbose = settings.headerGetInt("/settings/@verbose")
    services = service.IServiceCollection(bots)
    services.setSettings(settings)
    
    for table in settings.headerGetProperties("/settings/table"):
        for i in range(0, int(table["count"])):
            table['tournament'] = False
            factory = PokerBotFactory(settings = settings,
                                      join_info = table)
            bot = Bot(host, port, factory)
            factory.bot = bot
            bot.setServiceParent(services)
    for tournament in settings.headerGetProperties("/settings/tournament"):
        for i in range(0, int(tournament["count"])):
            tournament['tournament'] = True
            factory = PokerBotFactory(settings = settings,
                                      join_info = tournament)
            bot = Bot(host, port, factory)
            factory.bot = bot
            bot.setServiceParent(services)
    return bots

application = run(sys.argv[1:])

if __name__ == '__main__':
    try:
        app.startApplication(application, None)
        reactor.run()
    except:
        if application.verbose:
            print_exc()
        else:
            print sys.exc_value
