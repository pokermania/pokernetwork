#
# -*- py-indent-offset: 4; coding: iso-8859-1 -*-
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
from pokernetwork.packets import PACKET_LOGIN, PACKET_AUTH
from pokernetwork import log as network_log
log = network_log.getChild("pokerauth")

class PokerAuth:

    def __init__(self, db, memcache, settings):
        self.log = log.getChild(self.__class__.__name__)
        self.db = db
        self.memcache = memcache
        self.type2auth = {}
        self.auto_create_account = settings.headerGet("/server/@auto_create_account") != 'no'

    def SetLevel(self, pkt_type, level):
        self.type2auth[pkt_type] = level

    def GetLevel(self, pkt_type):
        # return the minimum privilege level if not defined
        return self.type2auth.get(pkt_type,0) 

    def _authLogin(self,name,password):
        cursor = self.db.cursor()
        cursor.execute("SELECT serial, password, privilege FROM users WHERE name = %s",(name,))
        numrows = int(cursor.rowcount)
        serial = 0
        privilege = User.REGULAR
        valid_credentials = False
        if numrows <= 0 and password is not None:
            if self.auto_create_account:
                valid_credentials = True
                self.log.inform("user %s does not exist, create it", name)
                serial = self.userCreate(name, password)
                cursor.close()
            else:
                self.log.debug("user %s does not exist", name)
                cursor.close()
        elif numrows > 1:
            self.log.warn("more than one row for %s", name)
            cursor.close()
        else:
            (serial, password_sql, privilege) = cursor.fetchone()
            cursor.close()
            valid_credentials = (password_sql == password)

        if valid_credentials:
            return ( (serial, name, privilege), None )
        else:
#            if a user was found with this name, log the unsuccesful attempt
            if serial != 0:
                self.log.debug('password mismatch for %s', name)
            return ( False, "Invalid login or password" )
        
    def _authAuth(self,auth_token):
        serial = 0
        privilege = User.REGULAR
        valid_credentials = False
        memcache_serial = self.memcache.get(auth_token)
        if memcache_serial is not None:
            cursor = self.db.cursor()
            cursor.execute("SELECT serial, name, privilege FROM users WHERE serial = %s",(memcache_serial,))
            numrows = int(cursor.rowcount)
            if numrows == 1:
                valid_credentials = True
                (serial, name, privilege) = cursor.fetchone()
        if valid_credentials:
            return ( (serial, name, privilege), None )
        else:
            self.log.debug("auth mismatch: %s", auth_token)
            return ( False, "Invalid login or password" )
               
    def auth(self,auth_type,auth_args):
        if auth_type == PACKET_LOGIN:
            (name,password) = auth_args
            return self._authLogin(name, password)
        elif auth_type == PACKET_AUTH:
            (auth_token,) = auth_args
            return self._authAuth(auth_token)
        else:
            self.log.error("auth_type '%s' not implemented", auth_type)
            raise NotImplementedError()

    def userCreate(self, name, password):
        self.log.inform("creating user %s", name)
        cursor = self.db.cursor()
        cursor.execute(
           "INSERT INTO users (created, name, password) values (%s, %s, %s)",
           (seconds(), name, password)
        )
        serial = cursor.lastrowid
        self.log.inform("create user with serial %s", serial)
        cursor.execute("INSERT INTO users_private (serial) values (%s)", (serial,))
        cursor.close()
        return int(serial)

_get_auth_instance = None
def get_auth_instance(db, memcache, settings):
    global _get_auth_instance
    if _get_auth_instance == None:
        import imp
        script = settings.headerGet("/server/auth/@script")
        _get_auth_instance = lambda db, memcache, settings: PokerAuth(db, memcache, settings)
        if script:
            try:
                log.debug("get_auth_instance: trying to load: '%s'", script)
                module = imp.load_source("user_defined_pokerauth", script)
                get_instance = getattr(module, "get_auth_instance")
                log.debug("get_auth_instance: using custom implementation of get_auth_instance: %s", script)
                _get_auth_instance = get_instance
            except:
                log.warn("get_auth_instance: falling back on pokerauth.get_auth_instance, script not found: '%s'", script)
            
    return apply(_get_auth_instance, [db, memcache, settings])
