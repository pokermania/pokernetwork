#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
from os.path import exists
import re
from traceback import print_exc, print_stack
import MySQLdb
from MySQLdb.cursors import DictCursor

class ExceptionDatabaseTooOld(Exception): pass
class ExceptionSoftwareTooOld(Exception): pass
class ExceptionUpgradeMissing(Exception): pass
class ExceptionUpgradeFailed(Exception): pass

from pokernetwork.version import Version, version

class PokerDatabase:

    def __init__(self, settings):
        self.verbose = settings.headerGetInt("/server/@verbose")
        self.parameters = settings.headerGetProperties("/server/database")[0]
        self.mysql_command = settings.headerGet("/server/database/@command")
        try:
            self.db = MySQLdb.connect(host = self.parameters["host"],
                                      user = self.parameters["user"],
                                      passwd = self.parameters["password"],
                                      db = self.parameters["name"])
        except:
            if self.parameters.has_key('root_user'):
                if self.verbose: print "connecting as root user '" + self.parameters["root_user"] + "'"
                db = MySQLdb.connect(host = self.parameters["host"],
                                     user = self.parameters["root_user"],
                                     passwd = self.parameters["root_password"])
                db.query("SHOW DATABASES LIKE '" + self.parameters["name"] + "'")
                result = db.store_result()
                #
                # It may be because the database does not exist
                #
                if result.num_rows() <= 0:
                    if self.verbose: print "creating database " + self.parameters["name"]
                    if not exists(self.parameters["schema"]):
                        db.close()
                        raise UserWarning, "PokerDatabase: schema " + self.parameters["schema"] + " file not found"
                    del result
                    db.query("CREATE DATABASE " + self.parameters["name"])
                    if self.verbose: print "populating database from " + self.parameters["schema"]
                    cmd = self.mysql_command + " --host='" + self.parameters["host"] + "' --user='" + self.parameters["root_user"] + "' --password='" + self.parameters["root_password"] + "' '" + self.parameters["name"] + "' < " + self.parameters["schema"]
                    if self.verbose: print cmd
                    os.system(cmd)
                db.select_db("mysql")
                #
                # Or because the user does not exist
                #
                try:
                    sql = "CREATE USER '" + self.parameters['user'] + "'@'%' IDENTIFIED BY '" + self.parameters['password'] + "'"
                    if self.verbose > 2: print sql
                    db.query(sql)
                    db.query("FLUSH PRIVILEGES")
                    if self.verbose: print "created database user " + self.parameters["user"]
                except:
                    if self.verbose > 2: print_exc()
                    if self.verbose: print "poker user '" + self.parameters["user"] + "' already exists"
                #
                # Or because the user does not have permission
                #
                db.query("GRANT ALL ON `" + self.parameters['name'] + "`.* TO '" + self.parameters['user'] + "'@'%'")
                db.query("FLUSH PRIVILEGES")
                db.close()
                if self.verbose: print "granted privilege to " + self.parameters["user"] + "' for database '" + self.parameters['name'] + "'"
            else:
                if self.verbose: print "root_user is not defined in the self.parameters, cannot create schema database"
            self.db = MySQLdb.connect(host = self.parameters["host"],
                                      user = self.parameters["user"],
                                      passwd = self.parameters["password"],
                                      db = self.parameters["name"])

        if self.verbose: print "PokerDatabase: Database connection to %s/%s open" % ( self.parameters["host"], self.parameters["name"] )
        self.db.query("SET AUTOCOMMIT = 1")
        self.version = Version(self.getVersionFromDatabase())
        if self.verbose: print "PokerDatabase: database version %s" % self.version

    def close(self):
        if hasattr(self, 'db'):
            self.db.close()

    def getVersionFromDatabase(self):
        try:
            cursor = self.cursor(DictCursor)
            cursor.execute("SELECT * FROM server")
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
            files = filter(lambda file: ".sql" == file[-4:], os.listdir(directory))
            files = map(lambda file: directory + "/" + file, files)
            parameters = self.parameters
            mysql = self.mysql_command + " -h '" + parameters['host'] + "' -u '" + parameters['user'] + "' --password='" + parameters['password'] + "' '" + parameters['name'] + "'"
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

