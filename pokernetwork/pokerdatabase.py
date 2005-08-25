#
# -*- coding: iso-8859-1 -*-
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
#  Loic Dachary <loic@gnu.org>
#
import os
import re
import MySQLdb
from MySQLdb.cursors import DictCursor

class ExceptionDatabaseTooOld(Exception): pass
class ExceptionSoftwareTooOld(Exception): pass
class ExceptionUpgradeMissing(Exception): pass
class ExceptionUpgradeFailed(Exception): pass

from pokernetwork.version import Version, version

class PokerDatabase:

    def __init__(self, settings):
        parameters = settings.headerGetProperties("/server/database")[0]
        self.db = MySQLdb.connect(host = parameters["host"],
                                  user = parameters["user"],
                                  passwd = parameters["password"],
                                  db = parameters["name"])
        self.parameters = parameters
        print "Database connection to %s/%s open" % ( parameters["host"], parameters["name"] )        
        self.verbose = settings.headerGetInt("/server/@verbose")
        self.version = Version(self.getVersionFromDatabase())
        if self.verbose: print "PokerDatabase: database version %s" % self.version

    def getVersionFromDatabase(self):
        try:
            cursor = self.cursor(DictCursor)
            cursor.execute("select * from server")
            row = cursor.fetchone()
            version = row['version']
            cursor.close()
            return version
        except:
            if self.verbose: print "PokerDatabase: no server table, assuming version 1.0.5"
            return "1.0.5"

    def setVersionInDatabase(self, version):
        cursor = self.cursor()
        sql = "update server set version = '%s'" % version
        cursor.execute(sql)
        if cursor.rowcount != 1:
            raise ExceptionUpgradeFailed, "%s: changed %d rows, expected exactly one" % ( sql, cursor.rowcount )
        cursor.close()
        
    def checkVersion(self):
        if version != self.version:
            print "PokerDatabase: database version %s must be the same as the poker-network version %s" % ( self.version, version )
            if version > self.version:
                print "PokerDatabase: upgrade the database with pokerdatabaseupgrade"
                raise ExceptionDatabaseTooOld
            else:
                print "ERROR: PokerDatabase: upgrade poker-network to version %s or better" % self.version
                raise ExceptionSoftwareTooOld

    def upgrade(self, directory, dry_run):
        try:
            self.checkVersion()
        except ExceptionDatabaseTooOld:
            files = filter(lambda file: ".sql" in file, os.listdir(directory))
            files = map(lambda file: directory + "/" + file, files)
            parameters = self.parameters
            mysql = "mysql -h '" + parameters['host'] + "' -u '" + parameters['user'] + "' --password='" + parameters['password'] + "' '" + parameters['name'] + "'"
            for file in self.version.upgradeChain(version, files):
                print "PokerDatabase: apply " + file
                if not dry_run:
                    if os.system(mysql + " < " + file):
                        raise ExceptionUpgradeFailed, "upgrade failed"
            print "PokerDatabase: upgraded database to version %s" % version
            if not dry_run:
                self.setVersionInDatabase(version)
                self.version = Version(self.getVersionFromDatabase())

    def getVersion(self):
        return self.version

    def cursor(self, *args, **kwargs):
        return self.db.cursor(*args, **kwargs)

