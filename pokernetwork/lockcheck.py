from twisted.internet import reactor
import traceback

class LockCheck(object):

    def __init__(self, timeout, callback, cb_args=()):
        self._timeout = timeout
        self._callback = callback
        self._callback_args = cb_args
        self._timer = None

    def start(self):
        try:
            if self._timer is None or not self._timer.active():
                self._timer = reactor.callLater(self._timeout, self._callback, *self._callback_args)
            else:
                self._timer.reset(self._timeout)
        except:
            print "[LockCheck] ERROR: Exception on start()\n" + "\n".join(traceback.format_exc())

    def stop(self):
        try:
            if self._timer is None:
                return
            if self._timer.active():
                self._timer.cancel()
            self._timer = None
        except:
            print "[LockCheck] ERROR: Exception on stop()\n" + "\n".join(traceback.format_exc())

class LockChecks(object):

    def __init__(self, timeout, callback):
        self._lock_checks = {}
        self._timeout = timeout
        self._callback = callback

    def start(self, serial):
        if serial not in self._lock_checks:
            self._lock_checks[serial] = LockCheck(self._timeout, self._callback, (serial,))
        self._lock_checks[serial].start()

    def stop(self, serial):
        if serial in self._lock_checks:
            self._lock_checks[serial].stop()

    def stopall(self):
        for lock in self._lock_checks.values():
            lock.stop()
