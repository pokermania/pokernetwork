from twisted.internet import reactor

from pokernetwork import log as network_log
log = network_log.get_child('lockcheck')

class LockCheck(object):

    log = log.get_child('LockCheck')

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
            self.log.error("Exception on start()", exc_info=1)

    def stop(self):
        try:
            if self._timer is None:
                return
            if self._timer.active():
                self._timer.cancel()
            self._timer = None
        except:
            self.log.error("Exception on stop()", exc_info=1)

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
