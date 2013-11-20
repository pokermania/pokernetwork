from pokernetwork.util import log as util_log
log = util_log.get_child('sql')

from pokernetwork.util.timer import Timer
from MySQLdb.cursors import Cursor, DictCursor

SLOW_QUERY_THRESHOLD = .1

class TimingCursor(Cursor):

    def execute(self, query, args=None, threshold=None):
        with Timer() as t:
            ret = super(TimingCursor, self).execute(query, args)

        if t.interval > (threshold or SLOW_QUERY_THRESHOLD):
            log.warn("slow query (%f sec): %s", t.interval, self._executed)

        return ret

class TimingDictCursor(DictCursor):

    def execute(self, query, args=None, threshold=None):
        with Timer() as t:
            ret = super(TimingDictCursor, self).execute(query, args)

        if t.interval > (threshold or SLOW_QUERY_THRESHOLD):
            log.warn("slow query (%f sec): %s", t.interval, self._executed)

        return ret

def lex(a, __cache={}):
    try:
        return __cache[a]
    except KeyError:
        i = 0
        quoted = None # should be None, single or double
        x = a
        try:
            while True:
                if x[i] == '\n':
                    if quoted:
                        x = x[:i] + '\\n' + x[i+1:]
                        i += 1
                    else:
                        x = x[:i] + x[i+1:]
                        i -= 1
                elif x[i] in ("'", '"', '`') and (i == 0 or x[i-1] != '\\'):
                    if x[i] == quoted:
                        quoted = None
                    elif not quoted:
                        quoted = x[i]
                elif i > 0 and not quoted  and x[i] == ' ' and x[i-1] == ' ':
                    x = x[:i] + x[i+1:]
                    i -= 1
                i += 1
        except IndexError:
            pass
        x = x.strip()
        __cache[a] = x
        return x
