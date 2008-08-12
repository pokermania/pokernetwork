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
import simplejson
import re
import imp
import time
from types import *

from traceback import format_exc

from twisted.web import server, resource, util, http
from twisted.internet import defer
from twisted.python import log

from pokernetwork.pokerpackets import *

def fromutf8(tree, encoding = 'ISO-8859-1'):
    return __walk(tree, lambda x: x.encode(encoding))

def toutf8(tree, encoding = 'ISO-8859-1'):
    return __walk(tree, lambda x: unicode(x, encoding))

def __walk(tree, convert):
    if type(tree) is TupleType or type(tree) is ListType:
        result = map(lambda x: __walk(x, convert), tree)
        if type(tree) is TupleType:
            return tuple(result)
        else:
            return result
    elif type(tree) is DictionaryType:
        new_tree = {}
        for (key, value) in tree.iteritems():
            converted_key = convert(str(key))
            new_tree[converted_key] = __walk(value, convert)
        return new_tree
    elif ( type(tree) is UnicodeType or type(tree) is StringType ):
        return convert(tree)
    else:
        return tree

def packets2maps(packets):
    maps = []
    for packet in packets:
        attributes = packet.__dict__.copy()
        if isinstance(packet, PacketList):
            attributes['packets'] = packets2maps(attributes['packets'])
        if 'message' in dir(packet):
            attributes['message'] = getattr(packet, 'message')
        #
        # It is forbiden to set a map key to a numeric (native
        # numeric or string made of digits). Taint the map entries
        # that are numeric and hope the client will figure it out.
        #
        for (key, value) in packet.__dict__.iteritems():
            if type(value) == DictType:
                    for ( subkey, subvalue ) in value.items():
                            del value[subkey]
                            new_subkey = str(subkey)
                            if new_subkey.isdigit():
                                    new_subkey = "X" + new_subkey
                            value[new_subkey] = subvalue
        attributes['type'] = packet.__class__.__name__
        maps.append(attributes)
    return maps

def args2packets(args):
    packets = []
    for arg in args:
        if re.match("^[a-zA-Z]+$", arg['type']):
            try:
                fun_args = len(arg) > 1 and '(**arg)' or '()'
                packets.append(eval(arg['type'] + fun_args))
            except:
                packets.append(PacketError(message = "Unable to instantiate %s(%s): %s" % ( arg['type'], arg, format_exc() )))
        else:
            packets.append(PacketError(message = "Invalid type name %s" % arg['type']))
    return packets

class MemcacheMockup:
    class Client:
        def __init__(self, addresses, *args, **kwargs):
            self.addresses = addresses
            self.cache = {}

        def get(self, key):
            if self.cache.has_key(key):
                return self.cache[key]
            else:
                return None
        
        def set(self, key, value):
            self.cache[key] = value

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

try:
    import memcache #pragma: no cover
except:
    memcache = MemcacheMockup #pragma: no cover

class Request(server.Request):

    def getSession(self):
        self.sitepath = self.args.get('name', [])
        return server.Request.getSession(self)

class Session(server.Session):

    def __init__(self, site, uid):
        server.Session.__init__(self, site, uid)
        self.avatar = site.resource.service.createAvatar()
        self.avatar.queuePackets()
        self.expired = False

    def expire(self):
        server.Session.expire(self)
        self.site.resource.service.destroyAvatar(self.avatar)
        del self.avatar
        self.expired = True
    
    def checkExpired(self):
        try:
            #
            # The session may expire as a side effect of the
            # verifications made by getSession against memcache.
            # When this happens an exception is thrown and checkExpire
            # is not called : this is intended because the
            # session already expired.
            #
            self.site.getSession(self.uid)
            server.Session.checkExpired(self)
            return True
        except KeyError:
            return False
        
class PokerResource(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.verbose = service.verbose
        self.deferred = defer.succeed(None)
        self.isLeaf = True

    def message(self, string):
        print "PokerXMLSimplified: " + string

#    def error(self, string):
#        self.message("*ERROR* " + string)

    def render(self, request):
        if self.verbose > 3:
            self.message("render " + request.content.read())
        request.content.seek(0, 0)
        jsonp = request.args.get('jsonp', [''])[0]
        if jsonp:
            data = request.args.get('packet', [''])[0]
        else:
            data = request.content.read()
        args = simplejson.loads(data, encoding = 'UTF-8')
        if hasattr(Packet.JSON, 'decode_objects'): # backward compatibility
            args = Packet.JSON.decode_objects(args)
        args = fromutf8(args)
        packet = args2packets([args])[0]

        if request.site.pipes:
            request.site.pipe(self.deferred, request, packet)

        def pipesFailed(reason):
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.write(body)
            request.connectionLost(reason)
            return reason

        self.deferred.addCallbacks(lambda result: self.deferRender(request, jsonp, packet),
                                   pipesFailed)
        return server.NOT_DONE_YET

    def deferRender(self, request, jsonp, packet):
        session = request.getSession()
        d = defer.maybeDeferred(session.avatar.handlePacketDefer, packet)
        def render(packets):
            #
            # update the session information if the avatar changed
            #
            session.site.updateSession(session)
            #
            # If the session expired and a session cookie was sent by the
            # client, expire the session cookie by setting its expiration date
            # in the past.
            #
            cookiename = "_".join(['TWISTED_SESSION'] + request.sitepath)
            sessionCookie = request.getCookie(cookiename)
            if session.expired:
                if not session.isLogged:
                    #
                    # If the user is not logged in and the session expired,
                    # the cookie must not be set.
                    #
                    request.cookies = []
                    if sessionCookie:
                        #
                        # If the cookie was already set but the user is not logged
                        # in and the session expired, it must be removed.
                        #
                        request.addCookie(cookiename,
                                          sessionCookie,
                                          expires = time.asctime(time.gmtime(time.time() - 3600)) + ' UTC',
                                          path = '/')
            #
            # Format answer
            #
            maps = packets2maps(packets)
            if jsonp:
                result_string = jsonp + '(' + str(Packet.JSON.encode(maps)) + ')'
            else:
                result_string = str(Packet.JSON.encode(maps))
            request.setHeader("Content-length", str(len(result_string)))
            request.setHeader("Content-type", 'text/plain; charset="UTF-8"')
            request.write(result_string)
            request.finish()
            return True
        def processingFailed(reason):
            session.expire()
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.write(body)
            request.connectionLost(reason)
            return True
        d.addCallbacks(render, processingFailed)
        return d
        
class PokerSite(server.Site):

    requestFactory = Request
    sessionFactory = Session

    def __init__(self, settings, resource, **kwargs):
        server.Site.__init__(self, resource, **kwargs)
        sessionTimeout = settings.headerGetInt("/server/@session_timeout")
        if sessionTimeout > 0:
            self.sessionFactory.sessionTimeout = sessionTimeout
        sessionCheckTime = settings.headerGetInt("/server/@session_check")
        if sessionCheckTime > 0:
            self.sessionCheckTime = sessionCheckTime
        memcache_address = settings.headerGet("/server/@memcached")
        if memcache_address:
            self.memcache = memcache.Client([memcache_address])
        else:
            self.memcache = MemcacheMockup.Client([])
        self.pipes = []
        for path in settings.header.xpathEval("/server/rest_filter"):
            module = imp.load_source("poker_pipe", path.content)
            self.pipes.append(getattr(module, "rest_filter"))

    def pipe(self, d, request, packet):
        if self.pipes:
            for pipe in self.pipes:
                d.addCallback(lambda x: defer.maybeDeferred(pipe, self, request, packet))

    #
    # prevent calling the startFactory method of site.Server
    # to disable loging.
    #
    def startFactory(self): 
        pass
        
    def updateSession(self, session):
        #
        # assert the session informations were not changed in memcache
        #
        if ( ( self.memcache.get(session.uid) != str(session.memcache_serial) ) or
             ( session.memcache_serial > 0 and
               self.memcache.get(str(session.memcache_serial)) != session.uid )):
            session.expire()
            return False

        serial = session.avatar.getSerial()
        if session.memcache_serial == 0:
            if serial > 0:
                #
                # if the user is now logged in, bind the serial to the session
                #
                self.memcache.replace(session.uid, str(serial))
                self.memcache.add(str(serial), session.uid)
        else:
            if serial == 0:
                #
                # if the user has logged out, unbind the serial that was in memcache
                #
                self.memcache.delete(str(session.memcache_serial))
                self.memcache.replace(session.uid, '0')
            elif serial != session.memcache_serial:
                #
                # if the user changed personality, delete old serial, add new one and
                # update session
                #
                self.memcache.delete(str(session.memcache_serial))
                self.memcache.add(str(serial), session.uid)
                self.memcache.replace(session.uid, str(serial))
        session.isLogged = session.avatar.isLogged()
        if len(session.avatar.tables) == 0:
            session.expire()
        return True

    def getSession(self, uid):
        memcache_serial = self.memcache.get(uid)
        if memcache_serial == None:
            #
            # If the memcache session is gone, trash the current session
            # if it exists.
            #
            if self.sessions.has_key(uid):
                self.sessions[uid].expire()
        else:
            #
            # Safeguard against memcache inconsistency
            #
            if int(memcache_serial) > 0:
                assert uid == self.memcache.get(memcache_serial)
            memcache_serial = int(memcache_serial)
            #
            # If a session exists, make sure it is in sync with the memcache
            # serial.
            #
            if self.sessions.has_key(uid):
                session = self.sessions[uid]
                session.memcache_serial = memcache_serial
                if session.avatar.getSerial() == 0:
                    #
                    # If the user has been authed by an external application
                    # (i.e. another poker server or a third party program)
                    # act as if a login was just sent and was successfully
                    # authed.
                    #
                    if memcache_serial > 0:
                        session.avatar.relogin(memcache_serial)
                else:
                    #
                    # If the avatar logout and logged into another serial,
                    # expire the session
                    #
                    if session.avatar.getSerial() != memcache_serial:
                        session.expire()
            if not self.sessions.has_key(uid):
                #
                # Create a session with an uid that matches the memcache
                # key
                #
                self.makeSessionFromUid(uid).memcache_serial = memcache_serial
                if memcache_serial > 0:
                    self.sessions[uid].avatar.relogin(memcache_serial)
                
        return self.sessions[uid]

    def makeSessionFromUid(self, uid):
        session = self.sessions[uid] = self.sessionFactory(self, uid)
        session.startCheckingExpiration(self.sessionCheckTime)
        return session
        
    def makeSession(self):
        uid = self._mkuid()
        session = self.makeSessionFromUid(uid)
        session.memcache_serial = 0
        self.memcache.add(uid, str(session.memcache_serial))
        return session
