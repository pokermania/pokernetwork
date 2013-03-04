#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pokernetwork import protocol
from pokerpackets import packets, binarypack
import sys, unittest


class UGAMEProtocolTestCase(unittest.TestCase):

    def setUp(self):
        self.protocol = protocol.UGAMEProtocol()

    def tearDown(self):
        del self.protocol

    def test_init(self):
        assert self.protocol.established == False

    def test_connectionMade(self):
        global _sendVersion_count
        _sendVersion_count = 0
        def _sendVersion():
            global _sendVersion_count
            _sendVersion_count += 1
        self.protocol._sendVersion = _sendVersion
    
        self.protocol.connectionMade()
        assert _sendVersion_count == 1

    def test_dataReceived(self):
        global packetReceived_args
        packetReceived_args = []
        self.protocol.packetReceived = lambda *a: packetReceived_args.append(a)
        self.protocol.transport = self.mock_transport([])

        self.protocol.dataReceived(protocol.protocol_handshake)
        assert self.protocol.established

        packed = binarypack.pack(packets.PacketLogin())
        self.protocol.dataReceived(packed)
        assert packetReceived_args == [(packets.PacketLogin(),)]
        packetReceived_args = []

        # small chunks
        for c in packed:
            self.protocol.dataReceived(c)
        assert packetReceived_args == [(packets.PacketLogin(),)]
        packetReceived_args = []

        # big chunks (2.5 + 0.5 packets)
        self.protocol.dataReceived(packed + packed + packed[:-3])
        assert len(packetReceived_args) == 2
        assert packetReceived_args[0] == (packets.PacketLogin(),)
        assert packetReceived_args[1] == (packets.PacketLogin(),)
        self.protocol.dataReceived(packed[-3:])
        assert len(packetReceived_args) == 3
        assert packetReceived_args[2] == (packets.PacketLogin(),)

    def test_dataWrite(self):
        data_list = []
        self.protocol.transport = self.mock_transport(data_list)
        self.protocol.dataWrite("test")
        assert data_list == ['test']

    def test__sendVersion(self):
        data_list = []
        self.protocol.transport = self.mock_transport(data_list)
        self.protocol._sendVersion()
        assert data_list == [protocol.protocol_handshake]

    def test__checkVersion(self):
        "UGAMEProtocol::_checkVersion should check the remote version string" \
        " against the local one and either call _protocolEstablished or _protocolInvalid"
        _protocolEstablished_args = []
        _protocolInvalid_args = []
        self.protocol._protocolEstablished = lambda *a: _protocolEstablished_args.append(a)
        self.protocol._protocolInvalid = lambda *a: _protocolInvalid_args.append(a)


        self.protocol._checkVersion(protocol.protocol_handshake)
        assert len(_protocolEstablished_args) == 1

        self.protocol._checkVersion('CGI 000.000\n')
        assert len(_protocolInvalid_args) == 1

    def test_sendPackets(self):
        self.protocol.sendPackets([packets.PacketPing(), packets.PacketPing()])
        assert len(self.protocol._out_buffer) == 2

        self.protocol.established = True
        data_list = []
        self.protocol.transport = self.mock_transport(data_list)
        self.protocol.sendPackets([packets.PacketPing(), packets.PacketPing()])
        assert data_list == ['\x05\x00\x00\x05\x00\x00']

    def test_sendPacket(self):
        "UGAMEProtocol::sendPacket should take a packet, check if connection is" \
        " established and either dataWrite the packed packet or push the packet onto the _out_buffer"
        data_list = []
        self.protocol.transport = self.mock_transport(data_list)

        # not established
        self.protocol.sendPacket(packets.PacketPing())
        assert self.protocol._out_buffer == [packets.PacketPing()]

        # established
        self.protocol.established = True
        self.protocol.sendPacket(packets.PacketPing())
        assert data_list == [binarypack.pack(packets.PacketPing())]

    def mock_transport(self, data_list=[]):
        class MockTransport:
            def __init__(self, _data_list):
                self._data_list = _data_list

            def write(self, data):
                self._data_list.append(data)
        return MockTransport(data_list)


if __name__ == '__main__':
    unittest.main()


