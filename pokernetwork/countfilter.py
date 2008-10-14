#
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
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

from pokernetwork import pokermemcache

#
# return a value if all actions were complete
#
def rest_filter(site, request, packet):    
    session = request.getSession()
    count_prefix = "COUNT"
    memcache_key = "_".join([count_prefix, str(request.sitepath), str(session.uid)])
    last_count = site.memcache.get(memcache_key)
    count = request.args.get("count", [0])[0]
    if count < last_count:
        raise Exception("a more recent client connection occured (%s), killing old connection (%s)" % (last_count, count))
    site.memcache.set(memcache_key, count, site.cookieTimeout*2)
    return True

#
# return a deferred if there is a pending action
#

#from twisted.internet import defer

#def rest_filter(site, request, packet):
#    return defer.Deferred()
