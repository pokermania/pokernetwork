
from pokernetwork.protocol import log as protocol_log
log = protocol_log.get_child('msgpack')

import pokerpackets.networkpackets
from pokerpackets.packets import type_id2type, name2type
from pokerpackets.dictpack import packet2dict
from pokernetwork.util.trace import format_exc

import msgpack as _msgpack

from pokernetwork.protocol._base import BaseProtocol

class MsgpackProtocol(BaseProtocol):

    log = log.get_child('MsgpackProtocol')

    def __init__(self):
        BaseProtocol.__init__(self)

        self._numeric_type = True
        self._unpacker = _msgpack.Unpacker()
        self._packer = _msgpack.Packer(autoreset=False)

    def dataReceived(self, data):
        self._unpacker.feed(data)

        for p_type_id, p_dict in self._unpacker:
            if isinstance(p_type_id, int):
                self._numeric_type = True
                self.packetReceived(type_id2type[p_type_id](**p_dict))
            elif isinstance(p_type_id, basestring):
                self._numeric_type = False
                self.packetReceived(name2type[p_type_id](**p_dict))

    def dataWrite(self, data, reset_keepalive=True):
        if reset_keepalive:
            self._keepalive_reset()
        self.transport.write(data)

    def sendPackets(self, packets):
        for packet in packets:
            p_dict = packet2dict(packet, self._numeric_type)
            p_type = p_dict.pop('type')
            self._packer.pack([p_type, p_dict])
        self.dataWrite(self._packer.bytes())
        self._packer.reset()

    def sendPacket(self, packet, reset_keepalive=True):
        p_dict = packet2dict(packet, self._numeric_type)
        p_type = p_dict.pop('type')
        self._packer.pack([p_type, p_dict])
        self.dataWrite(self._packer.bytes(), reset_keepalive)
        self._packer.reset()


class ServerMsgpackProtocol(MsgpackProtocol):

    def __init__(self):
        self.avatar = None
        MsgpackProtocol.__init__(self)

    def packetReceived(self, packet):
        try:
            if self.avatar:
                self.sendPackets(self.avatar.handlePacket(packet))
        except:
            self.log.error(format_exc())
            self.transport.loseConnection()

    def connectionMade(self):
        self.avatar = self.factory.createAvatar()
        self.avatar.setProtocol(self)
        MsgpackProtocol.connectionMade(self)

    def connectionLost(self, reason):
        if self.avatar:
            self.factory.destroyAvatar(self.avatar)
            self.avatar = None
        MsgpackProtocol.connectionLost(self, reason)
