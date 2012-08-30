#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jean-Paul Calderone <exarkun@twistedmatrix.com>
# Copyright (C) 2008 Johan Euphrosine <proppy@aminche.com>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
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

import guppy, gc
 
import sys
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from twisted.web import client
 
from twisted.web import server, resource
from twisted.internet import reactor
 
hpy = guppy.hpy()

class Simple(resource.Resource):
        isLeaf = True
        def render_GET(self, request):
                return "<html>Hello, world!</html>"
 
def f(ignored, last, first):
        gc.collect()
        next = hpy.heap()
        print 'SINCE LAST TIME'
        print next - last
        print 'SINCE FOREVER'
        print last - first
        d = client.getPage("http://localhost:8080/")
        d.addCallback(f, next, first)

def main():
        site = server.Site(Simple())
        port = reactor.listenTCP(8080, site)
        first = hpy.heap()
        f(None, first, first)
        reactor.run()
 
main()
