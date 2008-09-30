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
############################################################################
from _mysql_exceptions import ProgrammingError
class TourneySponsoredPrizesAccessor(AttrsAccessor):
    def __init__(self):
        AttrsAccessor.__init__(self)
        self.attrsSupported = ['is_monthly', 'prizes', 'sponsor']
        self.expectLookupArgs = [ 'service', 'table', 'serial' ]
    # ----------------------------------------------------------------------
    def _lookupValidAttr(self, attr, serial = -1, table = None, service = None):
        if attr == 'is_monthly':
            return True
        elif attr == 'prizes':
            return 5
        elif attr == 'sponsor':
            return 'Joe'
############################################################################
class TourneySponsoredPrizesLookup(AttrsLookup):
    def __init__(self, service = None):
        self.service = service
        AttrsLookup.__init__(self,
           attr2accessor = { 
                'is_monthly' : TourneySponsoredPrizesAccessor(),
                'prizes' : TourneySponsoredPrizesAccessor(),
                'sponsor' : TourneySponsoredPrizesAccessor() },
           packetClassesName = "TourneyAttrs",
           requiredAttrPacketFields = [ 'serial' ])
    # ----------------------------------------------------------------------
    def getAttrsAsPacket(self, **kwargs):
        if not kwargs.has_key('service'):
            kwargs['service'] = self.service
        return AttrsLookup.getAttrsAsPacket(self, **kwargs)
############################################################################
class TourneyAttrsFactory(AttrsFactory):
    def __init__(self):
        AttrsFactory.__init__(self, moduleStr = 'tourneyattrs',
                              classPrefix = "TourneyAttrs", defaultClass = "AttrsLookup")
############################################################################
