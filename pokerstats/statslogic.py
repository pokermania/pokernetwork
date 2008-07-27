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
import sys
sys.path.insert(0, "..")

import MySQLdb

from twisted.internet import reactor

from pokernetwork.pokerclientpackets import *

class PokerStats:

    BOOTSTRAP	= 1
    MONITOR	= 2
    IDLE	= 3
    
    def __init__(self, factory, connect = True):
        self.factory = factory
        if connect:
            self.setState(PokerStats.BOOTSTRAP)

    def setState(self, state):
        self.state = state
        
    def connect(self):
        p = self.factory.settings.headerGetProperties("/settings/server[%d]/database" % self.factory.server)[0]
        self.db = MySQLdb.connect(host = p["host"],
                                      port = int(p.get("port", '3306')),
                                      user = p["user"],
                                      passwd = p["password"],
                                      db = p["name"])

    def create(self):
        self.db.query("DROP TABLE IF EXISTS rank")
        self.db.query("CREATE TABLE rank (" +
                      "  user_serial INT UNSIGNED NOT NULL," +
                      "  currency_serial INT UNSIGNED NOT NULL," +
                      "  amount BIGINT NOT NULL," +
                      "  rank INT UNSIGNED NOT NULL," +
                      "  PRIMARY KEY (user_serial, currency_serial)," +
                      "  INDEX (currency_serial, amount)," +
                      "  INDEX (amount)" +
                      ") ENGINE=MyISAM")

    def populate(self):
        cursor = self.db.cursor()
        cursor.execute("SET @rank := 0, @currency_serial := 0, @amount := 0; " +
                       " INSERT INTO rank " +
                       "  (user_serial, currency_serial, amount, rank)" +
                       "  SELECT user_serial, currency_serial, amount, " +
                       "   GREATEST(" +
                       "     @rank := if(@currency_serial = currency_serial and @amount = amount, @rank, if(@currency_serial <> currency_serial, 1, @rank + 1))," +
                       "     least(0, @amount := amount)," +
                       "     least(0, @currency_serial := currency_serial)) AS rank " +
                       "   FROM user2money ORDER BY currency_serial DESC, amount DESC")
        cursor.close()
        
    def bootstrap(self, protocol, packet):
        if self.state != PokerStats.BOOTSTRAP:
            self.factory.error("unexpected state %s instead of %s" % ( self.state, PokerStats.MONITOR ))
            return False

        protocol.sendPacket(PacketPokerMonitor())
        self.setState(PokerStats.MONITOR)
        return True
        
    def ack(self, protocol, packet):
        if self.state == PokerStats.MONITOR:
            self.create()
            self.populate()
            self.setState(PokerStats.IDLE)
        else:
            self.factory.error("unexpected state %s instead of %s" % ( self.state, PokerStats.MONITOR ))
            return False
        return True

    def pokerMonitorEvent(self, protocol, packet):
        return True #pragma: no cover
