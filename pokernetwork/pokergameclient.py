# -*- py-indent-offset: 4; coding: iso-8859-1; mode: python -*-
#
# Copyright (C) 2007 Loic Dachary <loic@dachary.org>
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
from pokerengine.pokergame import PokerGameClient

class PokerNetworkGameClient(PokerGameClient):
    SERIAL_IN_POSITION = 0
    POSITION_OBSOLETE = 1

    def __init__(self, url, dirs):
        PokerGameClient.__init__(self, url, dirs)
        self.level_skin = ""
        self.currency_serial = 0
        self.history_index = 0
        self.position_info = [ 0, 0 ]
