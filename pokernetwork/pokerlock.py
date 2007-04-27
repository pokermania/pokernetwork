#
# Copyright (C) 2006, 2007 Loic Dachary <loic@dachary.org>
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

from twisted.internet import reactor, defer
from twisted.python import failure
import threading
import thread
import MySQLdb
import Queue
import time

class PokerLock(threading.Thread):

    TIMED_OUT	= 1
    DEAD	= 2
    RELEASE	= 3

    acquire_timeout = 60
    queue_timeout = 2 * 60
    acquire_sleep = 1
    
    def __init__(self, parameters):
        self.verbose = 0
        self.q = Queue.Queue()
        self.lock = threading.Lock()
        self.db = None
        self.running = True
        self.connect(parameters)
        threading.Thread.__init__(self, target = self.main)
    
    def close(self):
        if self.isAlive():
            self.q.put((None, None, None, None))
            self.join()

        if self.db:
            self.db.close()
            self.db = None
        
    def stopping(self):
        if self.verbose > 2: print "PokerLock::(" + str(thread.get_ident()) + ") stopping"
        self.running = False

    def main(self):
        try:
            reactor.addSystemEventTrigger('during', 'shutdown', self.stopping)
            while 1:
                if self.verbose > 2: print "PokerLock::(" + str(thread.get_ident()) + ") loop"
                if not self.running and self.q.empty():
                    print "PokerLock::(" + str(thread.get_ident()) + ") stopped"
                    break

                try:
                    ( name, function, timeout, deferred ) = self.q.get(timeout = PokerLock.queue_timeout)
                except Queue.Empty:
                    #
                    # When timeout, silently terminate the thread
                    #
                    print "PokerLock::(" + str(thread.get_ident()) + ") timeout"
                    break
                except:
                    raise

                if not name:
                    #
                    # Stop the thread
                    #
                    break

                try:
                    function(name, timeout)
                    if self.running:
                        reactor.callFromThread(deferred.callback, name)
                    else:
                        self.lock.release()
                except:
                    print "PokerLock::(" + str(thread.get_ident()) + ") exception in function"
                    self.lock.release()
                    reactor.callFromThread(deferred.errback, failure.Failure())
            self.db.close()
            self.db = None
        except:
            if self.verbose > 2: print "PokerLock::(" + str(thread.get_ident()) + ") exception"
            raise

    def connect(self, parameters):
        self.db = MySQLdb.connect(host = parameters["host"],
                                  user = parameters["user"],
                                  passwd = parameters["password"])

    def acquire(self, name, timeout = acquire_timeout):
        if self.verbose > 2: print "PokerLock::acquire"
        if not self.isAlive():
            raise Exception(PokerLock.DEAD, "this PokerLock instance is dead, create a new one")
        d = defer.Deferred()
        self.q.put((name, self.__acquire, timeout, d))
        return d
        
    def __acquire(self, name, timeout):
        if self.verbose > 2: print "PokerLock::__acquire(%s) %s %d" % ( str(thread.get_ident()), name, timeout )
        tick = timeout
        while 1:
            if self.lock.acquire(0):
                break
            tick -= PokerLock.acquire_sleep
            if tick <= 0:
                if self.verbose > 2: print "PokerLock::__acquire(%s) TIMED OUT" % str(thread.get_ident())
                raise Exception(PokerLock.TIMED_OUT, name)
            if self.verbose > 2: print "PokerLock::__acquire(%s) sleep %f" % ( str(thread.get_ident()), PokerLock.acquire_sleep )
            time.sleep(PokerLock.acquire_sleep)
        self.db.query("SELECT GET_LOCK('%s', %d)" % ( name, timeout))
        result = self.db.store_result()
        if result.fetch_row()[0][0] != 1:
            raise Exception(PokerLock.TIMED_OUT, name)
        if self.verbose > 2: print "PokerLock::__acquire(%s) got MySQL lock" % str(thread.get_ident())

    def release(self, name):
        if self.verbose > 2: print "PokerLock::release"
        self.db.query("SELECT RELEASE_LOCK('%s')" % name)
        result = self.db.store_result()
        if result.fetch_row()[0][0] != 1:
            raise Exception(PokerLock.RELEASE, name)
        self.lock.release()
