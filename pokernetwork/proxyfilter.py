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

from twisted.internet import defer, protocol, reactor, error
from twisted.web import http

from pokernetwork.pokerpackets import PacketPokerTableJoin

local_reactor = reactor

class ProxyClient(http.HTTPClient):
    """
    Used by ProxyClientFactory to implement a simple web proxy.
    """

    def __init__(self, command, rest, version, headers, data, father):
        self.father = father
        self.command = command
        self.rest = rest
        if "proxy-connection" in headers:
            del headers["proxy-connection"]
        headers["connection"] = "close"
        self.headers = headers
        self.data = data


    def connectionMade(self):
        self.sendCommand(self.command, self.rest)
        for header, value in self.headers.items():
            self.sendHeader(header, value)
        self.endHeaders()
        self.transport.write(self.data)


    def handleStatus(self, version, code, message):
        if message:
            # Add a whitespace to message, this allows empty messages
            # transparently
            message = " %s" % (message,)
        self.father.transport.write("%s %s%s\r\n" % (version, code, message))


    def handleHeader(self, key, value):
        self.father.transport.write("%s: %s\r\n" % (key, value))


    def handleEndHeaders(self):
        self.father.transport.write("\r\n")


    def handleResponsePart(self, buffer):
        self.father.transport.write(buffer)


    def handleResponseEnd(self):
        self.transport.loseConnection()
        self.father.channel.transport.loseConnection()



class ProxyClientFactory(protocol.ClientFactory):

    protocol = ProxyClient

    def __init__(self, command, rest, version, headers, data, father):
        self.father = father
        self.command = command
        self.rest = rest
        self.headers = headers
        self.data = data
        self.version = version
        self.deferred = defer.Deferred()


    def buildProtocol(self, addr):
        return self.protocol(self.command, self.rest, self.version,
                             self.headers, self.data, self.father)


    def clientConnectionFailed(self, connector, reason):
        if not self.deferred.called:
            self.deferred.errback(reason)

    def clientConnectionLost(self, connector, reason):
        if not reason.check(error.ConnectionDone):
            if not self.deferred.called:
                self.deferred.callback(reason)
        
#
# return a value if all actions were complete
#
def rest_filter(site, request, packet):
    service = site.resource.service
    resthost = service.packet2resthost(packet)
    if resthost:
        ( host, port, path ) = resthost
        request.content.seek(0, 0)
        clientFactory = ProxyClientFactory(
            request.method, path, request.clientproto,
            request.getAllHeaders(), request.content.read(), request)
        local_reactor.connectTCP(host, int(port), clientFactory)
        return clientFactory.deferred
    return True
