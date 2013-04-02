#
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2006, 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2008             Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#  Loic Dachary <loic@dachary.org>
#  Johan Euphrosine <proppy@aminche.com>
#  Henry Precheur <henry@precheur.org> (2004)
#  Cedric Pinson <mornifle@plopbyte.net> (2004-2006)

from twisted.python.runtime import seconds
from pokernetwork.user import User
from pokerpackets.packets import PACKET_LOGIN, PACKET_AUTH
from pokernetwork import log as network_log
log = network_log.get_child("pokerauth")

def _import(path):
    import sys
    __import__(path)
    return sys.modules[path]

class PokerAuth:

    log = log.get_child('PokerAuth')

    def __init__(self, db, memcache, settings):
        self.db = db
        self.memcache = memcache
        self.type2auth = {}
        self.auto_create_account = settings.headerGet("/server/@auto_create_account") == 'yes'

    def SetLevel(self, pkt_type, level):
        self.type2auth[pkt_type] = level

    def GetLevel(self, pkt_type):
        # return the minimum privilege level if not defined
        return self.type2auth.get(pkt_type, 0) 

    def _authLogin(self, name, password):
        c = self.db.cursor()
        try:
            c.execute("SELECT serial, password, privilege FROM users WHERE name = %s", (name,))
            if c.rowcount < 1:
                if self.auto_create_account:
                    serial = self.userCreate(name, password)
                    return (serial, name, User.REGULAR), None
                else:
                    self.log.debug("user does not exist.  name: %s", name)
                    return False, "Invalid login or password"
            if c.rowcount > 1:
                self.log.warn("multiple entries for user in database.  name: %s", name)
                return False, "Invalid login or password"

            serial, sql_password, privilege = c.fetchone()

            if sql_password != password:
                self.log.debug("invalid password in login attempt.  name: %s, serial: %d", name, serial)
                return False, "Invalid login or password"

            return (serial, name, privilege), None

        finally:
            c.close()

    def _authAuth(self, token):
        # memcache
        serial = self.memcache.get(token)
        if serial is None:
            self.log.debug("auth mismatch. token not found in memcache.  token: %s", token)
            return False, "Invalid session"
        serial = int(serial)

        # database
        c = self.db.cursor()
        try:
            c.execute("SELECT name, privilege FROM users WHERE serial = %s", (serial,))
            if c.rowcount < 1:
                self.log.debug("auth mismatch. user not found in database.  serial: %d", serial)
                return False, "Invalid session"
            if c.rowcount > 1:
                self.log.warn("multiple entries for user in database.  serial: %d", serial)
                return False, "Invalid session"
            name, privilege = c.fetchone()
            return (serial, name, privilege), None
        finally:
            c.close()
        
    def auth(self, auth_type, auth_args):
        if auth_type == PACKET_LOGIN:
            return self._authLogin(*auth_args)

        if auth_type == PACKET_AUTH:
            return self._authAuth(*auth_args)

        self.log.error("auth_type not implemented.  auth_type: %d", auth_type)
        raise NotImplementedError()

    def userCreate(self, name, password):
        c = self.db.cursor()
        try:
            c.execute("INSERT INTO users SET created = %s, name = %s, password = %s", (seconds(), name, password))
            serial = c.lastrowid
            c.execute("INSERT INTO users_private SET serial = %s", (serial,))
            self.log.inform("created user.  serial: %d, name: %s", serial, name)
            return serial
        finally:
            c.close()

_get_auth_instance = None
def get_auth_instance(db, memcache, settings):
    global _get_auth_instance
    if _get_auth_instance == None:
        script = settings.headerGet("/server/auth/@script")
        _get_auth_instance = lambda db, memcache, settings: PokerAuth(db, memcache, settings)
        if script:
            try:
                log.debug("get_auth_instance: trying to load: '%s'", script)
                get_instance = _import(script).get_auth_instance
                log.debug("get_auth_instance: using custom implementation of get_auth_instance: %s", script)
                _get_auth_instance = get_instance
            except ImportError, e:
                log.warn("get_auth_instance: falling back on pokerauth.get_auth_instance, script not found: '%s' (%s)", script, e)
            
    return apply(_get_auth_instance, [db, memcache, settings])
