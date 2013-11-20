#
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2006, 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
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
#  Henry Precheur <henry@precheur.org> (2004)
#

from pokernetwork import log as network_log
log = network_log.get_child('pokerserver')

import sys, os
sys.path.insert(0, ".")
sys.path.insert(0, "..")

import platform
from os.path import exists

try:
    from OpenSSL import SSL ; del SSL # just imported to check for SSL
    from pokernetwork.pokerservice import SSLContextFactory
    HAS_OPENSSL=True
except ImportError:
    log.inform("OpenSSL not available.")
    HAS_OPENSSL=False

from twisted.application import internet, service, app
from twisted.python import log as twisted_log

from pokernetwork.pokernetworkconfig import Config
from pokernetwork.pokerservice import PokerRestTree, PokerService, IPokerFactory
from pokernetwork.pokerpub import PubService
from pokernetwork.protocol import ServerMsgpackProtocol
from pokernetwork.pokersite import PokerSite
from pokernetwork.pokermanhole import makeService as makeManholeService

import reflogging
from reflogging.handlers import GELFHandler, StreamHandler, ColorStreamHandler, SyslogHandler
from reflogging._twisted import RefloggingObserver

from sys import stdout as orig_stdout, stderr as orig_stderr

def makeService(configuration):
    settings = Config([''])
    settings.load(configuration)
    if not settings.header:
        sys.exit(1)

    #
    # Setup Logging
    #
    root_logger = reflogging.RootLogger()
    root_logger.set_app_name('network')
    # acquire root log_level
    log_level = settings.headerGetInt('/server/logging/@log_level') or 30
    if 'LOG_LEVEL' in os.environ:
        log_level = int(os.environ['LOG_LEVEL'])
    if log_level not in (10, 20, 30, 40, 50):
        raise ValueError(
            "Unsupported log level %d. Supported log levels "
            "are DEBUG(10), INFO(20), WARNING(30), ERROR(40), CRITICAL(50)." % (log_level,)
        )
    root_logger.set_level(log_level)
    for node in settings.header.xpathEval('/server/logging/*'):
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

    serviceCollection = service.MultiService()
    poker_service = PokerService(settings)
    poker_service.setServiceParent(serviceCollection)


    #
    # Poker protocol (with or without SSL)
    #
    poker_factory = IPokerFactory(poker_service)
    tcp_port = settings.headerGetInt("/server/listen/@tcp")
    internet.TCPServer(tcp_port, poker_factory).setServiceParent(serviceCollection)

    tcp_ssl_port = settings.headerGetInt("/server/listen/@tcp_ssl")
    if HAS_OPENSSL and tcp_ssl_port:
        internet.SSLServer(tcp_ssl_port, poker_factory, SSLContextFactory(settings)).setServiceParent(serviceCollection)

    #
    # msgpack protocol
    #
    msgpack_port = settings.headerGetInt("/server/listen/@msgpack")
    if msgpack_port:
        msgpack_factory = IPokerFactory(poker_service)
        msgpack_factory.setProtocol(ServerMsgpackProtocol)
        internet.TCPServer(msgpack_port, msgpack_factory).setServiceParent(serviceCollection)

    #
    # HTTP (with or without SLL) that implements REST
    #
    rest_site = PokerSite(settings, PokerRestTree(poker_service))
    rest_port = settings.headerGetInt("/server/listen/@rest")
    if rest_port:
        internet.TCPServer(rest_port, rest_site).setServiceParent(serviceCollection)

    rest_ssl_port = settings.headerGetInt("/server/listen/@rest_ssl")
    if HAS_OPENSSL and rest_ssl_port:
        internet.SSLServer(rest_ssl_port, rest_site, SSLContextFactory(settings)).setServiceParent(serviceCollection)

    #
    # SSh twisted.conch.manhole
    #
    manhole_port = settings.headerGetInt("/server/listen/@manhole")
    if manhole_port:
        manhole_service = makeManholeService(manhole_port, {
            'poker_service': poker_service,
            'poker_site': rest_site
        })
        manhole_service.name = 'manhole'
        manhole_service.setServiceParent(serviceCollection)

    #
    # Pub/Sub
    #
    pub_port = settings.headerGetInt("/server/listen/@pub")
    if pub_port:
        pub_service = internet.TCPServer(pub_port, PubService(poker_service))
        pub_service.name = 'pub'
        pub_service.setServiceParent(serviceCollection)

    return serviceCollection

def makeApplication(argv):
    default_path = "/etc/poker-network" + sys.version[:3] + "/poker.server.xml"
    if not exists(default_path):
        default_path = "/etc/poker-network/poker.server.xml"
    configuration = argv[-1][-4:] == ".xml" and argv[-1] or default_path    
    application = service.Application('poker')
    serviceCollection = service.IServiceCollection(application)
    poker_service = makeService(configuration)
    poker_service.setServiceParent(serviceCollection)
    return application

def run(argv):
    twisted_log.startLoggingWithObserver(RefloggingObserver())

    if platform.system() != "Windows":
        if 'twisted.internet.reactor' not in sys.modules:
            log.debug("installing epoll reactor")
            from twisted.internet import epollreactor
            epollreactor.install()
        else:
            log.debug("reactor already installed")
    from twisted.internet import reactor
    application = makeApplication(argv)
    app.startApplication(application, None)
    reactor.run()

if __name__ == '__main__':
    run(sys.argv)
    
