#
# Copyright (C) 2006, 2007 Loic Dachary <loic@dachary.org>
# Copyright (C) 2006 Mekensleep
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
def silence_all_messages():
    from pokernetwork import pokerservice
    pokerservice.PokerService.message = lambda self, string: True
    pokerservice.PokerXML.message = lambda self, string: True
    pokerservice.PokerAuth.message = lambda self, string: True
    from pokernetwork import pokerlock
    pokerlock.PokerLock.message = lambda self, string: True
    from pokernetwork import pokeravatar
    pokeravatar.PokerAvatar.message = lambda self, string: True
    from pokernetwork import pokertable
    pokertable.PokerTable.message = lambda self, string: True
    from pokernetwork import pokercashier
    pokercashier.PokerCashier.message = lambda self, string: True
    from pokernetwork import pokerdatabase
    pokerdatabase.PokerDatabase.message = lambda self, string: True
    from pokerengine import pokergame
    pokergame.PokerGame.message = lambda self, string: True
    from pokerengine import pokertournament
    pokertournament.PokerTournament.message = lambda self, string: True
