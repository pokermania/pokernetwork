#
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
        for cb in self.callbacks[name]:
            cb(*args, **kwargs)
