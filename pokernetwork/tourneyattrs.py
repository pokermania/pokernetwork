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


from pokerpackets import PacketPokerPlayerStats, PacketPokerSupportedPlayerStats
from attrpack import AttrsAccessor, AttrsFactory, AttrsLookup
from random import randint

############################################################################
from _mysql_exceptions import ProgrammingError
class TourneyAttrsSponsoredPrizesAccessor(AttrsAccessor):
    def __init__(self):
        AttrsAccessor.__init__(self)
        self.attrsSupported = ['is_monthly', 'prizes', 'sponsor']
        self.expectLookupArgs = [ 'serial' ]
        # dummyFIXMEdata is used to create dummy data.  Someone else
        # should come along and implement real data.
        self.dummyFIXMEdata = { '_possibleSponsors' : [ 'Joe', 'Jack', 'John' ] }
    # ----------------------------------------------------------------------
    def _lookupValidAttr(self, attr, serial = -1, **kwargs):
        # FIXME: this function shouldn't use the dummy data but should be
        # written to lookup the right data based on serial.
        if serial < 0:
            return None
        if not self.dummyFIXMEdata.has_key(serial):
            isMonthly = True
            if randint(0, 1) == 0: isMonthly = False
            prizes = randint(1, 1200)
            sponsor = self.dummyFIXMEdata['_possibleSponsors'][randint(0, 2)]
            self.dummyFIXMEdata[serial] = { 'is_monthly' : isMonthly,
                                                     'prizes' : prizes,
                                                     'sponsor': sponsor }
        return self.dummyFIXMEdata[serial][attr]
############################################################################
class TourneyAttrsSponsoredPrizesLookup(AttrsLookup):
    def __init__(self):
        tourneyPrizeAcessor = TourneyAttrsSponsoredPrizesAccessor()
        AttrsLookup.__init__(self,
           attr2accessor = { 
                'is_monthly' : tourneyPrizeAcessor,
                'prizes' : tourneyPrizeAcessor,
                'sponsor' : tourneyPrizeAcessor },
           packetClassesName = "TourneyAttrs",
           requiredAttrPacketFields = [ 'serial' ])
    # ----------------------------------------------------------------------
    def getAttrsAsPacket(self, tourney = None, schedule_serial = None):

        """Returns a PacketPokerTourneyAttrs packet with the key/value
        correctly placed. 

        Keyword arguments:

            tourney: if a tourney argument is given, it must be a dict.
                     That dict should either have an entry with key
                     'schedule_serial', which if found will be used as the
                     'serial' for lookup, or it should have a 'serial'
                     dict entry, which will be used instead.  If the
                     tourney dict has neither, then the 'schedule_serial'
                     option is looked at.  If the schedule_serial can be
                     determined from this object, a 'schedule_serial'
                     keyword argument will be *ignored* completely.

            schedule_serial: the schedule_serial value to be used for
                             lookup.  This option is ignored completely if
                             'tourney' is given with a member of
                             'schedule_serial' or 'serial'.  If this
                             option is not given, then the returned packet
                             will have no values.
        """

        if tourney != None:
            if tourney.has_key('schedule_serial'):
                schedule_serial = tourney['schedule_serial']
            elif tourney.has_key('serial'):
                schedule_serial = tourney['serial']
        kwargs = {}
        kwargs['serial'] = schedule_serial
        return AttrsLookup.getAttrsAsPacket(self, **kwargs)
############################################################################
class TourneyAttrsFactory(AttrsFactory):
    def __init__(self):
        AttrsFactory.__init__(self, moduleStr = 'tourneyattrs',
                              classPrefix = "TourneyAttrs", defaultClass = "AttrsLookup")
############################################################################
