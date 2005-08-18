#
# Copyright (C) 2004, 2005 Mekensleep
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
from pokerengine import config
from pokernetwork.version import version
import libxml2

class Config(config.Config):

    upgrades_repository = None
    verbose = 0

    def __init__(self, *args, **kwargs):
        config.Config.__init__(self, *args, **kwargs)
        self.version = version

    def loadFromString(self, string):
        self.path = "<string>"
        self.doc = libxml2.parseMemory(string, len(string))
        self.header = self.doc.xpathNewContext()

    def load(self, path):
        status = config.Config.load(self, path)
        if Config.upgrades_repository:
            if self.checkVersion("poker_network_version", version, Config.upgrades_repository):
                return status
            else:
                return False
        else:
            return status
