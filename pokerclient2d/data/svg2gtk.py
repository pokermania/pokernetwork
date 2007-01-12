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
import string

class SVG2Glade(ContentHandler):
    def __init__(self, string):
        self.formats = []
        self.tuples = []
        parseString(string, self)
    def __str__(self):
        return string.join(map(lambda format, tuple: format % tuple, self.formats, self.tuples), '')
    def startElement(self, name, attrs):
        if name == "svg":
            self.formats.append('<glade-interface><widget class="GtkWindow" id="%s"><property name="width_request">%s</property><property name="height_request">%s</property><child><widget class="GtkFixed" id="%s_fixed">')
            self.tuples.append((attrs['id'], attrs['width'], attrs['height'], attrs['id']))
        elif name == "image":
            self.formats.append('<child><widget class="GtkButton" id="%s"><property name="width_request">%s</property><property name="height_request">%s</property><property name="label"/><signal name="clicked" handler="on_%s_clicked"/></widget><packing><property name="x">%s</property><property name="y">%s</property></packing></child>')
            self.tuples.append((attrs['id'], attrs['width'], attrs['height'], attrs['id'], attrs['x'], attrs['y']))
    def endElement(self, name):
        if name == "svg":
            self.formats.append('</widget></child></widget></glade-interface>')
            self.tuples.append(())

class SVG2Rc(ContentHandler):
    def __init__(self, string):
        self.root = ""
        self.formats = []
        self.tuples = []
        parseString(string, self)
    def __str__(self):
        return string.join(map(lambda format, tuple: format % tuple, self.formats, self.tuples), '')
    def startElement(self, name, attrs):
        if name == "svg":
            self.root = attrs['id']
        elif name == "image":
            self.formats.append('style "%s_style" {engine "pixmap" {image {function = BOX file = "%s"}}} widget "*%s*%s" style "%s_style"\n')
            self.tuples.append((attrs['id'], attrs['xlink:href'], self.root, attrs['id'], attrs['id']))

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        if sys.argv[1] == "--glade":
            print SVG2Glade(sys.stdin.read())
        elif sys.argv[1] == "--gtkrc":
            print SVG2Rc(sys.stdin.read())
