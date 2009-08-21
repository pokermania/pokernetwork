#
# Copyright (C) 2008, 2009 Loic Dachary <loic@dachary.org>
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
        self.percentiles = float(self.factory.settings.headerGet("/settings/@percentiles") or 4.0)

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
        self.db.query("DROP TABLE IF EXISTS rank_tmp")
        def create_rank_table(name):
            self.db.query("CREATE TABLE IF NOT EXISTS %s (" % name +
                          "  user_serial INT UNSIGNED NOT NULL," +
                          "  currency_serial INT UNSIGNED NOT NULL," +
                          "  amount BIGINT NOT NULL," +
                          "  rank INT UNSIGNED NOT NULL," +
                          "  percentile TINYINT UNSIGNED DEFAULT 0 NOT NULL," +
                          "  PRIMARY KEY (user_serial, currency_serial)," +
                          "  INDEX (currency_serial, amount)," +
                          "  INDEX (amount)," +
                          "  INDEX (currency_serial)," +
                          "  INDEX (rank)" +
                          ") ENGINE=MyISAM")
        create_rank_table("rank")
        create_rank_table("rank_tmp")
        
    def populate(self):
        cursor = self.db.cursor()
        cursor.execute("SET @rank := 0, @currency_serial := 0, @amount := 0; " +
                       " INSERT INTO rank_tmp " +
                       "  (user_serial, currency_serial, amount, rank)" +
                       "  SELECT user_serial, currency_serial, amount, " +
                       "   GREATEST(" +
                       "     @rank := if(@currency_serial = currency_serial and @amount = amount, @rank, if(@currency_serial <> currency_serial, 1, @rank + 1))," +
                       "     least(0, @amount := amount)," +
                       "     least(0, @currency_serial := currency_serial)) AS rank " +
                       "   FROM user2money ORDER BY currency_serial DESC, amount DESC")
        cursor.close()
        cursor = self.db.cursor()
        cursor.execute("SELECT  currency_serial, COUNT(*) FROM rank_tmp GROUP BY currency_serial")
        for (currency_serial, count) in cursor.fetchall():
            range_count = count / self.percentiles
            for j in xrange(self.percentiles):
                cursor.execute("UPDATE rank_tmp SET percentile = %s WHERE rank > %s AND rank <= %s AND currency_serial = %s", ( j, int(range_count * j), int(range_count * ( j + 1 )), currency_serial))
        cursor.close()
        cursor = self.db.cursor()
        cursor.execute("RENAME TABLE rank to rank_old, rank_tmp TO rank, rank_old TO rank_tmp")
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
