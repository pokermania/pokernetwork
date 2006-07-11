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

class RealCurrencyClient:

    def __init__(self):
        self.getPage = client.getPage

    def request(self, *args, **kwargs):
        args = [ kwargs.get('url') + "?command=" + kwargs.get('command', 'get_note') ]
        for key in ('name', 'serial', 'value', 'transaction_id'):
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
                
        if kwargs.has_key('values'):
            index = 0
            for value in kwargs['values']:
                args.append("values[%d]=%d" % ( index, value ))
                index += 1
        url = "&".join(args)
        #print "RealCurrencyClient: " + url
        return self.getPage(url)

    def parseResult(self, result):
        notes = []
        for line in result.split("\n"):
            note = line.split("\t")
            if len(note) == 4:
                notes.append(( note[0], int(note[1]), note[2], int(note[3]) ),)
            else:
                print "RealCurrencyClient::parseResult ignore line: " + line
        return notes

    def mergeNotes(self, *args):
        deferred = self.request(url = args[0][0], command = 'merge_notes', notes = args)
        deferred.addCallback(self.parseResult)
        return deferred

    def meltNotes(self, *notes):
        values = sum(map(lambda note: note[3], notes))
        deferred = self.request(url = notes[0][0], command = 'merge_notes', notes = notes, values = [ values ])
        deferred.addCallback(self.parseResult)
        return deferred

    def changeNote(self, note):
        deferred = self.request(url = note[0], command = 'change_note', note = note)
        deferred.addCallback(self.parseResult)
        return deferred

    def getNote(self, url, value):
        deferred = self.request(url = url, command = 'get_note', value = value)
        deferred.addCallback(self.parseResult)
        return deferred

    def checkNote(self, note):
        deferred = self.request(url = note[0], command = 'check_note', note = note)
        deferred.addCallback(self.parseResult)
        return deferred

    def commit(self, url, transaction_id):
        return self.request(url = url, command = 'commit', transaction_id = transaction_id)
        
CurrencyClient = RealCurrencyClient

class FakeCurrencyClient:

    def __init__(self):
        self.serial = 1
        self.check_note_result = True
        self.commit_result = True
        
    def mergeNotes(self, *notes):
        self.serial += 1
        result = list(notes[0])
        result[1] = self.serial
        result[2] = "%040d" % self.serial
        result[3] = sum(map(lambda x: x[3], notes))
        d = defer.Deferred()
        reactor.callLater(0, lambda: d.callback([result]))
        return d

    def changeNote(self, note):
        self.serial += 1
        result = note.copy()
        result[1] = self.serial
        result[2] = "%040d" % self.serial
        d = defer.Deferred()
        reactor.callLater(0, lambda: d.callback(result))
        return d

    def _buildNote(self, url, value):
        self.serial += 1
        name = "%040d" % self.serial
        return ( url, self.serial, name, value )

    def getNote(self, url, value):
        note = self._buildNote(url, value)
        d = defer.Deferred()
        reactor.callLater(0, lambda: d.callback(note))
        return d

    def checkNote(self, note):
        if self.check_note_result:
            result = note
        else:
            result = failure.Failure()
        d = defer.Deferred()
        reactor.callLater(0, lambda: d.callback(result))
        return d

    def commit(self, url, transaction_id):
        if self.commit_result:
            result = "OK"
        else:
            result = failure.Failure()
        d = defer.Deferred()
        reactor.callLater(0, lambda: d.callback(result))
        return d

