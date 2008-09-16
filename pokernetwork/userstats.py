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

# I decided to make the elements for lookup a table, an avatar, and a
# service.  I felt this was the most likely set of objects that would be
# used for looking up stats, and of course they need not be used if not
# needed.

from pokerpackets import PacketPokerPlayerStats, PacketPokerStatsSupported

class UserStatsAccessor:
    def __init__(self):
        self.statsSupported = []
    # ----------------------------------------------------------------------
    def error(self, string):
        self.message("ERROR " + string)
    # ----------------------------------------------------------------------
    def message(self, string):
        print string
    # ----------------------------------------------------------------------
    def getSupportedStatsList(self):
        return self.statsSupported
    # ----------------------------------------------------------------------
    def getStatValue(self, stat, avatar = None, table = None, service = None):
        if stat in self.statsSupported:
            return self._lookupValidStat(stat, avatar, table, service)
        else:
            self.error("invalid user statistic, %s" % stat)
            return None
    # ----------------------------------------------------------------------
    def _lookupValidStat(self, stat, avatar, table, service):
        return "UNIMPLEMENTED IN BASE CLASS"
############################################################################
from _mysql_exceptions import ProgrammingError
class UserStatsRankPercentileAccessor(UserStatsAccessor):
    def __init__(self):
        UserStatsAccessor.__init__(self)
        self.statsSupported = ['percentile', 'rank']
    # ----------------------------------------------------------------------
    def _lookupValidStat(self, stat, avatar, table, service):
        currency = table.currency_serial
        if not currency or currency < 0:
            return None
        user = avatar.getSerial()
        if not user or user < 0:
            return None
        value = None
        try:
            cursor = service.db.cursor()
            cursor.execute("SELECT %s from rank where currency_serial = %d and user_serial = %d"
                           % (stat, currency, user) )
            tuple = cursor.fetchone()
            if tuple != None: (value,) = tuple
            cursor.close()
        except ProgrammingError, (code, errorStr):
            self.error("RankPercentile: (MySQL code %d): %s" % (code, errorStr))
        return value
############################################################################
class UserStatsLookup:
    def __init__(self, service = None):
        self.service = service
        self.stat2accessor = {}
    # ----------------------------------------------------------------------
    def error(self, string):
        self.message("ERROR " + string)
    # ----------------------------------------------------------------------
    def message(self, string):
        print string
    # ----------------------------------------------------------------------
    def getStatValue(self, stat, table = None, avatar = None):
        if self.stat2accessor.has_key(stat):
            return self.stat2accessor[stat].getStatValue(stat, avatar, table, self.service)
        else:
            self.error("unsupported user statistic, %s" % stat)
            return None
    # ----------------------------------------------------------------------
    def allStatsAsPacket(self, table, avatar):
        sd = {}
        for stat in self.stat2accessor.keys():
            sd[stat] = self.getStatValue(stat, table, avatar)
        return PacketPokerPlayerStats(serial = avatar.getSerial(), statsDict = sd)
    # ----------------------------------------------------------------------
    def getSupportedListAsPacket(self):
        return PacketPokerStatsSupported(stats = self.stat2accessor.keys())
############################################################################
class UserStatsRankPercentileLookup(UserStatsLookup):
    def __init__(self, service = None):
        UserStatsLookup.__init__(self, service)
        self.service = service
        self.stat2accessor = { 'percentile' : UserStatsRankPercentileAccessor(),
                               'rank' : UserStatsRankPercentileAccessor() }
############################################################################
class UserStatsFactory:
    def error(self, string):
        self.message("ERROR " + string)
    # ----------------------------------------------------------------------
    def message(self, string):
        print string
    # ----------------------------------------------------------------------
    def getStatsClass(self, classname):
        if classname == "": return None
        classname = "UserStats" + classname + "Lookup"
        try:
            return getattr(__import__('userstats', globals(), locals(), [classname]), classname)
        except AttributeError, ae:
            self.error(ae.__str__())
            return None
############################################################################
