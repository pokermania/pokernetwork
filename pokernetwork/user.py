#
# Copyright (C) 2004 Mekensleep
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Henry Precheur <henry@precheur.org>
#  Loic Dachary <loic@gnu.org>
#
from re import match

def checkName(name):
    if not match("^[a-zA-Z][a-zA-Z0-9]{4,9}$", name):
        if len(name) > 10:
            return (False, "login name must be at most 10 characters long")
        elif len(name) < 5:
            return (False, "login name must be at least 5 characters long")
        elif not match("^[a-zA-Z]", name):
            return (False, "login name must start with a letter")
        else:
            return (False, "login name must be all letters and digits")

    return (True, None)

def checkPassword(password):
    if not match("^[a-zA-Z0-9]{5,9}$", password):
        if len(password) > 10:
            return (False, "password must be at most 10 characters long")
        elif len(password) < 5:
            return (False, "password must be at least 5 characters long")
        else:
            return (False, "password must be all letters and digits")

    return (True, None)

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

    def checkNameAndPassword(self, name, password):
        status = checkName(name)
        if status[0]:
            return checkPassword(password)
        else:
            return status

    def __str__(self):
        return "serial = %d, name = %s, url = %s, outfit = %s, privilege = %d" % ( self.serial, self.name, self.url, self.outfit, self.privilege )
