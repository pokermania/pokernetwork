#
# Copyright (C) 2005, 2006 Mekensleep
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
#  Johan Euphrosine <proppy@aminche.com>
#

def glade_interface(glade_string):
    return '<glade-interface>%s</glade-interface>' % glade_string
def glade_child(glade_string):
    return '<child>%s</child>' % glade_string
def glade_widget(type, id, glade_string):
    return '<widget class="%s" id="%s">%s</widget>' % (type, id, glade_string)
def glade_property(name, value):      
    return '<property name="%s">%s</property>' % (name, value)
def glade_signal(name, handler):
    return '<signal name="%s" handler="%s"/>' % (name, handler)
def glade_packing(glade_string):
    return '<packing>%s</packing>' % (glade_string)

def rc_style(name, rc_string):
    return 'style "%s_style" {%s}' % (name, rc_string)
def rc_engine(name, rc_string):
    return 'engine "%s" {%s}' % (name, rc_string)
def rc_image(file, state = None):
    return 'image {function = BOX file = "%s"}' % file
def rc_widget(name):
    return 'widget "*%s" style "%s_style"' % (name, name)
