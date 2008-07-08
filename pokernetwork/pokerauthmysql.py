#
# -*- py-indent-offset: 4; coding: iso-8859-1 -*-
#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2004, 2005, 2006 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
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
#  Loic Dachary <loic@gnu.org>
#  Johan Euphrosine <proppy@aminche.com>
#  Henry Precheur <henry@precheur.org> (2004)
#  Cedric Pinson <mornifle@plopbyte.net> (2004-2006)

from pokernetwork.user import User
from twisted.python.runtime import seconds
import MySQLdb

class PokerAuth:

    def __init__(self, db, settings):
        self.db = db
        self.type2auth = {}
        self.verbose = settings.headerGetInt("/server/@verbose")
        self.settings = settings
        self.parameters = self.settings.headerGetProperties("/server/auth")[0]
        self.auth_db = MySQLdb.connect(host = self.parameters["host"],
                                  port = int(self.parameters.get("port", '3306')),
                                  user = self.parameters["user"],
                                  passwd = self.parameters["password"],
                                  db = self.parameters["db"])

    def message(self, string):
        print "PokerAuth: " + string

    def error(self, string):
        self.message("*ERROR* " + string)
            
    def SetLevel(self, type, level):
        self.type2auth[type] = level

    def GetLevel(self, type):
        return self.type2auth.has_key(type) and self.type2auth[type]

    def auth(self, name, password):
        cursor = self.auth_db.cursor()
        cursor.execute("SELECT username, password, privilege FROM %s " % self.parameters["table"] +
                       "WHERE username = '%s'" % name)
        numrows = int(cursor.rowcount)
        serial = 0
        privilege = User.REGULAR
        if numrows <= 0:
                if self.verbose > 1:
                    self.message("user %s does not exist" % name)
                cursor.close()
                return ( False, "Invalid login or password" )
        elif numrows > 1:
            self.error("more than one row for %s" % name)
            cursor.close()
            return ( False, "Invalid login or password" )
        else:
            (serial, password_sql, privilege) = cursor.fetchone()
            cursor.close()
            if password_sql != password:
                self.message("password mismatch for %s" % name)
                return ( False, "Invalid login or password" )

        return ( (serial, name, privilege), None )

def get_auth_instance(db, settings):
    return PokerAuth(db, settings)
