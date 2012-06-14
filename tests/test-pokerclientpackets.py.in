#!@PYTHON@
# -*- mode: python -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C)       2009 Bradley M. Kuhn <bkuhn@ebb.org>
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

import sys, os
sys.path.insert(0, "@top_srcdir@")
sys.path.insert(0, "@srcdir@")
sys.path.insert(0, "..")

import unittest
from struct import pack, unpack, calcsize

import testpackets

from pokerengine.pokercards import PokerCards
from pokerengine.pokerchips import PokerChips

from pokernetwork import packets
from pokernetwork import pokerclientpackets

class PokerClientPacketsTestCase(testpackets.PacketsTestBase):

    @staticmethod
    def copydict(packet):
        packet_dict = packet.__dict__.copy()
        if packet_dict.has_key('length'): del packet_dict['length']
        if packet_dict.has_key('type'): del packet_dict['type']
        return packet_dict

    def comparedict(self, packet, other_packet):
        packet_dict = self.copydict(packet)
        other_packet_dict = self.copydict(other_packet)
        self.assertEqual(packet_dict, other_packet_dict)

    #--------------------------------------------------------------    
    def test_packets(self):
        for type in pokerclientpackets._TYPES:
            if pokerclientpackets.PacketFactory.has_key(type):
                self.packetCheck(type = pokerclientpackets.PacketFactory[type])

    #--------------------------------------------------------------    
    def test_chips2amount(self):
        self.assertEqual(10, pokerclientpackets.chips2amount([1, 2, 4, 2]))

    def defineTestPacket(self):
        
        class TestPacket(packets.Packet):
            info = packets.Packet.info + (
                ('f1' , [1, 10], 'c'),
            )
            fields = (
                "\x0a", # type
                "\0\0", # length
                "\0\0\0\x0a", # f1
            )
            binary = fields[0] + pack('!H', len("".join(fields))) + "".join(fields[2:])

        d = {}
        d['PacketFactory'] = {}
        d['PacketNames'] = {}
        packets.Packet.infoDeclare(d, TestPacket, packets.Packet, 'NAME', 10)
        return TestPacket

    def test_infoPack(self):
        type = self.defineTestPacket()
        packet = type()
        self.assertEqual(type.binary, packet.infoPack())

    def test_infoPackFail(self):
        type = self.defineTestPacket()
        class Foo:
            pass
        type.info = packets.Packet.info + (('f1' , Foo(), 'j'),)
        self.failUnlessRaises(TypeError, type)

    def test_infoUnpack(self):
        pkt_type = self.defineTestPacket()
        packet = pkt_type()
        packet.infoUnpack(pkt_type.binary)
        self.assertEqual(pkt_type.binary, packet.infoPack())

    def test_infoCalcsize(self):
        pkt_type = self.defineTestPacket()
        packet = pkt_type()
        self.assertEqual(len(pkt_type.binary), packet.infoCalcsize())

#--------------------------------------------------------------
def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PokerClientPacketsTestCase))
    return suite
    
#--------------------------------------------------------------
def Run(verbose = 1):
    return unittest.TextTestRunner(verbosity=verbose).run(GetTestSuite())
    
#--------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "( cd .. ; ./config.status tests/test-pokerclientpackets.py ) ; ( cd ../tests ; make COVERAGE_FILES='../pokernetwork/pokerclientpackets.py ../pokernetwork/OLDpokerclientpackets.py' TESTS='coverage-reset test-pokerclientpackets.py coverage-report' check )"
# End:
