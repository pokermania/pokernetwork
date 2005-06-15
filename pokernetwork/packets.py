#
# Copyright (C) 2004 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
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
# Authors:
#  Loic Dachary <loic@gnu.org>
#  Henry Precheur <henry@precheur.org>
#
from struct import pack, unpack, calcsize

from string import join

PacketFactory = {}
PacketNames = {}

PACKET_NONE = 0
PacketNames[PACKET_NONE] = "NONE"

class Packet:
    """

     Packet base class
    
    """

    type = PACKET_NONE
    length = -1
    format = "!BH"
    format_size = calcsize(format)

    format_list_length = "!B"

    def pack(self):
        return pack(Packet.format, self.type, self.calcsize())

    def unpack(self, block):
        (self.type,self.length) = unpack(Packet.format, block[:Packet.format_size])
        return block[Packet.format_size:]

    def calcsize(self):
        return Packet.format_size

    def packlist(self, list, format):
        block = pack(Packet.format_list_length, len(list))
        for value in list:
            block += pack(format, value)
        return block

    def unpacklist(self, block, format):
        (length,) = unpack(Packet.format_list_length, block[:calcsize(Packet.format_list_length)])
        format_size = calcsize(format)
        block = block[calcsize(Packet.format_list_length):]
        list = []
        for i in xrange(length):
            list.append(unpack(format, block[:format_size])[0])
            block = block[format_size:]
        return (block, list)

    def calcsizelist(self, list, format):
        return calcsize(Packet.format_list_length) + len(list) * calcsize(format)

    def packstring(self, string):
        return pack("!H", len(string)) + string

    def unpackstring(self, block):
        offset = calcsize("!H")
        (length,) = unpack("!H", block[:offset])
        string = block[offset:offset + length]
        return (block[offset + length:], string)

    def calcsizestring(self, string):
        return calcsize("!H") + len(string)

    def __str__(self):
        return "type = %s(%d)" % ( PacketNames[self.type], self.type )

    def __repr__(self):
        return self.__str__()

PacketFactory[PACKET_NONE] = Packet

########################################

PACKET_STRING = 1
PacketNames[PACKET_STRING] = "STRING"

class PacketString(Packet):
    """

    Packet containing a single string
    
    """

    type = PACKET_STRING
    string = ""

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("string"):
            self.string = kwargs["string"]

    def pack(self):
        return Packet.pack(self) + self.packstring(self.string)

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (block, self.string) = self.unpackstring(block)
        return block

    def calcsize(self):
        return Packet.calcsize(self) + self.calcsizestring(self.string)

    def __str__(self):
        return Packet.__str__(self) + " string = %s" % self.string

PacketFactory[PACKET_STRING] = PacketString

########################################

PACKET_INT = 2
PacketNames[PACKET_INT] = "INT"

class PacketInt(Packet):
    """

    Packet containing an unsigned integer value
    
    """

    type = PACKET_INT
    value = 0
    format = "!I"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("value"):
            self.value = kwargs["value"]

    def pack(self):
        return Packet.pack(self) + pack(PacketInt.format, self.value)

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (self.value,) = unpack(PacketInt.format, block[:PacketInt.format_size])
        return block[PacketInt.format_size:]

    def calcsize(self):
        return Packet.calcsize(self) + PacketInt.format_size

    def __str__(self):
        return Packet.__str__(self) + " value = %d" % self.value

PacketFactory[PACKET_INT] = PacketInt

########################################

PACKET_SERIAL = 3
PacketNames[PACKET_SERIAL] = "SERIAL"

class PacketSerial(Packet):
    """
    Serial Number
    """

    type = PACKET_SERIAL

    serial = 0
    format = "!I"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("serial"):
            self.serial = kwargs["serial"]

    def pack(self):
        return Packet.pack(self) + pack(PacketSerial.format, self.serial)

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (self.serial,) = unpack(PacketSerial.format, block[:PacketSerial.format_size])
        return block[PacketSerial.format_size:]

    def calcsize(self):
        return Packet.calcsize(self) + PacketSerial.format_size

    def __str__(self):
        return Packet.__str__(self) + " serial = %d" % self.serial
        
PacketFactory[PACKET_SERIAL] = PacketSerial

########################################

PACKET_QUIT = 4
PacketNames[PACKET_QUIT] = "QUIT"

class PacketQuit(Packet):
    "Client tells the server it will leave"

    type = PACKET_QUIT

PacketFactory[PACKET_QUIT] = PacketQuit

########################################

PACKET_AUTH_OK = 5
PacketNames[PACKET_AUTH_OK] = "AUTH_OK"

class PacketAuthOk(Packet):
    """
    Authentication successfull
    """

    type = PACKET_AUTH_OK

PacketFactory[PACKET_AUTH_OK] = PacketAuthOk

########################################

PACKET_AUTH_REFUSED = 6
PacketNames[PACKET_AUTH_REFUSED] = "AUTH_REFUSED"

class PacketAuthRefused(Packet):
    """
    Authentication failed
    """

    type = PACKET_AUTH_REFUSED

PacketFactory[PACKET_AUTH_REFUSED] = PacketAuthRefused

########################################

PACKET_LOGIN = 7
PacketNames[PACKET_LOGIN] = "LOGIN"

class PacketLogin(Packet):
    """

    Packet containing a single name + a password
    
    """

    type = PACKET_LOGIN
    name = ""
    password = ""

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("name"):
            self.name = kwargs["name"]
        if kwargs.has_key("password"):
            self.password = kwargs["password"]

    def pack(self):
        return Packet.pack(self) + self.packstring(self.name) + self.packstring(self.password)

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (block, self.name) = self.unpackstring(block)
        (block, self.password) = self.unpackstring(block)
        return block

    def calcsize(self):
        return Packet.calcsize(self) + self.calcsizestring(self.name) + self.calcsizestring(self.password)

    def __str__(self):
        return Packet.__str__(self) + " name = %s, password = %s" % (self.name, self.password)

PacketFactory[PACKET_LOGIN] = PacketLogin

########################################

PACKET_AUTH_REQUEST = 8
PacketNames[PACKET_AUTH_REQUEST] = "AUTH_REQUEST"

class PacketAuthRequest(Packet):
    """
    Packet to asck authentification from the client
    """

    type = PACKET_AUTH_REQUEST

PacketFactory[PACKET_AUTH_REQUEST] = PacketAuthRequest

########################################

PACKET_AUTH_EXPIRES = 9
PacketNames[PACKET_AUTH_EXPIRES] = "AUTH_EXPIRES"

class PacketAuthExpires(Packet):
    """
    The server gave up waiting for auth packets.
    """

    type = PACKET_AUTH_EXPIRES

PacketFactory[PACKET_AUTH_EXPIRES] = PacketAuthExpires

########################################

PACKET_LIST = 10
PacketNames[PACKET_LIST] = "LIST"

class PacketList(Packet):
    """

    Packet containing a list of packets
    
    """

    type = PACKET_LIST
    packets = []
    format = "!B"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        self.packets = kwargs.get("packets", [])

    def pack(self):
        block = Packet.pack(self) + pack(PacketList.format, len(self.packets))
        for packet in self.packets:
            block += packet.pack()
        return block

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (length,) = unpack(PacketList.format, block[:PacketList.format_size])
        block = block[PacketList.format_size:]
        type = Packet()
        count = 0
        self.packets = []
        while len(block) > 0 and count < length:
            type.unpack(block)
            if not PacketFactory.has_key(type.type):
                print " *ERROR* unknown packet type %d (known types are %s)" % ( type.type, PacketNames)
                return
            packet = PacketFactory[type.type]()
            block = packet.unpack(block)
            count += 1
            self.packets.append(packet)
        if count != length:
            print " *ERROR* expected a list of %d packets but found only %d" % ( length, count)
        return block

    def calcsize(self):
        return Packet.calcsize(self) + PacketList.format_size + sum([ packet.calcsize() for packet in self.packets ])

    def __str__(self):
        return Packet.__str__(self) + join([packet.__str__() for packet in self.packets ])

PacketFactory[PACKET_LIST] = PacketList

########################################

PACKET_LOGOUT = 12
PacketNames[PACKET_LOGOUT] = "LOGOUT"

class PacketLogout(Packet):
    """
    Login out
    """

    type = PACKET_LOGOUT

PacketFactory[PACKET_LOGOUT] = PacketLogout

########################################

PACKET_AUTH_CANCEL = 13
PacketNames[PACKET_AUTH_CANCEL] = "AUTH_CANCEL"

class PacketAuthCancel(Packet):
    """
    Authentication canceled by client
    """

    type = PACKET_AUTH_CANCEL

PacketFactory[PACKET_AUTH_CANCEL] = PacketAuthCancel

########################################

PACKET_ERROR = 14
PacketNames[PACKET_ERROR] = "ERROR"

class PacketError(Packet):
    """

    Packet describing an error
    
    """

    type = PACKET_ERROR
    other_type = 0
    code = 0
    message = ""

    format = "!IB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.message = kwargs.get("message", "no message")
        self.code = kwargs.get("code", 0)
        self.other_type = kwargs.get("other_type", PACKET_ERROR)

    def pack(self):
        return Packet.pack(self) + self.packstring(self.message) + pack(PacketError.format, self.code, self.other_type)

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (block, self.message) = self.unpackstring(block)
        (self.code, self.other_type) = unpack(PacketError.format, block[:PacketError.format_size])
        return block[PacketError.format_size:]

    def calcsize(self):
        return Packet.calcsize(self) + self.calcsizestring(self.message) + PacketError.format_size

    def __str__(self):
        return Packet.__str__(self) + " message = %s, code = %d, other_type = %s" % (self.message, self.code, PacketNames[self.other_type])

PacketFactory[PACKET_ERROR] = PacketError

########################################

PACKET_BOOTSTRAP = 15
PacketNames[PACKET_BOOTSTRAP] = "BOOTSTRAP"

class PacketBootstrap(Packet):
    "Client tells the server it will leave"

    type = PACKET_BOOTSTRAP

PacketFactory[PACKET_BOOTSTRAP] = PacketBootstrap

########################################

PACKET_PROTOCOL_ERROR = 16
PacketNames[PACKET_PROTOCOL_ERROR] = "PROTOCOL_ERROR"

class PacketProtocolError(PacketError):
    """
    Client protocol version does not match server protocol version.
    """

    type = PACKET_PROTOCOL_ERROR

PacketFactory[PACKET_PROTOCOL_ERROR] = PacketProtocolError

