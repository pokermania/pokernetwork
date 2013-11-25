
from pokernetwork.protocol import log as protocol_log
log = protocol_log.get_child('binarypack')

from pokernetwork.protocol._base import BaseProtocol

from pokerpackets import binarypack
from pokerpackets.binarypack._binarypack import S_PACKET_HEAD as s_packet_head

from pokernetwork import protocol_number
from pokernetwork.version import Version
protocol_version = Version(protocol_number)
protocol_handshake = 'CGI %03d.%d%02d\n' % protocol_version.version

class UGAMEProtocol(BaseProtocol):

    log = log.get_child('UGAMEProtocol')

    def __init__(self):
        BaseProtocol.__init__(self)

        self._data = b""
        self._out_buffer = [] # as long as not established outgoing packets are buffered

        self._cur_packet_length = None # None: not currently on any packet
        self._ignore_incoming = False

    def connectionMade(self):
        self._sendVersion()

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
                    self.packetReceived(binarypack.unpack(self._data))
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

    def dataWrite(self, data, reset_keepalive=True):
        if reset_keepalive:
            self._keepalive_reset()
        self.transport.write(data)

    def _sendVersion(self):
        self.dataWrite(protocol_handshake)

    def _checkVersion(self, string):
        if string == protocol_handshake:
            self._protocolEstablished()
        else:
            self._protocolInvalid(protocol_handshake, string)

    def _protocolEstablished(self):
        BaseProtocol.connectionMade(self)
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

    def sendPackets(self, packets, reset_keepalive=True):
        if self.established:
            self.dataWrite(''.join([binarypack.pack(packet) for packet in packets]))
        else:
            self._out_buffer.extend(packets)

    def sendPacket(self, packet, reset_keepalive=True):
        if self.established:
            self.dataWrite(binarypack.pack(packet), reset_keepalive)
        else:
            self._out_buffer.append(packet)

    def packetReceived(self, packet):
        raise NotImplementedError('packetReceived has to be implemented by sub protocol (eg. client or server)')
