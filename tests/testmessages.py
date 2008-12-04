#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
# Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
#                    24 rue vieille du temple, 75004 Paris
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
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
import sys, os

classes = []

from pokerui import pokerinteractor
classes.append(pokerinteractor.PokerInteractor)
from pokerui import pokerrenderer
classes.append(pokerrenderer.PokerRenderer)
classes.append(pokerrenderer.PokerInteractors)
from pokernetwork import currencyclient
classes.append(currencyclient.FakeCurrencyClient)
from pokernetwork import pokerchildren
classes.append(pokerchildren.PokerChild)
from pokernetwork import client
classes.append(client.UGAMEClientFactory)
from pokernetwork import protocol
classes.append(protocol.UGAMEProtocol)
from pokernetwork import pokerservice
classes.append(pokerservice.PokerService)
classes.append(pokerservice.PokerXML)
from pokernetwork import pokerauth
classes.append(pokerauth.PokerAuth)
from pokernetwork import pokerlock
classes.append(pokerlock.PokerLock)
from pokernetwork import pokeravatar
classes.append(pokeravatar.PokerAvatar)
from pokernetwork import pokerexplain
classes.append(pokerexplain.PokerExplain)
from pokernetwork import pokertable
classes.append(pokertable.PokerTable)
from pokernetwork import pokercashier
classes.append(pokercashier.PokerCashier)
from pokernetwork import pokerdatabase
classes.append(pokerdatabase.PokerDatabase)
from pokerengine import pokergame
classes.append(pokergame.PokerGame)
from pokerengine import pokertournament
classes.append(pokertournament.PokerTournament)
from pokernetwork import upgrade
classes.append(upgrade.CheckClientVersion)
classes.append(upgrade.Upgrader)
from pokernetwork import pokersite
classes.append(pokersite.PokerResource)
classes.append(pokersite.PokerImageUpload)
classes.append(pokersite.PokerAvatarResource)
classes.append(pokersite.PokerSite)
from pokernetwork import userstats
classes.append(userstats.UserStatsFactory)
classes.append(userstats.UserStatsRankPercentileAccessor)
classes.append(userstats.UserStatsRankPercentileLookup)
from pokernetwork import attrpack
classes.append(attrpack.AttrsFactory)
classes.append(attrpack.AttrsAccessor)
classes.append(attrpack.AttrsLookup)
# that does not work because it gets imported in two different ways
#from pokernetwork import proxyfilter
#classes.append(proxyfilter.ProxyClientFactory)

from twisted.internet import defer

verbose = int(os.environ.get('VERBOSE_T', '-1'))

#
# for coverage purpose, make sure all message functions
# are called at least once
#
def call_messages():
    import StringIO
    for a_class in classes:
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
call_messages()

messages_needle = ''
messages_grep_hit = None
def grep_output(needle):
    messages_grep_hit = defer.Deferred()
    messages_needle = needle
    return messages_grep_hit

def messages_grep(haystack):
    if haystack.find(messages_needle):
        hit = messages_grep_hit
        messages_grep_hit = None
        hit.callback(haystack)
        
def messages_append(string):
    if verbose > 3:
        print "OUTPUT: " + string
    if not hasattr(string, '__str__'):
        raise Exception, "Message comes in as non-stringifiable object" 
    string = string.__str__()
    messages_out.append(string)
    messages_grep(string)

class2message = {
    pokergame.PokerGame: lambda self, string: messages_append(self.prefix + "[PokerGame " + str(self.id) + "] " + string)
    }
messages_out = []

def redirect_messages(a_class):
    if not hasattr(a_class, 'orig_message'):
        a_class.orig_message = [ ]
    a_class.orig_message.append(a_class.message)
    a_class.message = class2message.get(a_class, lambda self, string: messages_append(string))
    
def silence_all_messages():
    messages_out = []
    for a_class in classes:
        redirect_messages(a_class)

def restore_all_messages():
    for a_class in classes:
        a_class.message = a_class.orig_message.pop()

def search_output(what):
    if verbose > 1:
        print "search_output: " + what
    for message in messages_out:
        if message.find(what) >= 0:
            return True
        if verbose > 1:
            print "\tnot in " + message
    return False

def clear_all_messages():
    global messages_out
    messages_out = []

def get_messages():
    return messages_out
