from twisted.internet import reactor
import traceback

class LockCheck(object):

    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._timer = None

    def start(self):
        try:
            if self._timer is None or not self._timer.active():
                self._timer = reactor.callLater(self._timeout, self._callback)
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
