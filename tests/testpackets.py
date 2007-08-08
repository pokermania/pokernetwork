# -*- mode: python -*-
#
# Copyright (C) 2007 Loic Dachary <loic@dachary.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
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

import os

import unittest

class PacketsTestBase(unittest.TestCase):

    def setUp(self):
        self.verbose = int(os.environ.get('VERBOSE_T', '3'))
        
    @staticmethod
    def polute(packet):
        int_value = 1
        info = packet.info[2:] # skip type + length
        for (variable, default, pack_type) in info:
            if pack_type in ('I', 'H', 'B'):
                packet.__dict__[variable] = int_value
                int_value += 1
        
    def packetCheck(self, **kwargs):
        packet_type = kwargs['type']
        del kwargs['type']
        packet = packet_type(**kwargs)
        self.polute(packet)
        size = packet.calcsize()
        packet.infoInit()
        self.assertEqual(size, packet.infoCalcsize())
        packed = packet.pack()
        self.assertEqual(size, len(packed))
        self.assertEqual(packed, packet.infoPack())
        other_packet = packet_type()
        if other_packet.unpack(packed) != None:
            self.assertEqual(repr(packet), repr(other_packet))
            self.assertEqual(packet, other_packet)
            self.assertEqual(packed, other_packet.pack())
            info_packet = packet_type()
            info_packet.infoInit()
            info_packet.infoUnpack(packed)
            self.assertEqual(packed, info_packet.infoPack())
            return packet
        else:
            return None
