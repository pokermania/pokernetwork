#
# -*- py-indent-offset: 4; coding: iso-8859-1 -*-
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

from MySQLdb.constants import ER

from twisted.internet import reactor

from pokernetwork import currencyclient
from pokernetwork import pokerlock
from pokernetwork.pokerpackets import *

class PokerCashier:

    def __init__(self, settings):
        self.settings = settings
        self.verbose = self.settings.headerGetInt("/server/@verbose")
        self.currency_client = currencyclient.CurrencyClient()
        self.parameters = settings.headerGetProperties("/server/cashier")[0]
        if self.parameters.has_key('pokerlock_queue_timeout'):
            pokerlock.PokerLock.queue_timeout = int(self.parameters['pokerlock_queue_timeout'])
        self.db = None
        self.db_parameters = settings.headerGetProperties("/server/database")[0]
        self.locks = {}
        reactor.callLater(0, self.resumeCommits)

    def close(self):
        for lock in self.locks.values():
            lock.close()
        del self.db
        
    def setDb(self, db):
        self.db = db

    def getDb(self):
        return self.db

    def resumeCommits(self):
        pass
    
    def getCurrencySerial(self, url, reentrant = True):
        cursor = self.db.cursor()
        #
        # Figure out the currency_serial matching the URL
        #
        sql = "SELECT serial FROM currencies WHERE url = %s"
        if self.verbose > 2: print sql % self.db.db.literal(url)
        cursor.execute(sql, url)
        if cursor.rowcount not in (1, 0):
            message = sql % url + " found " + str(cursor.rowcount) + " records instead of 0 or 1"
            print "*ERROR* " + message
        if cursor.rowcount == 0:
            sql = "INSERT INTO currencies (url) VALUES (%s)"
            if self.verbose > 2: print sql % self.db.db.literal(url)
            try:
                cursor.execute(sql, url)
                if cursor.rowcount == 1:
                    #
                    # Accomodate for MySQLdb versions < 1.1
                    #
                    if hasattr(cursor, "lastrowid"):
                        currency_serial = cursor.lastrowid
                    else:
                        currency_serial = cursor.insert_id()
            except Exception, e:
                cursor.close()
                if e[0] == ER.DUP_ENTRY and reentrant:
                    #
                    # Insertion failed, assume it's because another
                    # process already inserted it.
                    #
                    return self.getCurrencySerial(url, False)
                else:
                    raise
        else:
            (currency_serial,) = cursor.fetchone()

        cursor.close()
        return currency_serial

    def cashInGeneralFailure(self, reason, packet):
        if self.verbose > 2: print "cashInGeneralFailure: " + str(reason) + " packet = " + str(packet)
        if hasattr(packet, "currency_serial"):
            self.unlock(packet)
            del packet.currency_serial
        return reason

    def cashInUpdateSafe(self, result, transaction_id, packet):
        if self.verbose > 2: print "cashInUpdateSafe: " + str(packet)
        cursor = self.db.cursor()
        cursor.execute("START TRANSACTION")
        try:
            sqls = []
            sqls.append( ( "INSERT INTO safe SELECT currency_serial, serial, name, value FROM counter "  +
                           "       WHERE transaction_id = '" + transaction_id + "' AND " +
                           "             valid = 'n' ", 1 ) )
            sqls.append( ( "DELETE FROM counter,safe USING counter,safe WHERE " +
                           " counter.currency_serial = safe.currency_serial AND " +
                           " counter.serial = safe.serial AND " +
                           " counter.value = safe.value AND " +
                           " counter.valid = 'y' ", 0 ) )
            sqls.append( ( "DELETE FROM counter WHERE transaction_id = '" + transaction_id + "'", 1 ) )
            sqls.append( ( "INSERT INTO user2money (user_serial, currency_serial, amount) VALUES (" +
                           str(packet.serial) + ", " + str(packet.currency_serial) + ", " + str(packet.value) + ") " +
                           " ON DUPLICATE KEY UPDATE amount = amount + " + str(packet.value), 0 ) )

            for ( sql, rowcount ) in sqls:
                if cursor.execute(sql) < rowcount:
                    message = sql + " affected " + str(cursor.rowcount) + " records instead >= 1"
                    print "*ERROR* " + message
                    raise PacketError(other_type = PACKET_POKER_CASH_IN,
                                      code = PacketPokerCashIn.SAFE,
                                      message = message)

            cursor.execute("COMMIT")
            cursor.close()
        except:
            cursor.execute("ROLLBACK")
            cursor.close()
            raise

        self.unlock(packet);
        return PacketAck()

    def cashInUpdateCounter(self, new_notes, packet, old_notes):
        if self.verbose > 2: print "cashInUpdateCounter: new_notes = " + str(new_notes) + " old_notes = " + str(old_notes)
        #
        # The currency server gives us new notes to replace the
        # old ones. These new notes are not valid yet, the
        # currency server is waiting for our commit. Store all
        # the notes involved in the transaction on the counter.
        #
        cursor = self.db.cursor()
        cursor.execute("START TRANSACTION")
        transaction_id = new_notes[0][2]
        try:
            def notes_on_counter(notes, transaction_id, valid):
                for ( url, serial, name, value ) in notes:
                    sql = ( "INSERT INTO counter ( transaction_id, user_serial, currency_serial, serial, name, value, valid) VALUES " +
                            "                    ( %s,           %s,          %s,              %s,     %s,   %s,    %s )" )
                    cursor.execute(sql, ( transaction_id, packet.serial, packet.currency_serial, serial, name, value, valid ));
            notes_on_counter(new_notes, transaction_id, 'n')
            notes_on_counter(old_notes, transaction_id, 'y')
            cursor.execute("COMMIT")
            cursor.close()
        except:
            cursor.execute("ROLLBACK")
            cursor.close()
            raise

        return self.cashInCommit(transaction_id, packet)

    def cashInCommit(self, transaction_id, packet):
        if self.verbose > 2: print "cashInCommit"
        deferred = self.currency_client.commit(packet.url, transaction_id)
        deferred.addCallback(self.cashInUpdateSafe, transaction_id, packet)
        return deferred
        
    def cashInValidateNote(self, lock_name, packet):
        #
        # Ask the currency server for change
        #
        cursor = self.db.cursor()
        try:
            sql = ( "SELECT transaction_id FROM counter WHERE " +
                    " currency_serial = " + str(packet.currency_serial) + " AND " +
                    " serial = " + str(packet.bserial) )
            if self.verbose > 2: print sql
            cursor.execute(sql)
            if cursor.rowcount > 0:
                (transaction_id, ) = cursor.fetchone()
                deferred = self.cashInCommit(transaction_id, packet)
            else:
                #
                # Get the currency note from the safe
                #
                sql = "SELECT name, serial, value FROM safe WHERE currency_serial = " + str(packet.currency_serial)
                if self.verbose > 2: print sql
                cursor.execute(sql)
                if cursor.rowcount not in (0, 1):
                    message = sql + " found " + str(cursor.rowcount) + " records instead 1"
                    print "*ERROR* " + message
                    raise PacketError(other_type = PACKET_POKER_CASH_IN,
                                      code = PacketPokerCashIn.SAFE,
                                      message = message)
                notes = [ (packet.url, packet.bserial, packet.name, packet.value) ]
                if cursor.rowcount == 1:
                    #
                    # A note already exists in the safe, merge it
                    # with the provided note
                    #
                    (name, serial, value) = cursor.fetchone()
                    notes.append((packet.url, serial, name, value))
                deferred = self.currency_client.meltNotes(*notes)
                deferred.addCallback(self.cashInUpdateCounter, packet, notes)
        finally:
            cursor.close()
        return deferred

    def getLockName(self, serial):
        return "cashIn_%d" % serial

    def unlock(self, packet):
        name = self.getLockName(packet.currency_serial)
        if not self.locks.has_key(name):
            if self.verbose: print "*ERROR* cashInUnlock: unpexected missing " + name + " in locks (ignored)"
            return
        if not self.locks[name].isAlive():
            if self.verbose: print "*ERROR* cashInUnlock: unpexected dead " + name + " pokerlock (ignored)"
            return
        self.locks[name].release(name)

    def lock(self, packet):
        name = self.getLockName(packet.currency_serial)

        if self.verbose > 2: print "get lock " + name
        if self.locks.has_key(name):
            lock = self.locks[name]
            if lock.isAlive():
                create_lock = False
            else:
                lock.close()
                create_lock = True
        else:
            create_lock = True
        if create_lock:
            self.locks[name] = pokerlock.PokerLock(self.db_parameters)
            self.locks[name].verbose = self.verbose
            self.locks[name].start()

        return self.locks[name].acquire(name, int(self.parameters.get('acquire_timeout', 60)))
        
    def cashIn(self, packet):
        if self.verbose > 2: print "cashIn: " + str(packet)
        currency_serial = self.getCurrencySerial(packet.url)
        packet.currency_serial = currency_serial
        d = self.lock(packet)
        d.addCallback(self.cashInValidateNote, packet)
        d.addErrback(self.cashInGeneralFailure, packet)
        return d
    
    def cashOut(self, packet):
        pass
