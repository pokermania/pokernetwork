#
# Copyright (C) 2010 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
#       
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
#  Johan Euphrosine <proppy@aminche.com>
#  Loic Dachary <loic@dachary.org>
#  Henry Precheur <henry@precheur.org> (2004)
#

from pokernetwork import log as network_log
log = network_log.get_child('pokerbot')


import sys
import os
sys.path.insert(0, "..")

import platform
from os.path import exists
from random import randint

from twisted.application import internet, service, app

from twisted.python import log as twisted_log
import reflogging
from reflogging.handlers import GELFHandler, StreamHandler, ColorStreamHandler, SyslogHandler
from reflogging._twisted import RefloggingObserver

from sys import stdout as orig_stdout, stderr as orig_stderr

if platform.system() != "Windows":
    if 'twisted.internet.reactor' not in sys.modules:
        from twisted.internet import epollreactor
        log.debug("installing epoll reactor")
        epollreactor.install()
    else:
        log.debug("reactor already installed")

from twisted.internet import reactor
from twisted.python import components
from twisted.persisted import sob
from twisted.internet import error

from pokerengine.pokertournament import *
from pokernetwork import pokernetworkconfig
from pokerpackets.clientpackets import *
from pokernetwork.pokerclient import PokerClientFactory, PokerClientProtocol
from pokernetwork.pokerbotlogic import StringGenerator, NoteGenerator, PokerBot

class PokerBotProtocol(PokerClientProtocol):

    def protocolEstablished(self):
        PokerClientProtocol.protocolEstablished(self)
        self.setPrefix(self.user.name + " ")
        if self.factory.disconnect_delay:
            delay = randint(*self.factory.disconnect_delay)
            self.log.debug("%s: will disconnect in %d seconds (for kicks)", self.user.name, delay)
            reactor.callLater(delay, self.disconnectMyself, self.user.name)

    def disconnectMyself(self, name):
        if name == self.user.name:
            if self.factory.can_disconnect:
                self.factory.disconnected_volontarily = True
                self.log.debug("%s: disconnect (for kicks)", self.user.name)
                self.transport.loseConnection()
            else:
                delay = randint(*self.factory.disconnect_delay)
                self.log.debug("%s: scheduled disconnect not allowed, will try again in %d seconds (for kicks)", self.user.name, delay)
                reactor.callLater(delay, self.disconnectMyself, self.user.name)
        
class PokerBotFactory(PokerClientFactory):

    string_generator = None

    log = log.get_child('PokerBotFactory')

    def __init__(self, *args, **kwargs):
        self.log = PokerBotFactory.log.get_instance(self, refs=[
            ("User", self, lambda factory: factory.serial if factory.serial else None)
        ])
        self.serial = kwargs["serial"]
        PokerClientFactory.__init__(self, *args, **kwargs)
        self.protocol = PokerBotProtocol
        self.join_info = kwargs["join_info"]
        settings = kwargs["settings"]
        self.level = settings.headerGetInt("/settings/@level")
        self.reconnect = settings.headerGet("/settings/@reconnect") == "yes"
        self.rebuy = settings.headerGet("/settings/@rebuy") == "yes"
        self.watch = settings.headerGet("/settings/@watch") == "yes"
        self.cash_in = settings.headerGet("/settings/@cash_in") != "no"
        self.wait = settings.headerGetInt("/settings/@wait")
        self.disconnect_delay = settings.headerGet("/settings/@disconnect_delay")
        if self.disconnect_delay:
            self.disconnect_delay = tuple(map(int, self.disconnect_delay.split(',')))
        self.reconnect_delay = settings.headerGet("/settings/@reconnect_delay")
        if self.reconnect_delay:
            self.reconnect_delay = tuple(map(int, self.reconnect_delay.split(',')))
        self.currency = settings.headerGetInt("/settings/currency")
        self.currency_id = settings.headerGet("/settings/currency/@id")
        self.bot = None
        self.went_broke = False
        self.disconnected_volontarily = False
        self.can_disconnect = True
        self.kwargs = kwargs
        self.name =  kwargs.get('name', PokerBotFactory.string_generator.getName())
        self.password = kwargs.get('password', PokerBotFactory.string_generator.getPassword())
        
    def buildProtocol(self, addr):
        protocol = PokerClientFactory.buildProtocol(self, addr)
        pokerbot = PokerBot(self)
        protocol._poll = False
        protocol.registerHandler(True, PACKET_BOOTSTRAP, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_AUTH_OK, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_AUTH_REFUSED, pokerbot._handleConnection)
        protocol.registerHandler(True, PACKET_ERROR, pokerbot._handleConnection)
        protocol.registerHandler('outbound', PACKET_SERIAL, pokerbot._handleConnection)
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
        self.log.warn("Failed to establish connection to table %s, reason: %s", self.join_info['name'], reason)
        self.bot.parent.removeService(self.bot)
        
    def clientConnectionLost(self, connector, reason):
        if self.reconnect:
            delay = randint(*self.reconnect_delay)
            if self.went_broke:
                if 'name' not in self.kwargs:
                    self.name = PokerBotFactory.string_generator.getName()
                self.log.debug("%s Re-establishing in %d seconds (get more money).", self.name, delay)
                self.went_broke = False
            elif self.disconnected_volontarily:
                self.log.debug("%s Re-establishing in %d seconds (volontarily).", self.name, delay)
                self.disconnected_volontarily = False
            else:
                self.log.inform("%s Re-establishing in %d seconds (other).", self.name, delay)
            reactor.callLater(delay, connector.connect)
        else:
            self.log.debug("The bot server connection to %s was closed, reason: %s",
                self.join_info['name'],
                reason if not reason.check(error.ConnectionDone) else None
            )
            self.bot.parent.removeService(self.bot)

class Bots(service.MultiService):

    log = log.get_child('Bots')
    
    def __init__(self, *a, **kw):
        service.MultiService.__init__(self, *a, **kw)

    def setSettings(self, settings):
        self.count = 0
        self.settings = settings

    def addService(self, _service):
        service.MultiService.addService(self, _service)
        self.check()

    def removeService(self, _service):
        service.MultiService.removeService(self, _service)
        self.check()

    def check(self):
        self.log.debug("%d bots currently active", len(self.services))
        if len(self.services) <= 0 and reactor.running:
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

def makeApplication(argv):
    default_path = "/etc/poker-network" + sys.version[:3] + "/poker.bot.xml"
    if not exists(default_path):
        default_path = "/etc/poker-network/poker.bot.xml"
    configuration = argv[-1][-4:] == ".xml" and argv[-1] or default_path

    application = service.Application('pokerbot')
    serviceCollection = service.IServiceCollection(application)
    bots_service = makeService(configuration)
    bots_service.setServiceParent(serviceCollection)
    return application

def makeService(configuration):
    settings = pokernetworkconfig.Config([''])
    settings.load(configuration)

    # Setup Logging
    root_logger = reflogging.RootLogger()
    root_logger.set_app_name('bot')
    
    log_level = settings.headerGetInt('/settings/logging/@log_level') or 30
    if 'LOG_LEVEL' in os.environ:
        log_level = int(os.environ['LOG_LEVEL'])
    if log_level not in (10, 20, 30, 40, 50):
        raise ValueError(
            "Unsupported log level %d. Supported log levels "
            "are DEBUG(10), INFO(20), WARNING(30), ERROR(40), CRITICAL(50)." % (log_level,)
        )
        
    root_logger.set_level(log_level)
    for node in settings.header.xpathEval('/settings/logging/*'):
        _name = node.name
        _log_level_node = node.xpathEval('@log_level')
        _log_level = int(_log_level_node[0].content) if _log_level_node else 30
        if _name in ('stream', 'colorstream'):
            _output_node = node.xpathEval('@output')
            _output = _output_node[0].content if _output_node else 'stdout'
            if _output in ('stdout', '-'):
                _output = orig_stdout
            elif _output == 'stderr':
                _output = orig_stderr
            else:
                if _output.startswith('-'):
                    _output = open(_output[1:], 'w')
                else:
                    _output = open(_output, 'a')
            if _name == 'stream':
                _handler = StreamHandler(_output)
            elif _name == 'colorstream':
                _handler = ColorStreamHandler(_output)
        if _name == 'gelf':
            _host_node = node.xpathEval('@host')
            _port_node = node.xpathEval('@port')
            _host = _host_node[0].content if _host_node else 'localhost'
            _port = _port_node[0].content if _port_node else 12201
            _handler = GELFHandler(_host, _port)
        if _name == 'syslog':
            _handler = SyslogHandler('pokernetwork', 0)
        _handler.set_level(_log_level)
        root_logger.add_handler(_handler)
    
    PokerBotFactory.string_generator = StringGenerator(settings.headerGet("/settings/@name_prefix"))
    PokerBot.note_generator = NoteGenerator(settings.headerGet("/settings/currency"))

    host, port = settings.headerGet("/settings/servers").split(':')
    port = int(port)

    services = Bots()
    services.setSettings(settings)

    def bot_serial_generator():
        serial = 0
        while True:
            serial += 1
            yield serial

    def create_bot(*args, **kwargs):
        factory = PokerBotFactory(*args, **kwargs)
        bot = Bot(host, port, factory)
        factory.bot = bot
        bot.setServiceParent(services)

    bot_serial = bot_serial_generator()

    for table in settings.headerGetProperties("/settings/table"):
        table['tournament'] = False
        if 'count' in table:
            for _i in xrange(0, int(table["count"])):
                create_bot(settings=settings, join_info=table, serial=bot_serial.next())
        else:
            table_attributes = ["@name=\"%s\"" % table["name"]]
            table_attributes.append("@skin=\"%s\"" % table["skin"] if "skin" in table else "not(@skin)")
            for bot in settings.headerGetProperties("/settings/table[%s]/bot" % " and ".join(table_attributes)):
                create_bot(settings=settings, join_info=table, serial=bot_serial.next(), name=bot['name'], password=bot['password'])
    for tournament in settings.headerGetProperties("/settings/tournament"):
        tournament['tournament'] = True
        if 'count' in tournament:
            for _i in xrange(0, int(tournament["count"])):
                create_bot(settings=settings, join_info=tournament, serial=bot_serial.next())
        else:
            tournament_attributes = ["@name=\"%s\"" % tournament["name"]]
            tournament_attributes.append("@skin=\"%s\"" % tournament["skin"] if "skin" in tournament else "not(@skin)")
            for bot in settings.headerGetProperties("/settings/tournament[%s]/bot" % " and ".join(tournament_attributes)):
                create_bot(settings=settings, join_info=tournament, serial=bot_serial.next(), name=bot['name'], password=bot['password'])
    return services

def run():
    twisted_log.startLoggingWithObserver(RefloggingObserver())
    application = makeApplication(sys.argv[1:])
    app.startApplication(application, None)
    reactor.run()

if __name__ == '__main__':
    run()
