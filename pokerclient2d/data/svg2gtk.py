#!/usr/bin/python
# -*- mode: python -*-
#
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
#  Johan Euphrosine <johan@mekensleep.com>
#

from xml.sax import parseString
from xml.sax.handler import ContentHandler
from xml.dom import minidom
from xml.xpath import Evaluate

import string

class SVG2Glade(ContentHandler):
    def __init__(self, string):
        self.formats = []
        self.tuples = []
        self.doc = minidom.parseString(string)
        parseString(string, self)
    def __str__(self):
        return string.join(map(lambda format, tuple: format % tuple, self.formats, self.tuples), '')
    def startElement(self, name, attrs):
        format = '<child><widget class="GtkButton" id="%s"><property name="width_request">%s</property><property name="height_request">%s</property><property name="label"/><signal name="clicked" handler="on_%s_clicked"/></widget><packing><property name="x">%s</property><property name="y">%s</property></packing></child>'
        if name == "svg":
            self.formats.append('<glade-interface><widget class="GtkWindow" id="%s"><property name="width_request">%s</property><property name="height_request">%s</property><child><widget class="GtkFixed" id="%s_fixed">')
            self.tuples.append((attrs['id'], attrs['width'], attrs['height'], attrs['id']))
        elif name == "image":
            self.formats.append(format)
            self.tuples.append((attrs['id'], attrs['width'], attrs['height'], attrs['id'], attrs['x'], attrs['y']))
        elif name == "use":
            groupId = attrs['id']
            href = attrs['xlink:href']
            nodePath = href[1:]
            nodes = Evaluate('//g[@id="'+nodePath+'"]/image', self.doc)
            for node in nodes:
                nodeId = node.attributes['id'].value
                (groupPrefix, groupSuffix) = groupId.split('_')
                (nodePrefix, nodeSuffix) = nodeId.split('_')
                nodeId = nodeId.replace(nodeSuffix, groupSuffix)
                self.formats.append(format)
                self.tuples.append((nodeId, node.attributes['width'].value, node.attributes['height'].value, nodeId, node.attributes['x'].value, node.attributes['y'].value))
                
    def endElement(self, name):
        if name == "svg":
            self.formats.append('</widget></child></widget></glade-interface>')
            self.tuples.append(())

class SVG2Rc(ContentHandler):
    def __init__(self, string):
        self.root = ""
        self.formats = []
        self.tuples = []
        self.doc = minidom.parseString(string)
        parseString(string, self)
    def __str__(self):
        return string.join(map(lambda format, tuple: format % tuple, self.formats, self.tuples), '')
    def startElement(self, name, attrs):
        format = 'style "%s_style" {engine "pixmap" {image {function = BOX file = "%s"}}} widget "*%s*%s" style "%s_style"\n'
        if name == "svg":
            self.root = attrs['id']
        elif name == "image":
            self.formats.append(format)
            self.tuples.append((attrs['id'], attrs['xlink:href'], self.root, attrs['id'], attrs['id']))           
        elif name == "use":
            groupId = attrs['id']
            href = attrs['xlink:href']
            nodePath = href[1:]
            nodes = Evaluate('//g[@id="'+nodePath+'"]/image', self.doc)
            for node in nodes:
                nodeId = node.attributes['id'].value
                (groupPrefix, groupSuffix) = groupId.split('_')
                (nodePrefix, nodeSuffix) = nodeId.split('_')
                nodeId = nodeId.replace(nodeSuffix, groupSuffix)
                self.formats.append(format)
                self.tuples.append((nodeId, node.attributes['xlink:href'].value, self.root, nodeId, nodeId))           
 
 
if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        if sys.argv[1] == "--glade":
            print SVG2Glade(sys.stdin.read())
        elif sys.argv[1] == "--gtkrc":
            print SVG2Rc(sys.stdin.read())
