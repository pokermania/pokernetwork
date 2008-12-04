#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2008 Loic Dachary <loic@dachary.org>
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
from twisted.internet import error, defer

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
        self.stop_service_deferred = kwargs.has_key('stop_service_deferred') and kwargs['stop_service_deferred'] or None
        self.pokerstats = PokerStats(self)
        
    def buildProtocol(self, addr):
        protocol = PokerClientFactory.buildProtocol(self, addr)
        protocol._poll = False
        pokerstats = self.pokerstats
        pokerstats.connect()
        protocol.registerHandler(True, PACKET_POKER_MONITOR_EVENT, pokerstats.pokerMonitorEvent)
        protocol.registerHandler(True, PACKET_BOOTSTRAP, pokerstats.bootstrap)
        def ack_and_stop(protocol, packet):
            pokerstats.ack(protocol, packet)
            if self.stop_service_deferred:
                self.stop_service_deferred.callback(True)
        protocol.registerHandler(True, PACKET_ACK, ack_and_stop)
        return protocol

class Stat(internet.TCPClient):

    def stopService(self):
        #
        # If the connection is still available (i.e. the stats
        # were stopped because of a SIGINT signal), properly
        # close it before exiting.
        #
        if self._connection:
            if(hasattr(self._connection.transport, "protocol")):
                protocol = self._connection.transport.protocol
                #
                # If the connection fails, the transport exists but
                # the protocol is not set
                #
                if protocol:
                    self._connection.transport.protocol.sendPacket(PacketQuit())
        return internet.TCPClient.stopService(self)

def newApplication(settings, one_time = False):
    stats = service.Application('pokerstats')
    services = service.IServiceCollection(stats)

    i = 1
    ds = []
    for server in settings.headerGetProperties("/settings/server"):
        host = server['host']
        port = int(server['port'])
        stop_service_deferred = None
        if one_time:
            stop_service_deferred = defer.Deferred()
            ds.append(stop_service_deferred)
        factory = PokerStatsFactory(settings = settings,
                                    server = i,
                                    stop_service_deferred = stop_service_deferred)
        stat = Stat(host, port, factory)
        stat.setServiceParent(services)
        stat.factory = factory
        i += 1
    if one_time and len(ds) > 0:
        global stop_application
        stop_application = defer.DeferredList(ds)
    return stats

def configureApplication(argv):
    default_path = "/etc/poker-network/poker.stats.xml"
    configuration = argv[-1][-4:] == ".xml" and argv[-1] or default_path

    try:
        open(configuration, 'r').close()
    except:
        return None
    
    settings = pokernetworkconfig.Config([''])
    settings.load(configuration)
    one_time = (len(argv) > 1 and argv[1] == '--one-time') and True or False
    return newApplication(settings, one_time)

stop_application = None
application = configureApplication(sys.argv[:])

def run():
    global application, stop_application    #pragma: no cover
    app.startApplication(application, None) #pragma: no cover
    if stop_application: stop_application.addCallback(lambda x: reactor.stop()) #pragma: no cover
    reactor.run()                           #pragma: no cover

if __name__ == '__main__':
    run() #pragma: no cover
