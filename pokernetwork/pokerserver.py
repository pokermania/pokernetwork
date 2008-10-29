#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
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

import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")

import platform
from os.path import exists
from types import *

from OpenSSL import SSL

try:
        from OpenSSL import SSL
        HAS_OPENSSL=True
except:
        print "openSSL not available."
        HAS_OPENSSL=False
        

from twisted.application import internet, service, app
from twisted.web import resource,server

from pokernetwork.pokernetworkconfig import Config
from pokernetwork.pokerservice import PokerTree, PokerRestTree, PokerService, IPokerFactory, SSLContextFactory
from pokernetwork.pokersite import PokerSite

def makeService(configuration):
    settings = Config([''])
    settings.load(configuration)
    if not settings.header:
        sys.exit(1)

    serviceCollection = service.MultiService()
    poker_service = PokerService(settings)
    poker_service.setServiceParent(serviceCollection)

    poker_factory = IPokerFactory(poker_service)

    #
    # Poker protocol (with or without SSL)
    #
    tcp_port = settings.headerGetInt("/server/listen/@tcp")
    internet.TCPServer(tcp_port, poker_factory
                       ).setServiceParent(serviceCollection)    

    tcp_ssl_port = settings.headerGetInt("/server/listen/@tcp_ssl")
    if HAS_OPENSSL and tcp_ssl_port:
            internet.SSLServer(tcp_ssl_port, poker_factory, SSLContextFactory(settings)
                           ).setServiceParent(serviceCollection)

    rest_site = PokerSite(settings, PokerRestTree(poker_service))

    #
    # HTTP (with or without SLL) that implements REST
    #
    rest_port = settings.headerGetInt("/server/listen/@rest")
    if rest_port:
            internet.TCPServer(rest_port, rest_site
                               ).setServiceParent(serviceCollection)

    rest_ssl_port = settings.headerGetInt("/server/listen/@rest_ssl")
    if HAS_OPENSSL and rest_ssl_port:
            internet.SSLServer(rest_ssl_port, rest_site, SSLContextFactory(settings)
                               ).setServiceParent(serviceCollection)

    http_site = server.Site(PokerTree(poker_service))

    #
    # HTTP (with or without SLL) that implements XML-RPC and SOAP
    #
    http_port = settings.headerGetInt("/server/listen/@http")
    if http_port:
            internet.TCPServer(http_port, http_site
                               ).setServiceParent(serviceCollection)

    http_ssl_port = settings.headerGetInt("/server/listen/@http_ssl")
    if HAS_OPENSSL and http_ssl_port:
            internet.SSLServer(http_ssl_port, http_site, SSLContextFactory(settings)
                               ).setServiceParent(serviceCollection)
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

def run():
    if platform.system() != "Windows":
        if not sys.modules.has_key('twisted.internet.reactor'):
                print "installing poll reactor"
                pollreactor.install()
        else:
                print "poll reactor already installed"
    from twisted.internet import reactor
    application = makeApplication(sys.argv)
    app.startApplication(application, None)
    from twisted.internet import pollreactor
    reactor.run()

if __name__ == '__main__':
    run()
