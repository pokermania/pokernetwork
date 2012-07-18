#
# Copyright (C) 2006, 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
#                    24 rue vieille du temple, 75004 Paris
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

from twisted.internet import reactor, defer
from twisted.python import failure
import threading
import thread
import MySQLdb
import Queue
import time

from pokernetwork import log as network_log
log = network_log.getChild('pokerlock')

class PokerLock(threading.Thread):

    TIMED_OUT = 1
    DEAD = 2
    RELEASE = 3

    acquire_timeout = 60
    queue_timeout = 2 * 60
    acquire_sleep = 0.1
    
    def __init__(self, parameters):
        self.log = log.getChild(self.__class__.__name__)
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
        self.log.debug("stopping")
        self.running = False

    def main(self):
        try:
            reactor.addSystemEventTrigger('during', 'shutdown', self.stopping)
            while 1:
                self.log.debug("loop, queue size %s", self.q.qsize())
                if not self.running and self.q.empty():
                    self.log.debug("stopped")
                    break

                try:
                    ( name, function, timeout, deferred ) = self.q.get(timeout = PokerLock.queue_timeout)
                except Queue.Empty:
                    #
                    # When timeout, silently terminate the thread
                    #
                    self.log.debug("timeout")
                    break
                except:
                    raise

                if not name:
                    #
                    # Stop the thread
                    #
                    self.log.debug("stop")
                    break

                try:
                    function(name, timeout)
                    if self.running:
                        reactor.callFromThread(deferred.callback, name)
                    else:
                        self.log.debug("release because not running")
                        self.lock.release()
                except:
                    self.log.error("exception in function main() -> release", exc_info=1)
                    try:
                        self.lock.release()
                    except:
                        self.log.error("failed to release lock after exception", exc_info=1)
                    reactor.callFromThread(deferred.errback, failure.Failure())
            self.db.close()
            self.db = None
        except:
            self.log.error("exception", exc_info=1)
            raise

    def connect(self, parameters):
        self.db = MySQLdb.connect(
            host=parameters["host"],
            user=parameters["user"],
            passwd=parameters["password"]
        )

    def acquire(self, name, timeout = acquire_timeout):
        self.log.debug("acquire")
        if not self.isAlive():
            raise Exception(PokerLock.DEAD, "this PokerLock instance is dead, create a new one")
        d = defer.Deferred()
        self.q.put((name, self.__acquire, timeout, d))
        return d
        
    def __acquire(self, name, timeout):
        self.log.debug("__acquire %s %d", name, timeout)
        tick = timeout
        while 1:
            if self.lock.acquire(0):
                self.log.debug("acquired")
                break
            tick -= PokerLock.acquire_sleep
            if tick <= 0:
                self.log.debug("__acquire TIMED OUT")
                raise Exception(PokerLock.TIMED_OUT, name)
            self.log.debug("__acquire sleep %f", PokerLock.acquire_sleep)
            time.sleep(PokerLock.acquire_sleep)
        self.db.query("SELECT GET_LOCK('%s', %d)" % ( name, timeout))
        result = self.db.store_result()
        if result.fetch_row()[0][0] != 1:
            raise Exception(PokerLock.TIMED_OUT, name)
        self.log.debug("__acquire got MySQL lock")

    def release(self, name):
        self.log.debug("release %s", name)
        self.db.query("SELECT RELEASE_LOCK('%s')" % name)
        result = self.db.store_result()
        if result.fetch_row()[0][0] != 1:
            raise Exception(PokerLock.RELEASE, name)
        self.lock.release()
