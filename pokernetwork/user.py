#
# Copyright (C) 2004, 2005 Mekensleep
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
#  Henry Precheur <henry@precheur.org>
#  Loic Dachary <loic@gnu.org>
#
from re import match

NAME_TOO_SHORT = 1
NAME_TOO_LONG = 2
NAME_MUST_START_WITH_LETTER = 3
NAME_NOT_ALNUM = 4
PASSWORD_TOO_SHORT = 5
PASSWORD_TOO_LONG = 6
PASSWORD_NOT_ALNUM = 7
INVALID_EMAIL = 8
NAME_ALREADY_EXISTS = 9
EMAIL_ALREADY_EXISTS = 10
SERVER_ERROR = 11

NAME_LENGTH_MAX = 20
NAME_LENGTH_MIN = 5

PASSWORD_LENGTH_MAX = 15
PASSWORD_LENGTH_MIN = 5

def checkName(name):
    if not match("^[a-zA-Z][a-zA-Z0-9]{" + str(NAME_LENGTH_MIN - 1) + "," + str(NAME_LENGTH_MAX - 1) + "}$", name):
        if len(name) > NAME_LENGTH_MAX:
            return (False, NAME_TOO_LONG, "login name must be at most %d characters long" % NAME_LENGTH_MAX)
        elif len(name) < NAME_LENGTH_MIN:
            return (False, NAME_TOO_SHORT, "login name must be at least %d characters long" % NAME_LENGTH_MIN)
        elif not match("^[a-zA-Z]", name):
            return (False, NAME_MUST_START_WITH_LETTER, "login name must start with a letter")
        else:
            return (False, NAME_NOT_ALNUM, "login name must be all letters and digits")

    return (True, None, None)

def checkPassword(password):
    if not match("^[a-zA-Z0-9]{" + str(PASSWORD_LENGTH_MIN) + "," + str(PASSWORD_LENGTH_MAX) + "}$", password):
        if len(password) > PASSWORD_LENGTH_MAX:
            return (False, PASSWORD_TOO_LONG, "password must be at most %d characters long" % PASSWORD_LENGTH_MAX)
        elif len(password) < PASSWORD_LENGTH_MIN:
            return (False, PASSWORD_TOO_SHORT, "password must be at least %d characters long" % PASSWORD_LENGTH_MIN)
        else:
            return (False, PASSWORD_NOT_ALNUM, "password must be all letters and digits")

    return (True, None, None)

def checkNameAndPassword(name, password):
    status = checkName(name)
    if status[0]:
        return checkPassword(password)
    else:
        return status

class User:
    REGULAR = 1
    ADMIN = 2

    def __init__(self, serial = 0):
        self.serial = serial
        self.name = "anonymous"
        self.url = "random"
        self.outfit = "random"
        self.privilege = None

    def logout(self):
        self.serial = 0
        self.name = "anonymous"
        self.url = "random"
        self.outfit = "random"
        self.privilege = None
        
    def isLogged(self):
        return not self.serial == 0

    def hasPrivilege(self, privilege):
        if not privilege:
            return True
        
        return self.privilege >= privilege

    def __str__(self):
        return "serial = %d, name = %s, url = %s, outfit = %s, privilege = %d" % ( self.serial, self.name, self.url, self.outfit, self.privilege )
