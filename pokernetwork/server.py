#
# Copyright (C) 2004, 2005 Mekensleep
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
# 
from struct import pack, unpack
from twisted.internet import reactor, protocol
import MySQLdb

from pokernetwork.packets import *
from pokernetwork.protocol import UGAMEProtocol
from pokernetwork.user import User

AUTH_TIMEOUT = 180

class UGAMEServer(UGAMEProtocol):
    """UGAMEServerProtocol"""

    def __init__(self):
        self.user = User()
        self.__login_timer = None
        self._context = []
        UGAMEProtocol.__init__(self)
        self._poll = False

    def isAuthorized(self, type):
        return self.user.hasPrivilege(self.factory.authGetLevel(type))

    def askAuth(self, packet):
        self.sendPacketVerbose(PacketAuthRequest())
        self._context = [ packet ]
        self.__login_timer = reactor.callLater(AUTH_TIMEOUT, self.__auth_expires)
        self._handler = self.auth

    def __auth_expires(self):
        self.sendPacketVerbose(PacketAuthExpires())
        self.__login_timer = None
        self._handler = self._handleConnection
        self.flushContext()

    def login(self, info):
        (serial, name, privilege) = info
        self.user.serial = serial
        self.user.name = name
        self.user.privilege = privilege
        self.sendPacketVerbose(PacketSerial(serial = self.user.serial))
        self.factory.serial2client[serial] = self
        if self.factory.verbose:
            print "user %s/%d logged in" % ( self.user.name, self.user.serial )

    def logout(self):
        if self.user.serial:
            del self.factory.serial2client[self.user.serial]
            self.user.logout()
        
    def auth(self, packet):
        if ( packet.type != PACKET_LOGIN and
             packet.type != PACKET_AUTH_CANCEL ):
            if self.factory.verbose:
                print "packet prepended to backlog"
            self._context.append(packet)
            return

        if self.__login_timer and self.__login_timer.active():
            self.__login_timer.cancel()
        self.__login_timer = None

        if packet.type == PACKET_AUTH_CANCEL:
            self._handler = self._handleConnection
            return
            
        if self.user.checkNameAndPassword(packet.name, packet.password):
            info = self.factory.auth(packet.name, packet.password)
        else:
            info = False
        if info:
            self.sendPacketVerbose(PacketAuthOk())
            self.login(info)
        else:
            self.sendPacketVerbose(PacketAuthRefused())
        self.flushContext()

    def flushContext(self):
        for packet in self._context:
            print "PACKET %s " % packet
            self._handler = self._handleConnection
            if packet and self.isAuthorized(packet.type):
                if hasattr(packet, "serial"):
                    packet.serial = self.getSerial()
                self._handler(packet)
        self._context = []

    def userRemove(self, packet):
        if self.getSerial() == packet.serial:
            self.factory.userRemove(self.user)
            self.transport.loseConnection()

    def getSerial(self):
        return self.user.serial

    def getName(self):
        return self.user.name

    def getUrl(self):
        return self.user.url

    def getOutfit(self):
        return self.user.outfit
    
    def isLogged(self):
        return self.user.isLogged()
    
    def sendPacket(self, packet):
        self.transport.write(packet.pack())

    def sendPacketVerbose(self, packet):
        if self.factory.verbose > 1:
            print "sendPacket: %s" % str(packet)
        self.sendPacket(packet)
        
    def connectionLost(self, reason):
        self.logout()
        UGAMEProtocol.connectionLost(self, reason)

class UGAMEServerFactory(protocol.ServerFactory):
    """Factory"""

    def __init__(self, *args, **kwargs):
        self.type2auth = {}
        self.database = kwargs["database"]
        self.serial2client = {}
        database = self.database
        self.db = MySQLdb.connect(host = database["host"],
                                  user = database["user"],
                                  passwd = database["password"],
                                  db = database["name"])
        #
        # Database will be close when the object is destroyed
        #
        print "Database connection to %s/%s open" % ( database["host"], database["name"] )        
        self.verbose = 0

    def authSetLevel(self, type, level):
        self.type2auth[type] = level

    def authGetLevel(self, type):
        return self.type2auth.has_key(type) and self.type2auth[type]
    
    def auth(self, name, password):
        cursor = self.db.cursor()
        cursor.execute("select serial, password, privilege from users "
                       "where name = '%s'" % name)
        numrows = int(cursor.rowcount)
        serial = 0
        privilege = User.REGULAR
        if numrows <= 0:
            if self.verbose > 1:
                print "user %s does not exist, create it" % name
            serial = self.userCreate(name, password)
        elif numrows > 1:
            print "more than one row for %s" % name
            return False
        else: 
            (serial, password_sql, privilege) = cursor.fetchone()
            cursor.close()
            if password_sql != password:
                print "password mismatch for %s" % name
                return False

        return (serial, name, privilege)

    def userCreate(self, name, password):
        if self.verbose:
            print "creating user %s" % name,
        cursor = self.db.cursor()
        cursor.execute("insert into users (name, password) values ('%s', '%s')" %
                       (name, password))
        #
        # Accomodate for MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            serial = cursor.lastrowid
        else:
            serial = cursor.insert_id()
        if self.verbose:
            print "create user with serial %s" % serial
        cursor.execute("insert into users_private (serial) values ('%d')" % serial)
        cursor.close()
        return int(serial)

    def userRemove(self, user):
        if self.verbose:
            print "removing %s" % user
        cursor = self.db.cursor()
        cursor.execute("delete from users where serial = %d" % user.serial)
        cursor.close()
