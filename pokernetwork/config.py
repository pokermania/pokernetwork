#
# Copyright (C) 2004 Mekensleep
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#
from os.path import exists, expanduser
import libxml2
import re

class Config:
    def __init__(self, dirs):
        self.path = None
        self.header = None
        self.doc = None
        self.dirs = [ expanduser(dir) for dir in dirs ]

    def load(self, path):
        for dir in self.dirs:
            abspath = expanduser(dir and (dir + "/" + path) or path )
            if exists(abspath):
                self.path = abspath
                break
        if self.path:
            self.doc = libxml2.parseFile(self.path)
            self.header = self.doc.xpathNewContext()
            return True
        else:
            print "Config::load: unable to find %s in directories %s" % ( path, self.dirs )
            return False

    def headerGetList(self, name):
        result = self.header.xpathEval(name)
        return [o.content for o in result]

    def headerGetInt(self, name):
        string = self.headerGet(name)
        if re.match("[0-9]+$", string):
            return int(string)
        else:
            return 0
        
    def headerGet(self, name):
        results = self.header.xpathEval(name)
        return results and results[0].content or ""
        
    def headerGetProperties(self, name):
        results = []
        for node in self.header.xpathEval(name):
            results.append(self.headerNodeProperties(node))
        return results

    def headerNodeProperties(self, node):
        result = {}
        property = node.properties
        while property != None:
            result[property.name] = property.content
            property = property.next
        return result
