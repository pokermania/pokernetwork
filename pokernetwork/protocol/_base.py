
from twisted.internet.protocol import Protocol
from twisted.internet.error import ConnectionDone
from twisted.internet.task import LoopingCall
from twisted.internet import defer

from pokerpackets.packets import PacketPing

class BaseProtocol(Protocol):

    def __init__(self):

        self.established = False
        self.d_established = defer.Deferred()
        self.d_connection_lost = defer.Deferred()

        self.__lc_keepalive = LoopingCall(self._keepalive)
        self.__keepalive_interval = 10

    def connectionMade(self):
        self._keepalive_start()
        self.established = True
        self.d_established.callback(self)

    def connectionLost(self, reason):
        if not reason.check(ConnectionDone):
            self.log.inform("connection was closed uncleanly. failure: %s", reason.getErrorMessage())
        self._keepalive_stop()
        self.established = False
        d, self.d_connection_lost = self.d_connection_lost, defer.Deferred()
        d.callback(self)

    def keepalive_set_interval(self, interval):
        self.__keepalive_interval = interval
        if self.__lc_keepalive.running:
            self._keepalive_start()

    def _keepalive_start(self):
        self._keepalive_reset()

    def _keepalive_stop(self):
        if self.__lc_keepalive.running:
            self.__lc_keepalive.stop()

    def _keepalive_reset(self):
        if self.__lc_keepalive.running:
            self.__lc_keepalive.stop()
            self.__lc_keepalive.start(self.__keepalive_interval, False)

    def _keepalive(self):
        self.sendPacket(PacketPing(), False)

    def packetReceived(self, packet):
        raise NotImplementedError('packetReceived has to be implemented by sub protocol (eg. client or server)')
