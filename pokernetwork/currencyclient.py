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
#  Loic Dachary <loic@gnu.org>
#
from types import *
from twisted.web import client

class FakeCurrencyClient:

    def __init__(self, parameters):
        self.parameters = parameters

    def mergeNote(self, note_a, note_b):
        result = list(note_a)
        result[3] += note_b[3]
        return result

    def changeNote(self, note):
        return note

class CurrencyClient:

    def __init__(self, parameters):
        self.parameters = parameters
        self.getPage = client.getPage

    def request(self, *args, **kwargs):
        url = ( kwargs.get('url') + "?command=" + kwargs.get('command', 'get') )
        args = ()
        for key in ('name', 'serial', 'value'):
            if kwargs.has_key(key): 
                arg = kwargs[key]
                args.append("%s=%s" % ( key, arg ))

        if kwargs.has_key('notes'):
            index = 0
            for (name, serial, value) in kwargs['notes']:
                args.append("name[%d]=%s" % ( index, name ) )
                args.append("serial[%d]=%s" % ( index, serial ) )
                args.append("value[%d]=%s" % ( index, value ) )
                index += 1
                
        if kwargs.has_key('note'):
            (name, serial, value) = kwargs['note']
            args.append("name=%s" % name )
            args.append("serial=%s" % serial )
            args.append("value=%s" % value )
                
        url += join("&", args)
        return self.getPage(url)

    def mergeNote(self, note_a, note_b):
        deferred = self.request(url = note_a[0], command = 'merge_notes', notes = ( note_a, note_b ))
        deferred.addCallback(self.mergeNoteResult)
        return deferred

    def mergedNoteResult(self, result):
        return result.split("\t")

    def changeNote(self, note):
        deferred = self.request(url = note[0], command = 'change_note', note = note)
        deferred.addCallback(self.changeNoteResult)
        return deferred

    changeNoteResult = mergedNoteResult
