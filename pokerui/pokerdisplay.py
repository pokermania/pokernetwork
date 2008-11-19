#
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
#
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
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
# Authors:
#  Loic Dachary <loic@dachary.org>
#
#

from pokernetwork.packets import PACKET_QUIT
from twisted.internet import reactor

class PokerDisplay:
    def __init__(self, *args, **kwargs):
        self.config = kwargs['config']
        self.settings = kwargs['settings']
        self.factory = kwargs['factory']
        self.protocol = None
        self.renderer = None
        self.animations = None
        self.finished = False

    def init(self):
        pass

    def setProtocol(self, protocol):
        self.protocol = protocol
        if self.animations: self.animations.setProtocol(protocol)

    def unsetProtocol(self):
        if self.animations: self.animations.unsetProtocol()
        self.protocol = None

    def setRenderer(self, renderer):
        self.renderer = renderer

    def finish(self):
        if self.finished:
            return False
        else:
            self.finished = True
            return True

    def render(self, packet):
        if packet.type == PACKET_QUIT:
            reactor.stop()
            return

    def showProgressBar(self):
        pass
    
    def hideProgressBar(self):
        print "\n"

    def tickProgressBar(self, ratio, message):
        if message: print "\n" + message + " "
        if ratio > 0: print str(int(ratio * 100)) + "% "

    def setSoundEnabled(self, yesno):
        return yesno and 1 or 0;
