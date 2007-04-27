#!@PYTHON@
# -*- py-indent-offset: 4; coding: iso-8859-1; mode: python -*-
#
# Copyright (C) 2007 Loic Dachary <loic@dachary.org>
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
#
# Tweak poker-engine & twisted to use a fake clock so that
# the tests are immune to the performances of the machine
# running the test, even when testing timeouts or other delays.
#
import time, os
from twisted.python import runtime
from twisted.internet import reactor, base
from pokerengine import pokertournament

_seconds_value = time.time()
def _seconds_reset():
    global _seconds_original
    _seconds_original = _seconds_value
_seconds_reset()
_seconds_verbose = int(os.environ.get('VERBOSE_T', '3'))
def _seconds_tick():
    global _seconds_value
    if _seconds_verbose > 2:
        print "tick: %.01f" % ( _seconds_value - _seconds_original )
    _seconds_value += 0.1
    return _seconds_value

base.seconds = _seconds_tick
#
# select timeout must return immediately, it makes no sense
# to wait while testing.
#
reactor.timeout = lambda: 0
runtime.seconds = _seconds_tick
pokertournament.tournament_seconds = _seconds_tick

from pokernetwork.pokerlock import PokerLock
PokerLock.acquire_sleep = 0.01
