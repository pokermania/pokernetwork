#
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
