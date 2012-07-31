#!/usr/bin/env python test-pokerlock.py
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2008, 2009 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2006       Mekensleep <licensing@mekensleep.com>
#                          24 rue vieille du temple, 75004 Paris
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
#  Bradley M. Kuhn <bkuhn@ebb.org>
#

import sys
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))
sys.path.insert(1, path.join(TESTS_PATH, "../../common"))

from config import config
import log_history

from twisted.python import failure
from twisted.trial import unittest, runner, reporter
import twisted.internet.base
from twisted.internet import reactor
from twisted.internet import defer

twisted.internet.base.DelayedCall.debug = True

from urlparse import urlparse

from pokernetwork import pokerlock

import logging
from tests.testmessages import TestLoggingHandler
logger = logging.getLogger()
handler = TestLoggingHandler()
logger.addHandler(handler)
logger.setLevel(10)

class PokerLockTestCase(unittest.TestCase):
    # A note about self.log_history.reset()() calls: Note that due to the
    #  threading nature of the pokerlock methods, you must be very careful
    #  when you call self.log_history.reset()() in these tests.  This is because
    #  a thread can wake up and write the messages you are hoping for to
    #  check in your tests while you are clearing them.  The most
    #  important rule-of-thumb that I discovered was to make sure that you
    #  always call self.log_history.reset()() before each lock.aquire() method
    #  call.
    #  ----------------------------------------------------------------
    def setUp(self):
        self.log_history = log_history.Log()
        pokerlock.PokerLock.acquire_sleep = 1
        self.parameters = {'host': 'localhost', 'user': 'root', 'password': 'holahola'}
        pokerlock.PokerLock.queue_timeout = 30
        self.locker = pokerlock.PokerLock(self.parameters)
        self.locker.start()
    # ----------------------------------------------------------------    
    def tearDown(self):
        self.locker.close()
    # ----------------------------------------------------------------    
    def test01_simple(self):
        self.log_history.reset()()
        d = self.locker.acquire('lock01')
        def validate(result):
            if isinstance(result, failure.Failure): raise result
            for string in  ['__acquire lock01',
                         '__acquire got MySQL lock', 'acquired' ]:
                self.failUnless(self.log_history.search(string), "missing '%s' in output" % string)
            self.assertEqual("lock01", result)
            self.locker.release('lock01')
            return result
        d.addBoth(validate)
        return d
    # ----------------------------------------------------------------
    # Note that test02_wait, no locker2 failure, is the only test that
    # looks for 'loop, queue size' in the output strings.  The other tests
    # do not do this because the system may be so fast that it never
    # loops.
    def test02_wait(self):
        def locker2_succeeded(result):
            self.locker.release('lock01')
            self.fail("locker2 succeeded with result = %s : should have failed with timeout")
            self.locker2.close()

        def locker2_failed(result):
            needed = [
                '__acquire lock01', 'acquired', 'exception in function', 'loop, queue size'
            ]
            for s in needed:
                self.assertTrue(self.log_history.search(s), "missing '%s' in output (got %s)" % (s,self.log_history.get_all()))

            self.log_history.reset()()
            self.locker.release('lock01')
            self.assertTrue(isinstance(result, failure.Failure))
            self.assertEqual(result.value[0], pokerlock.PokerLock.TIMED_OUT)
            self.locker2.close()

        def locker2():
            self.log_history.reset()()
            self.locker2 = pokerlock.PokerLock(self.parameters)
            self.locker2.start()
            d = self.locker2.acquire('lock01', 0)
            d.addCallback(locker2_succeeded)
            d.addErrback(locker2_failed)
            return d
            
        def validate(result):
            if isinstance(result, failure.Failure): raise result

            needed = [
                '__acquire lock01',
                'acquired', 
                '__acquire got MySQL lock'
            ]
            for s in needed:
                self.assertTrue(self.log_history.search(s), "missing '%s' in output (got %s)" % (s,self.log_history.get_all()))
            self.assertEqual("lock01", result)
            return locker2()

        self.log_history.reset()()
        d = self.locker.acquire('lock01', 0)
        d.addBoth(validate)
        return d
    # ----------------------------------------------------------------    
    def test03_acquire_dead(self):
        self.locker.close()
        self.log_history.reset()()
        try:
            self.locker.acquire('lock01')
            problem = True
        except Exception, e:
            problem = False
            self.assertEqual(e[0], pokerlock.PokerLock.DEAD)
            self.failUnless(self.log_history.search('acquire'), "missing 'acquire' in output")
        if problem:
            self.fail("acquire on dead PokerLock did not raise exception")
    # ----------------------------------------------------------------    
    def test04_release_twice(self):
        def validate(result):
            if isinstance(result, failure.Failure): raise result
            self.assertEqual("lock01", result)
            for string in ['__acquire lock01', 'acquired',
                           '__acquire got MySQL lock']:
                if not self.log_history.search(string): print self.log_history.get_all()
                self.failUnless(self.log_history.search(string), "%s not found in output" % string)

            self.log_history.reset()()
            self.locker.release("lock01")
            self.failUnless(self.log_history.search('release lock01'),
                            "missing 'release lock01' in output")
            self.log_history.reset()()
            try:
                self.locker.release("lock01")
                problem = True
            except Exception, e:
                problem = False
                self.assertEqual(e[0], pokerlock.PokerLock.RELEASE)
                self.failUnless(self.log_history.search('release lock01'),
                                "missing 'release lock01' in output")
            if problem:
                self.fail("double release did not raise exception")

        self.log_history.reset()()
        d = self.locker.acquire('lock01')
        d.addBoth(validate)
        return d
    # ----------------------------------------------------------------    
    def test05_many(self):
        self.locker.message = lambda self, string: True
        # Runs too slow if you have messages on
        dl = []
        def show(x):
            self.locker.release('lock01')

        pokerlock.PokerLock.acquire_sleep = 0.01

        for i in xrange(1,300):
            d = self.locker.acquire('lock01', 3)
            d.addBoth(show)
            dl.append(d)
        self.log_history.reset()()
        return defer.DeferredList(dl)
    # ----------------------------------------------------------------    
    def test06_aquireTimeout(self):
        pokerlock.PokerLock.acquire_sleep = 0.01

        def lockTimeoutExpected_succeeded(result):
            self.locker.release('lock01')
            self.fail("lock timeout succeeded with result = %s : should have failed with timeout"
                      % result)

        def lockTimeoutExpected_failed(result):
            self.assertTrue(isinstance(result, failure.Failure))
            self.assertEqual(result.value[0], pokerlock.PokerLock.TIMED_OUT)
            self.failUnless(self.log_history.search('__acquire TIMED OUT'),
                            "missing '__acquire TIMED OUT' in output")
            
        def lockFastTimeout():
            self.failUnless(self.log_history.search('acquire'),
                            "missing 'acquire' in output")
            pokerlock.PokerLock.acquire_sleep = 1
            self.log_history.reset()()
            d = self.locker.acquire('lock01', 0)
            d.addCallback(lockTimeoutExpected_succeeded)
            d.addErrback(lockTimeoutExpected_failed)
            return d
            
        def validate(result):
            if isinstance(result, failure.Failure): raise result
            self.assertEqual("lock01", result)
            for string in  ['__acquire lock01',
                         '__acquire got MySQL lock', 'acquired' ]:
                if not self.log_history.search(string):
                    print self.log_history.get_all()
                self.failUnless(self.log_history.search(string), "missing '%s' in output" % string)
            return lockFastTimeout()

        pokerlock.PokerLock.acquire_sleep = 0.01
        self.log_history.reset()()
        d = self.locker.acquire('lock01', 30)
        d.addBoth(validate)
        return d
    # ----------------------------------------------------------------    
    def test07_mainTests_stopped(self):
        self.log_history.reset()()
        self.locker.stopping()
        self.failUnless(self.log_history.search("stopping"), "missing 'stopping' in output")
        self.log_history.reset()()
        d = defer.Deferred()
        def checker(val):
            self.failIf(self.locker.running)
            self.failUnless(self.log_history.search("stopped"), "missing 'stopped' in output")
        reactor.callLater(pokerlock.PokerLock.acquire_sleep*3, lambda: d.callback(True))
        return d
    # ----------------------------------------------------------------    
    def test08_mainTests_emptyQueue(self):
        """test08_mainTests_emptyQueue

        This test creates a dummy PokerLock.__init__() so that a MockQueue
        can be used that force-raises a Queue.Empty() exception, which is
        caught by the running loop in the lock and ends it."""
        import Queue
        import threading
        from pokernetwork.pokerlock import PokerLock
        from pokernetwork import log as network_log
        
        class  MockQueue:
            def __init__(qSelf):
                qSelf.qSizeCallCount = 0
                qSelf.getCallCount = 0
            def qsize(qSelf):
                qSelf.qSizeCallCount += 1
                return 1
            def get(qSelf, timeout = 1):
                qSelf.getCallCount += 1
                raise Queue.Empty("MOCK")
            def empty(qSelf):
                return False
            def put(qSelf, val):
                pass
            
        myMockQueue = MockQueue()
        log = network_log.getChild('pokerlock')
        
        class MockInitLock(PokerLock):
            def __init__(self, parameters):
                self.log = log.getChild(self.__class__.__name__)
                self.q = myMockQueue
                self.lock = threading.Lock()
                self.db = None
                self.running = True
                self.connect(parameters)
                threading.Thread.__init__(self, target = self.main)

        self.log_history.reset()()
        mockLocker = MockInitLock(self.parameters)
        mockLocker.start()
        mockLocker.close()
        self.failUnless(self.log_history.search("timeout"),
                          "output does not contain 'timeout'")
        self.failUnless(self.log_history.search("loop"),
                          "output does not contain 'loop'")
        self.failUnless(myMockQueue.qSizeCallCount > 0,
                        "MockQueue.qSize() should be called at least once.")
        self.failUnless(myMockQueue.getCallCount > 0,
                        "MockQueue.get() should be called at least once.")
    # ----------------------------------------------------------------    
    def test09_mainTests_wrongRaise(self):
        import Queue
        import time
        from cStringIO import StringIO
        class MockException(Exception): pass
        class  MockQueue:
            def qsize(qSelf):
                return 1
            def get(qSelf, timeout = 1):
                raise MockException("MOCK")
            def empty(qSelf):
                return False
            def put(qSelf, val):
                pass
        oldStderr = sys.stderr
        sys.stderr = StringIO()
        anotherLock = pokerlock.PokerLock(self.parameters)
        anotherLock.q = MockQueue()
        anotherLock.start()
        time.sleep(2)
        value = sys.stderr.getvalue()
        sys.stderr = oldStderr
        self.failUnless(value.find('raise MockException("MOCK")\nMockException: MOCK') >= 0)
    # ----------------------------------------------------------------    
    def test10_mainTests_notRunningForCallback(self):
        import Queue
        import time

        global myLock
        def setNotRunning(name, timeout):
            global myLock
            myLock.running = False

        d = defer.Deferred()
        def succeeded(result): 
            self.failIf(True)
            
        def failed(result): 
            self.failIf(True)
        d.addErrback(failed)
        d.addCallback(succeeded)

        class  MockQueue:
            def __init__(qSelf):
                qSelf.count = 1
            def qsize(qSelf):
                return qSelf.count
            def get(qSelf, timeout = 1):
                if qSelf.count > 0:
                    qSelf.count = 0
                    return ("Mocky", setNotRunning, 10, d)
                else:
                    raise Queue.Empty
            def empty(qSelf):
                return qSelf.count <= 0
            def put(qSelf, val):
                pass
        class  MockLock:
            def __init__(lSelf):
                lSelf.calledReleaseCount = 0
            def release(lSelf):
                lSelf.calledReleaseCount += 1

        self.log_history.reset()()
        anotherLock = pokerlock.PokerLock(self.parameters)
        anotherLock.q = MockQueue()
        anotherLock.lock = MockLock()
        myLock = anotherLock
        anotherLock.start()
        time.sleep(2)
        self.failUnless(self.log_history.search('release because not running'), 
                        "missing 'release because not running' in output")
        self.assertEquals(anotherLock.running, False)
        self.assertEquals(anotherLock.lock.calledReleaseCount, 1)
    # ----------------------------------------------------------------    
    def test11_mainTests_raiseForceRelease(self):
        import Queue
        import time
        class MockException(Exception): pass

        def raiseForceRelease(name, timeout):
            raise MockException()

        def succeeded(result): 
            self.failIf(True)
            
        def failed(result): 
            self.failUnless(issinstance(result, MockException))
            # FIXME: this callback never happens; it should, however.  I
            # am not completely sure why; I assume it's because the
            # reactor.callFromThread() errback call in the main() doesn't
            # get executed before the reactor dies.  OTOH, I don't fully
            # understand the thread/reactor interaction issues .  If
            # someone can figure out and make sure this callback happens,
            # I'd appreciate it.
        d = defer.Deferred()
        d.addErrback(failed)
        d.addCallback(succeeded)

        class  MockQueue:
            def __init__(qSelf):
                qSelf.count = 1
            def qsize(qSelf):
                return qSelf.count
            def get(qSelf, timeout = 1):
                if qSelf.count > 0:
                    qSelf.count = 0
                    return ("Mocky", raiseForceRelease, 10, d)
                else:
                    raise Queue.Empty
            def empty(qSelf):
                return qSelf.count <= 0
            def put(qSelf, val):
                pass
        class  MockLock:
            def release(lSelf):
                raise MockException("MOCKY NO LOCK RELEASE")

        self.log_history.reset()()
        anotherLock = pokerlock.PokerLock(self.parameters)

        anotherLock.q = MockQueue()
        anotherLock.lock = MockLock()
        anotherLock.start()
        time.sleep(2)

        self.assertEquals(anotherLock.running, True)
        for string in [ 
            'exception in function', 
            'failed to release lock after exception',
            'raise MockException("MOCKY NO LOCK RELEASE")'
        ]:
            self.failUnless(self.log_history.search(string), "missing '%s' in output" % string)
    # ----------------------------------------------------------------    
    def test12_mainTests_makeSureDBCloses(self):
        class  MockDB:
            def __init__(dbSelf):
                dbSelf.closeCount = 0
            def close(dbSelf):
                dbSelf.closeCount += 1
        db = MockDB()
        oldIsAlive = self.locker.isAlive
        def mockIsAlive(): return False
        self.locker.isAlive = mockIsAlive
        oldDb = self.locker.db
        self.locker.db = db
        self.locker.close()
        self.assertEquals(self.locker.db, None)
        self.locker.db = oldDb
        self.assertEquals(db.closeCount, 1)
        self.locker.isAlive = oldIsAlive
# ----------------------------------------------------------------
def GetTestSuite():
    suite = runner.TestSuite(PokerLockTestCase)
    suite.addTest(unittest.makeSuite(PokerLockTestCase))
    return suite
# ----------------------------------------------------------------
def GetTestedModule():
    return currencyclient
# ----------------------------------------------------------------
def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test02"
    suite = loader.loadClass(PokerLockTestCase)
    return runner.TrialRunner(
        reporter.TextReporter,
        tracebackFormat='default',
    ).run(GetTestSuite())

# ----------------------------------------------------------------
if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
