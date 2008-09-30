# Copyright (C)             2008 Bradley M. Kuhn <bkuhn@ebb.org>
#
# This program gives you software freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation, either version 3 of the License, or (at your
# option) any later version of the AGPL.
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
# Authors:
#  Bradley M. Kuhn <bkuhn@ebb.org>

# This is designed to be a flexible user stats package to allow various
# methods for looking up stats, and allowing for mix-in of different types
# of stats.  Each stat is usually looked up with a UserStatsAccessor class
# (or a subclass thereof).  The UserStatsLookup class itself (or
# subclasses thereof) are the things used by other classes to lookup
# statistics.

# It is based on the "attrspack" system, which is in file attrspack.py

from pokerpackets import PacketPokerPlayerStats, PacketPokerSupportedPlayerStats
from attrpack import AttrsAccessor, AttrsFactory, AttrsLookup
############################################################################
from _mysql_exceptions import ProgrammingError
class UserStatsRankPercentileAccessor(AttrsAccessor):
    def __init__(self):
        AttrsAccessor.__init__(self)
        self.attrsSupported = ['percentile', 'rank']
        self.expectLookupArgs = [ 'service', 'table', 'serial' ]
    # ----------------------------------------------------------------------
    def _lookupValidAttr(self, stat, serial = -1, table = None, service = None):
        currency = table.currency_serial
        if currency == None or currency < 0:
            return None
        if not serial or serial <= 0:
            return None
        value = None
        try:
            cursor = service.db.cursor()
            cursor.execute("SELECT %s from rank where currency_serial = %d and user_serial = %d"
                           % (stat, currency, serial) )
            tuple = cursor.fetchone()
            if tuple != None: (value,) = tuple
            cursor.close()
        except ProgrammingError, (code, errorStr):
            self.error("RankPercentile: (MySQL code %d): %s" % (code, errorStr))
        return value
############################################################################
class UserStatsRankPercentileLookup(AttrsLookup):
    def __init__(self, service = None):
        self.service = service
        AttrsLookup.__init__(self,
           attr2accessor = { 
                'percentile' : UserStatsRankPercentileAccessor(),
                'rank' : UserStatsRankPercentileAccessor() },
           packetClassesName = "PlayerStats",
           requiredAttrPacketFields = [ 'serial' ])
    # ----------------------------------------------------------------------
    def getAttrsAsPacket(self, **kwargs):
        if not kwargs.has_key('service'):
            kwargs['service'] = self.service
        return AttrsLookup.getAttrsAsPacket(self, **kwargs)
############################################################################
class UserStatsEmptyLookup(AttrsLookup):
    def __init__(self, service = None):
        self.service = service
        AttrsLookup.__init__(self,
           attr2accessor = { },
           packetClassesName = "PlayerStats",
           requiredAttrPacketFields = [ 'serial' ])
    # ----------------------------------------------------------------------
    def getAttrsAsPacket(self, **kwargs):
        if not kwargs.has_key('service'):
            kwargs['service'] = self.service
        return AttrsLookup.getAttrsAsPacket(self, **kwargs)
############################################################################
class UserStatsFactory(AttrsFactory):
    def __init__(self):
        AttrsFactory.__init__(self, moduleStr = 'userstats',
                              classPrefix = "UserStats", defaultClass = "UserStatsEmptyLookup")
############################################################################
