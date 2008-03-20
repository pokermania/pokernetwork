#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
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
import sys
import StringIO

messages_out = []

def redirect_messages(a_class):
    stdout = sys.stdout
    sys.stdout = StringIO.StringIO()
    class F(a_class):
        def __init__(self, *args, **kwargs):
            self._prefix = 'P'
            self.prefix = 'P'
            self.id = 1
            self.name = 'name'
    F().message('')
    sys.stdout = stdout
    a_class.message = lambda self, string: messages_out.append(string)
    
def silence_all_messages():
    from pokernetwork import pokerservice
    redirect_messages(pokerservice.PokerService)
    redirect_messages(pokerservice.PokerXML)
    redirect_messages(pokerservice.PokerAuth)
    from pokernetwork import pokerlock
    redirect_messages(pokerlock.PokerLock)
    from pokernetwork import pokeravatar
    redirect_messages(pokeravatar.PokerAvatar)
    from pokernetwork import pokerexplain
    redirect_messages(pokerexplain.PokerExplain)
    from pokernetwork import pokertable
    redirect_messages(pokertable.PokerTable)
    from pokernetwork import pokercashier
    redirect_messages(pokercashier.PokerCashier)
    from pokernetwork import pokerdatabase
    redirect_messages(pokerdatabase.PokerDatabase)
    from pokerengine import pokergame
    redirect_messages(pokergame.PokerGame)
    from pokerengine import pokertournament
    redirect_messages(pokertournament.PokerTournament)
