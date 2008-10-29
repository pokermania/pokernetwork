#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
