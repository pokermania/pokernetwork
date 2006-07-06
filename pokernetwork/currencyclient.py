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
from twisted.internet import defer, reactor

class FakeCurrencyClient:

    def mergeNote(self, note_a, note_b):
        result = list(note_a)
        result[3] += note_b[3]
        d = defer.Deferred()
        reactor.callLater(0, lambda: d.callback(result))
        return d

    def changeNote(self, note):
        d = defer.Deferred()
        reactor.callLater(0, lambda: d.callback(note))
        return d

class CurrencyClient:

    def __init__(self):
        self.getPage = client.getPage

    def request(self, *args, **kwargs):
        args = [ kwargs.get('url') + "?command=" + kwargs.get('command', 'get_note') ]
        for key in ('name', 'serial', 'value'):
            if kwargs.has_key(key): 
                arg = kwargs[key]
                args.append("%s=%s" % ( key, arg ))

        if kwargs.has_key('notes'):
            index = 0
            for (url, serial, name, value) in kwargs['notes']:
                args.append("name[%d]=%s" % ( index, name ) )
                args.append("serial[%d]=%s" % ( index, serial ) )
                args.append("value[%d]=%s" % ( index, value ) )
                index += 1
                
        if kwargs.has_key('note'):
            (url, serial, name, value) = kwargs['note']
            args.append("name=%s" % name )
            args.append("serial=%s" % serial )
            args.append("value=%s" % value )
                
        return self.getPage("&".join(args))

    def mergeNotes(self, note_a, note_b):
        deferred = self.request(url = note_a[0], command = 'merge_notes', notes = ( note_a, note_b ))
        deferred.addCallback(self.mergedNotesResult)
        return deferred

    def mergedNotesResult(self, result):
        print result
        note = result.split("\t")
        return ( note[0], int(note[1]), note[2], int(note[3]) )

    def changeNote(self, note):
        deferred = self.request(url = note[0], command = 'change_note', note = note)
        deferred.addCallback(self.changeNoteResult)
        return deferred

    changeNoteResult = mergedNotesResult

    def getNote(self, url, value):
        deferred = self.request(url = url, command = 'get_note', value = value)
        deferred.addCallback(self.getNoteResult)
        return deferred

    getNoteResult = mergedNotesResult

    def checkNote(self, note):
        deferred = self.request(url = note[0], command = 'check_note', note = note)
        deferred.addCallback(self.checkNoteResult)
        return deferred

    checkNoteResult = mergedNotesResult
