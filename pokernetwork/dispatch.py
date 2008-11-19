#
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
#
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
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
# Originaly imported from twisted. The code is small enough not to warrant
# an actually copyright.
#
class EventDispatcher:
    """
    A global event dispatcher for events.
    I'm used for any events that need to span disparate objects in the client.

    I should only be used when one object needs to signal an object that it's
    not got a direct reference to (unless you really want to pass it through
    here, in which case I won't mind).

    I'm mainly useful for complex GUIs.
    """

    def __init__(self, prefix="event_"):
        self.prefix = prefix
        self.callbacks = {}


    def registerHandler(self, name, meth):
        self.callbacks.setdefault(name, []).append(meth)


    def autoRegister(self, obj):
        from twisted.python import reflect
        d = {}
        reflect.accumulateMethods(obj, d, self.prefix)
        for k,v in d.items():
            self.registerHandler(k, v)


    def publishEvent(self, name, *args, **kwargs):
	if self.callbacks.has_key(name):
	    for cb in self.callbacks[name]:
		cb(*args, **kwargs)
