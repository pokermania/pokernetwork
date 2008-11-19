#
# Copyright (C) 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                          24 rue vieille du temple, 75004 Paris
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
import sys
import os
sys.path.insert(0, "..")

import gtk
if os.path.exists(".libs"):
    sys.path.insert(0, ".libs")    
    _pokerinterface = __import__('_pokerinterface')
else:
    _pokerinterface = __import__('_pokerinterface' + sys.version[0] + '_' + sys.version[2])

from pokerui.pokerinterface import PokerInterface

class PokerInterface2D(PokerInterface):

    def __init__(self, settings):
        PokerInterface.__init__(self)
        self.verbose = settings.headerGetInt("/settings/@verbose")
        datadir = settings.headerGet("/settings/data/@path")
        _pokerinterface.init(callback = self.event,
                            datadir = datadir,
                            glade = datadir + "/interface/interface2d.glade",
                            verbose = self.verbose,
                            )
        self.width = settings.headerGetInt("/settings/screen/@width")
        self.height = settings.headerGetInt("/settings/screen/@height")
        window = gtk.Window()
        self.window = window
        window.set_default_size(self.width, self.height)
        window.set_title("Poker")
        window.set_name("lobby_window_root")
        window.set_icon_from_file(datadir + "/interface/pixmaps/poker2D_16.png")
        self.screen = gtk.Layout()
        self.screen.set_size(self.width, self.height)
        self.screen.set_name("screen")
        window.add(self.screen)
        window.show_all()
        
    def __del__(self):
        _pokerinterface.uninit()

    def command(self, *args):
        if self.verbose > 2: print "PokerInterface2D.command: " + str(args)
        _pokerinterface.command(self.screen, *args)
