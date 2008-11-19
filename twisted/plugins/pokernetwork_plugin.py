#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
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
#  Johan Euphrosine <proppy@aminche.com>
#

from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet

from pokernetwork import pokerserver

class Options(usage.Options):
    optParameters = [["config", "c", "/etc/poker-network/poker.server.xml", "The configuration file to use."]]

class PokerNetworkServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "pokerserver"
    description = "A pokerserver twisted multi-service."
    options = Options

    def makeService(self, options):
        return pokerserver.makeService(options["config"])

# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = PokerNetworkServiceMaker()
