#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2008 Loic Dachary <loic@dachary.org>
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
import sys
sys.path.insert(0, "..")

from os import popen
from os.path import exists

from twisted.application import internet, service, app
from twisted.internet import pollreactor
if not sys.modules.has_key('twisted.internet.reactor'):
    pollreactor.install()                    #pragma: no cover
from twisted.internet import reactor
from twisted.python import components
from twisted.persisted import sob
from twisted.internet import error

from pokernetwork import pokernetworkconfig
from pokernetwork.pokerclientpackets import *
from pokernetwork.pokerclient import PokerClientFactory
from pokernetwork.pokerclientpackets import *
from pokerstats.statslogic import PokerStats

class PokerStatsFactory(PokerClientFactory):

    def __init__(self, *args, **kwargs):
        PokerClientFactory.__init__(self, *args, **kwargs)
        self.server = kwargs['server']
        self.verbose = self.settings.headerGetInt("/settings/@verbose")
        self.pokerstats = PokerStats(self)
        
    def buildProtocol(self, addr):
        protocol = PokerClientFactory.buildProtocol(self, addr)
        protocol._poll = False
        pokerstats = self.pokerstats
        pokerstats.connect()
        protocol.registerHandler(True, PACKET_POKER_MONITOR_EVENT, pokerstats.pokerMonitorEvent)
        protocol.registerHandler(True, PACKET_BOOTSTRAP, pokerstats.bootstrap)
        protocol.registerHandler(True, PACKET_ACK, pokerstats.ack)
        return protocol

class Stat(internet.TCPClient):

    def stopService(self):
        #
        # If the connection is still available (i.e. the stats
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

def newApplication(settings):
    stats = service.Application('pokerstats')
    services = service.IServiceCollection(stats)

    i = 1
    for server in settings.headerGetProperties("/settings/server"):
        host = server['host']
        port = int(server['port'])
        factory = PokerStatsFactory(settings = settings,
                                    server = i)
        Stat(host, port, factory).setServiceParent(services)
        i += 1
    return stats

def configureApplication(argv):
    default_path = "/etc/poker-network/poker.stats.xml"
    configuration = argv[-1][-4:] == ".xml" and argv[-1] or default_path

    if not exists(configuration):
        return None
    
    settings = pokernetworkconfig.Config([''])
    settings.load(configuration)
    return newApplication(settings)

application = configureApplication(sys.argv[:])

def run():
    app.startApplication(application, None) #pragma: no cover
    reactor.run()                           #pragma: no cover

if __name__ == '__main__':
    run() #pragma: no cover
