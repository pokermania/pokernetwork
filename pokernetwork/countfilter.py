#
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2008 Loic Dachary <loic@dachary.org>
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

from pokernetwork import pokermemcache

#
# return a value if all actions were complete
#
def rest_filter(site, request, packet):    
    session = request.getSession()
    count_prefix = "COUNT"
    memcache_key = "_".join([count_prefix, str(request.sitepath), str(session.uid)])
    last_count = site.memcache.get(memcache_key)
    if last_count:
        last_count = int(last_count)
    else:
        last_count = 0
    count = int(request.args.get("count", ['0'])[0])
    if count < last_count:
        raise Exception("a more recent client connection occured (%s), killing old connection (%s)" % (last_count, count))
    site.memcache.set(memcache_key, str(count), site.cookieTimeout*2)
    return True

#
# return a deferred if there is a pending action
#

#from twisted.internet import defer

#def rest_filter(site, request, packet):
#    return defer.Deferred()
