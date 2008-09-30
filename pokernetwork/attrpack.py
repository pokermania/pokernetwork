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

# methods for looking up stats, and allowing for mix-in of different types
# of stats.  Each stat is usually looked up with a UserStatsAccessor class
# (or a subclass thereof).  The UserStatsLookup class itself (or
# subclasses thereof) are the things used by other classes to lookup
# statistics.

# I decided to make the elements for lookup a table, a user_serial, and a
# service.  I felt this was the most likely set of objects that would be
# used for looking up stats, and of course they need not be used if not
# needed.

from pokerpackets import PacketPokerGetAttrs, PacketPokerAttrs, PacketPokerGetSupportedAttrs, PacketPokerSupportedAttrs
############################################################################
class AttrsFactory:

    """The Attrs system is designed to be a flexible and arbitrary key/value
    system for object types when we want poker-network to have
    easily-implemented aribitrary data associated with a particular item.

    The public interface usage looks something like this (although "Attr" will
    be replaced with "SOMETHING" since this is a virtual base class):

        attrLookup = AttrFactory().getClass("MySpecialStuff")(args...)

        answerGetSupported = attrLookup.supportedAttrsAsPacket(args...)
        #  Send packet inside answerGetSupported to client...
        answerGetAttrs     = attrLookup.allStatsAsPacket(args...)
        #  Send packet inside answerGetAttrs to client...

    The general idea is that only poker-network code that knows a *thing*
    about what key/value attributes are being supported for the particular
    SOMETHING are specific to the classes defined by "MySpecialStuff".

    The Attr base classes are currently used to implement the UserStats (in
    userstats.py) and TourneyAttrs (in tourneyattrs.py).  You may want to read
    the code in those files before reading further here, because understanding
    the code here in detail is only needed if you want to write a new
    SOMETHING.

         Actually Using This Class To Implement New Attribute System
        -----------------------------------------------------------

    If you want to implement an attribute system for SOMETHING, you should
    (initially) derive from three classes, AttrFactory (this one),
    AttrLookup, and AttrAccessor.  For this one:
         SOMETHINGFactory (base class: AttrFactory)
             what to override:
                 __init__() : set the right module name of where are in.
         
    Note that you will also need to implement the following packet types
    in pokerpackets.py:
        PacketPokerGetSOMETHING           (base class: PacketPokerGetAttrs)
        PacketPokerSOMETHING              (base class: PacketPokerAttrs)
        PacketPokerGetSupportedSOMETHING  (base class: PacketPokerGetSupportedAttrs)
        PacketPokerSupportedSOMETHING     (base class: PacketPokerSupportedAttrs)
"""

    def error(self, string):
        self.message("ERROR " + string)
    # ----------------------------------------------------------------------
    def message(self, string):
        print string
    # ----------------------------------------------------------------------
    def getClass(self, classname):
        classname = "UserStats" + classname + "Lookup"
        try:
            return getattr(__import__('userstats', globals(), locals(), [classname]), classname)
        except AttributeError, ae:
            self.error(ae.__str__())
        return UserStatsLookup
############################################################################

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
    def getStatValue(self, stat, userSerial = None, table = None, service = None):
        if stat in self.statsSupported:
            return self._lookupValidStat(stat, userSerial, table, service)
        else:
            self.error("invalid user statistic, %s" % stat)
            return None
    # ----------------------------------------------------------------------
    def _lookupValidStat(self, stat, userSerial, table, service):
        return "UNIMPLEMENTED IN BASE CLASS"
############################################################################
from _mysql_exceptions import ProgrammingError
class UserStatsRankPercentileAccessor(UserStatsAccessor):
    def __init__(self):
        UserStatsAccessor.__init__(self)
        self.statsSupported = ['percentile', 'rank']
    # ----------------------------------------------------------------------
    def _lookupValidStat(self, stat, userSerial, table, service):
        currency = table.currency_serial
        if currency == None or currency < 0:
            return None
        if not userSerial or userSerial <= 0:
            return None
        value = None
        try:
            cursor = service.db.cursor()
            cursor.execute("SELECT %s from rank where currency_serial = %d and user_serial = %d"
                           % (stat, currency, userSerial) )
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
    def getStatValue(self, stat, table = None, userSerial = None):
        if self.stat2accessor.has_key(stat):
            return self.stat2accessor[stat].getStatValue(stat, userSerial, table, self.service)
        else:
            self.error("unsupported user statistic, %s" % stat)
            return None
    # ----------------------------------------------------------------------
    def allStatsAsPacket(self, table, userSerial):
        sd = {}
        for stat in self.stat2accessor.keys():
            sd[stat] = self.getStatValue(stat, table, userSerial)
        return PacketPokerPlayerStats(serial = userSerial, statsDict = sd)
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
