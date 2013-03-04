
from twisted.internet import protocol, reactor, defer

import struct
from struct import Struct

import simplejson

from pokerpackets import binarypack
from pokerpackets.binarypack import _s_packet_head as s_packet_head
from pokerpackets.packets import PacketPing

from pokernetwork import log as network_log
log = network_log.get_child('protocol')

from pokernetwork import protocol_number
from pokernetwork.version import Version
protocol_version = Version(protocol_number)
protocol_handshake = 'CGI %03d.%d%02d\n' % protocol_version.version
from twisted.internet.error import ConnectionDone

from reflogging import deprecated

class UGAMEProtocol(protocol.Protocol):

    log = log.get_child('UGAMEProtocol')

    def __init__(self):
        self._data = b""
        self.established = False

        self._out_buffer = [] # as long as not established outgoing packets are buffered

        self._cur_packet_length = None # None: not currently on any packet

        self._ignore_incoming = False

        self._keepalive_timer = None
        self._keepalive_delay = 25

        self.d_established = defer.Deferred()
        self.d_connection_lost = defer.Deferred()

    def setPingDelay(self, delay):
        self._keepalive_delay = delay

    def connectionMade(self):
        self._sendVersion()

    def connectionLost(self, reason):
        if not reason.check(ConnectionDone):
            self.log.inform("connection was closed uncleanly. failure: %s", reason.getErrorMessage())
        self.established = False
        self._keepalive_uninit()
        deferred, self.d_connection_lost = self.d_connection_lost, defer.Deferred()
        deferred.callback(self)

    def dataReceived(self, data):
        if self._ignore_incoming:
            return

        self._data += data

        while self._data:
            # handle packet
            if self.established:

                # packet head
                if self._cur_packet_length == None:
                    if len(self._data) >= s_packet_head.size:
                        _type, length = s_packet_head.unpack_from(self._data)
                        self._cur_packet_length = s_packet_head.size + length

                    # not enough data for packet head
                    else: break

                # packet data
                elif len(self._data) >= self._cur_packet_length:
                    self.packetReceived(binarypack.unpack(self._data)[1])
                    self._data = self._data[self._cur_packet_length:]
                    self._cur_packet_length = None

                # not enough data for packet
                else: break

            # handle handshake
            elif len(self._data) >= len(protocol_handshake):
                self._checkVersion(self._data[:len(protocol_handshake)])
                self._data = self._data[len(protocol_handshake):]

            # not enough data for handshake
            else: break

    def dataWrite(self, data):
        self._keepalive_reset()
        self.transport.write(data)

    def _sendVersion(self):
        self.transport.write(protocol_handshake)

    def _checkVersion(self, string):
        if string == protocol_handshake:
            self._protocolEstablished()
        else:
            self._protocolInvalid(protocol_handshake, string)

    def _protocolEstablished(self):
        self.established = True
        self._keepalive_init()
        out_buffer, self._out_buffer = self._out_buffer, []
        self.sendPackets(out_buffer)
        self.protocolEstablished()

    def protocolEstablished(self):
        pass

    def _protocolInvalid(self, local, remote):
        self.transport.loseConnection()
        self.protocolInvalid(local, remote)

    def protocolInvalid(self, local, remote):
        pass

    def sendPackets(self, packets):
        if self.established:
            self.dataWrite(''.join([binarypack.pack(packet) for packet in packets]))
        else:
            self._out_buffer.extend(packets)

    def sendPacket(self, packet):
        if self.established:
            self.dataWrite(binarypack.pack(packet))
        else:
            self._out_buffer.append(packet)

    def packetReceived(self, packet):
        raise NotImplementedError('packetReceived has to be implemented by sub protocol (eg. client or server)')

    def ignoreIncomingData(self):
        self._ignore_incoming = True
        self._data = b""

    def _keepalive_init(self):
        self._keepalive_timer = reactor.callLater(self._keepalive_delay, self._keepalive)

    def _keepalive_uninit(self):
        if self._keepalive_timer:
            if self._keepalive_timer.active():
                self._keepalive_timer.cancel()
            self._keepalive_timer = None

    def _keepalive_reset(self):
        if self._keepalive_timer:
            if self._keepalive_timer.active():
                self._keepalive_timer.reset(self._keepalive_delay)
            else:
                self._keepalive_init()

    def _keepalive(self):
        self.sendPacket(PacketPing())


