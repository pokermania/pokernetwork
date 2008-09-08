#
# -*- py-indent-offset: 4; coding: iso-8859-1 -*-
#
# Copyright (C) 2008 Loic Dachary <loic@dachary.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
memcache_singleton = {}

class MemcacheMockup:
    class Client:
        def __init__(self, addresses, *args, **kwargs):
            self.addresses = addresses
            self.cache = memcache_singleton

        def get(self, key):
            if self.cache.has_key(key):
                return self.cache[key]
            else:
                return None

        def get_multi(self, keys):
            r = {}
            for key in keys:
                if self.cache.has_key(key):
                    r[key] = self.cache[key]
            return r
        
        def set(self, key, value, time = 0):
            self.cache[key] = value

        def set_multi(self, kwargs, time = 0):
            self.cache.update(kwargs)
            return []

        def add(self, key, value):
            if self.cache.has_key(key):
                return 0
            else:
                self.cache[key] = value
                return 1

        def replace(self, key, value):
            if self.cache.has_key(key):
                self.cache[key] = value
                return 1
            else:
                return 0
            
        def delete(self, key):
            try:
                del self.cache[key]
                return 1
            except:
                return 0

        def delete_multi(self, keys):
            for key in keys:
                if self.cache.has_key(key):
                    del self.cache[key]
            return 1

try:
    import memcache #pragma: no cover
except:
    memcache = MemcacheMockup #pragma: no cover

