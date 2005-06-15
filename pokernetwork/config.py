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
from os.path import exists, expanduser, abspath
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
            tmppath = abspath(expanduser(dir and (dir + "/" + path) or path ))
            if exists(tmppath):
                self.path = tmppath
                break
        if self.path:
            self.doc = libxml2.parseFile(self.path)
            self.header = self.doc.xpathNewContext()
            return True
        else:
            print "Config::load: unable to find %s in directories %s" % ( path, self.dirs )
            return False

    def loadFromString(self, string):
        self.path = "<string>"
        self.doc = libxml2.parseMemory(string, len(string))
        self.header = self.doc.xpathNewContext()

    def save(self):
        if not self.path:
            print "unable to write back to %s" % self.path
            return
        self.doc.saveFile(self.path)
        
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
        
    def headerSet(self, name, value):
        results = self.header.xpathEval(name)
        results[0].setContent(value)
        
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
