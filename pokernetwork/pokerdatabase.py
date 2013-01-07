#
# -*- py-indent-offset: 4; coding: utf-8; mode: python -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
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
#
import os
from os.path import exists
import MySQLdb
from MySQLdb.cursors import DictCursor
import subprocess

from pokernetwork import log as network_log
log = network_log.get_child('pokerdatabase')

class ExceptionDatabaseTooOld(Exception): pass
class ExceptionSoftwareTooOld(Exception): pass
class ExceptionUpgradeMissing(Exception): pass
class ExceptionUpgradeFailed(Exception): pass

from pokernetwork.version import Version, version

class PokerDatabase:

    log = log.get_child('PokerDatabase')

    def __init__(self, settings):
        self.parameters = settings.headerGetProperties("/server/database")[0]
        self.mysql_command = settings.headerGet("/server/database/@command")
        try:
            self.db = MySQLdb.connect(
                host = self.parameters["host"],
                port = int(self.parameters.get("port", '3306')),
                user = self.parameters["user"],
                passwd = self.parameters["password"],
                db = self.parameters["name"]
            )
            self.log.debug("MySQL server version is %s", self.db.get_server_info())
        except Exception, login_exception:
            self.log.warn("could not login as user '%s': %s",(self.parameters['user'], login_exception))
            if 'root_user' in self.parameters:
                self.log.inform("connection as root user '%s'", self.parameters['root_user'])
                db = MySQLdb.connect(
                    host = self.parameters["host"],
                    port = int(self.parameters.get("port", '3306')),
                    user = self.parameters["root_user"],
                    passwd = self.parameters["root_password"]
                )
                self.log.inform("MySQL server version is %s", db.get_server_info())
                if int(db.get_server_info().split('.')[0]) < 5:
                    raise UserWarning, "PokerDatabase: MySQL server version is " + db.get_server_info() + " but version >= 5.0 is required"
                db.query("SHOW DATABASES LIKE '" + self.parameters["name"] + "'")
                result = db.store_result()
                #
                # It may be because the database does not exist
                #
                if result.num_rows() <= 0:
                    self.log.inform("creating database %s", self.parameters["name"])
                    if not exists(self.parameters["schema"]):
                        db.close()
                        raise UserWarning, "PokerDatabase: schema " + self.parameters["schema"] + " file not found"
                    del result
                    db.query("CREATE DATABASE " + self.parameters["name"])
                    self.log.inform("populating database from %s", self.parameters['schema'])
                    cmd = self.mysql_command + " --host='" + self.parameters["host"] + "' --user='" + self.parameters["root_user"] + "' --password='" + self.parameters["root_password"] + "' '" + self.parameters["name"] + "' < " + self.parameters["schema"]
                    self.log.inform("%s", cmd)
                    os.system(cmd)
                db.select_db("mysql")
                #
                # Or because the user does not exist
                #
                try:
                    sql = "CREATE USER '" + self.parameters['user'] + "'@'%' IDENTIFIED BY '" + self.parameters['password'] + "'"
                    self.log.debug("%s", sql)
                    db.query(sql)
                    sql = "CREATE USER '" + self.parameters['user'] + "'@'localhost' IDENTIFIED BY '" + self.parameters['password'] + "'"
                    self.log.debug("%s", sql)
                    db.query(sql)
                    db.query("FLUSH PRIVILEGES")
                    self.log.debug("create database user '%s'", self.parameters['user'])
                except:
                    self.log.inform("poker user '%s' already exists", self.parameters['user'], exc_info=1)
                #
                # Or because the user does not have permission
                #
                db.query("GRANT ALL ON `" + self.parameters['name'] + "`.* TO '" + self.parameters['user'] + "'@'%'")
                db.query("FLUSH PRIVILEGES")
                db.close()
                self.log.inform("granted privilege to '%s' for database '%s'", self.parameters['user'], self.parameters['name'])
            else:
                self.log.error("root_user is not defined in the self.parameters, cannot create schema database")
            self.db = MySQLdb.connect(
                host = self.parameters["host"],
                port = int(self.parameters.get("port", '3306')),
                user = self.parameters["user"],
                passwd = self.parameters["password"],
                db = self.parameters["name"]
            )

        self.log.debug("Database connection to %s/%s open", self.parameters['host'], self.parameters['name'])
        self.db.autocommit(True)
        self.version = Version(self.getVersionFromDatabase())
        self.log.inform("Database version %s", self.version)

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
            self.log.error("no server table, assuming version 1.0.5")
            return "1.0.5"

    def setVersionInDatabase(self, version):
        cursor = self.cursor()
        sql = "update server set version = '%s'" % version
        cursor.execute(sql)
        if cursor.rowcount not in (0, 1):
            raise ExceptionUpgradeFailed, "%s: changed %d rows, expected one or zero" % ( sql, cursor.rowcount )
        cursor.close()
        
    def checkVersion(self):
        if version != self.version:
            self.log.warn("database version %s must be the same as the poker-network version %s", self.version, version)
            if version > self.version:
                self.log.warn("upgrade the database with pokerdatabaseupgrade")
                raise ExceptionDatabaseTooOld
            else:
                self.log.warn("upgrade poker-network to version %s or better", self.version)
                raise ExceptionSoftwareTooOld

    def upgrade(self, directory, dry_run):
        try:
            self.checkVersion()
        except ExceptionDatabaseTooOld:
            files = ["%s/%s" % (directory,f) for f in os.listdir(directory) if f[-4:]=='.sql']
            parameters = self.parameters
            for f in self.version.upgradeChain(version, files):
                self.log.inform("apply '%s'", f)
                if not dry_run:
                    fd = open(f)
                    proc = subprocess.Popen(self.mysql_command.split() + [
                        '-h', parameters['host'],
                        '-u', parameters['user'],
                        '-p'+parameters['password']
                    ], stdin=fd, stderr=subprocess.PIPE)
                    if proc.wait():
                        raise ExceptionUpgradeFailed, "upgrade failed"
            self.log.inform("upgraded database to version %s", version)
            if not dry_run:
                self.setVersionInDatabase(version)
                self.version = Version(self.getVersionFromDatabase())

    def getVersion(self):
        return self.version

    def cursor(self, *args, **kwargs):
        try:
            return self.db.cursor(*args, **kwargs)
        except (AttributeError, MySQLdb.OperationalError):
            self.db.connect()
            return self.db.cursor(*args, **kwargs)

    def literal(self, args):
        return self.db.literal(args)

