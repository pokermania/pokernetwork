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

class PokerAuth:

    def __init__(self, db, settings):
        self.db = db
        self.type2auth = {}
        self.verbose = settings.headerGetInt("/server/@verbose")
        self.auto_create_account = settings.headerGet("/server/@auto_create_account") != 'no'
        currency = settings.headerGetProperties("/server/currency")
        if len(currency) > 0:
            self.currency = currency[0]
        else:
            self.currency = None

    def message(self, string):
        print "PokerAuth: " + string

    def error(self, string):
        self.message("*ERROR* " + string)
            
    def SetLevel(self, type, level):
        self.type2auth[type] = level

    def GetLevel(self, type):
        return self.type2auth.has_key(type) and self.type2auth[type]

    def auth(self, name, password):
        cursor = self.db.cursor()
        cursor.execute("SELECT serial, password, privilege FROM users "
                       "WHERE name = '%s'" % name)
        numrows = int(cursor.rowcount)
        serial = 0
        privilege = User.REGULAR
        if numrows <= 0:
            if self.auto_create_account:
                if self.verbose > 1:
                    self.message("user %s does not exist, create it" % name)
                serial = self.userCreate(name, password)
                cursor.close()
            else:
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

    def userCreate(self, name, password):
        if self.verbose:
            self.message("creating user %s" % name)
        cursor = self.db.cursor()
        cursor.execute("INSERT INTO users (created, name, password) values (%d, '%s', '%s')" %
                       (seconds(), name, password))
        #
        # Accomodate for MySQLdb versions < 1.1
        #
        if hasattr(cursor, "lastrowid"):
            serial = cursor.lastrowid
        else:
            serial = cursor.insert_id()
        if self.verbose:
            self.message("create user with serial %s" % serial)
        cursor.execute("INSERT INTO users_private (serial) values ('%d')" % serial)
        if self.currency:
            cursor.execute("INSERT INTO user2money (user_serial, currency_serial, amount) values (%d, %s, %s)" % ( serial, self.currency['serial'], self.currency['amount']))
        cursor.close()
        return int(serial)

_get_auth_instance = None
def get_auth_instance(db, settings):
    global _get_auth_instance
    if _get_auth_instance == None:
        verbose = settings.headerGet("/server/@verbose")
        def message(string):
            print "PokerAuth: " + string
        import imp
        script = settings.headerGet("/server/auth/@script")
        try:
            if verbose > 0: message("get_auth_instance: trying to load: '%s'" % script)
            module = imp.load_source("user_defined_pokerauth", script)
            get_instance = getattr(module, "get_auth_instance")
            if verbose > 0: message("get_auth_instance: using custom implementation of get_auth_instance: %s" % script)
            _get_auth_instance = get_instance
        except:
            if verbose > 0: message("get_auth_instance: falling back on pokerauth.get_auth_instance, script not found: '%s'" % script)
            _get_auth_instance = lambda db, settings: PokerAuth(db, settings)
    return apply(_get_auth_instance, [db, settings])
