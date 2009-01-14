#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2009 Loic Dachary <loic@dachary.org>
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
from pokerprizes.prizes import PokerPrizes
from MySQLdb.cursors import DictCursor
from pokernetwork.pokerpackets import PacketPokerTourneyInfo

class Handle(PokerPrizes):

    def __call__(self, service, packet, tourneys):
        info = PacketPokerTourneyInfo()
        def schedule_serials(tourney):
            if hasattr(tourney, 'schedule_serial'):
                return tourney.schedule_serial
            else:
                return tourney.serial
        serials = map(schedule_serials, tourneys)
        cursor = service.db.cursor(DictCursor)
        serials_sql = ",".join(map(lambda serial: str(serial), set(serials)))
        sql = "SELECT p.* FROM prizes AS p, tourneys_schedule2prizes AS t WHERE p.serial = t.prize_serial AND t.tourneys_schedule_serial IN ( %s ) GROUP BY p.serial" % serials_sql
        if self.verbose >= 3:
            self.message(sql)
        cursor.execute(sql)
        info.serial2prize = {}
        for row in cursor.fetchall():
            info.serial2prize[row['serial']] = row
        sql = "SELECT * FROM tourneys_schedule2prizes WHERE tourneys_schedule_serial IN ( %s )" % serials_sql
        if self.verbose >= 3:
            self.message(sql)
        cursor.execute(sql)
        info.tourneys_schedule2prizes = {}
        for row in cursor.fetchall():
            info.tourneys_schedule2prizes[row['tourneys_schedule_serial']] = row['prize_serial']
        cursor.close()
        return info
