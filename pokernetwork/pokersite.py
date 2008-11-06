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
import base64
from types import *

from traceback import format_exc

from twisted.web import server, resource, util, http
from twisted.internet import defer
from twisted.python import log
from twisted.python.runtime import seconds

from pokernetwork.pokerpackets import *
from pokernetwork import pokermemcache

def uid2last_modified(uid):
    return 'L' + uid

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

class Request(server.Request):

    def getSession(self):
        self.sitepath = self.args.get('name', [])
        return server.Request.getSession(self)

    def cookieName(self):
        return "_".join(['TWISTED_SESSION'] + self.sitepath)

    def expireSessionCookie(self):
        cookiename = self.cookieName()
        sessionCookie = self.getCookie(cookiename)
        if sessionCookie:
            self.addCookie(cookiename,
                           sessionCookie,
                           expires = time.asctime(time.gmtime(seconds() - 3600)) + ' UTC',
                           path = '/')
        

class Session(server.Session):

    def __init__(self, site, uid):
        server.Session.__init__(self, site, uid)
        self.avatar = site.resource.service.createAvatar()
        self.avatar.verbose = site.resource.verbose
        self.avatar.queuePackets()
        self.avatar.setExplain(PacketPokerExplain.ALL)
        self.avatar.roles.add(PacketPokerRoles.PLAY)
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
        except AssertionError:
            self.expire()
            return None
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

    def error(self, string):
        self.message("*ERROR* " + string)

    def render(self, request):
        if self.verbose > 3:
            request.content.seek(0, 0)
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
            #
            # Report only if the request has not been finished already.
            # It is the responsibility of each filter to handle errors
            # either by passing them on the errback chain or by filling
            # the request with a proper report.
            #
            if not request.finished:
                body = reason.getTraceback()
                request.setResponseCode(http.INTERNAL_SERVER_ERROR)
                request.setHeader('content-type',"text/html")
                request.setHeader('content-length', str(len(body)))
                request.expireSessionCookie()
                request.write(body)
                request.connectionLost(reason)
                if self.verbose > 2:
                    self.error(str(body))
                    
            #
            # Return a value that is not a Failure so that the next
            # incoming request is accepted (otherwise the server keeps
            # returning error on every request)
            #
            return True

        self.deferred.addCallback(lambda result: self.deferRender(request, jsonp, packet))
        self.deferred.addErrback(pipesFailed)
        return server.NOT_DONE_YET

    def deferRender(self, request, jsonp, packet):
        if request.finished:
            #
            # For instance : the request was reverse-proxied to a server.
            #
            return True
        session = request.getSession()
        d = defer.maybeDeferred(session.avatar.handlePacketDefer, packet)
        def render(packets):
            #
            # update the session information if the avatar changed
            #
            session.site.updateSession(session)
            #
            # Format answer
            #
            maps = toutf8(packets2maps(packets))
            if jsonp:
                result_string = jsonp + '(' + str(Packet.JSON.encode(maps)) + ')'
            else:
                result_string = str(Packet.JSON.encode(maps))
            request.setHeader("content-length", str(len(result_string)))
            request.setHeader("content-type", 'text/plain; charset="UTF-8"')
            request.write(result_string)
            request.finish()
            return True
        def processingFailed(reason):
            session.expire()
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-length', str(len(body)))
            request.setHeader('content-type',"text/html")
            request.write(body)
            request.connectionLost(reason)
            return True
        d.addCallbacks(render, processingFailed)
        return d

class PokerImageUpload(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.verbose = service.verbose
        self.deferred = defer.succeed(None)
        self.isLeaf = True

    def message(self, string):
        print "PokerImageUpload: " + string

#    def error(self, string):
#        self.message("*ERROR* " + string)

    def render(self, request):
        if self.verbose > 3:
            self.message("render " + request.content.read())
        request.content.seek(0, 0)
        self.deferred.addCallback(lambda result: self.deferRender(request))
        def failed(reason):
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.expireSessionCookie()
            request.write(body)
            request.connectionLost(reason)
            return True
        self.deferred.addErrback(failed)
        return server.NOT_DONE_YET

    def deferRender(self, request):
        session = request.getSession()
        if session.avatar.isLogged():
            serial = request.getSession().avatar.getSerial()
            data = request.args['filename'][0]    
            packet = PacketPokerPlayerImage(image = base64.b64encode(data), serial = serial)
            self.service.setPlayerImage(packet)
            result_string = 'image uploaded'
            request.setHeader("Content-length", str(len(result_string)))
            request.setHeader("Content-type", 'text/plain; charset="UTF-8"')
            request.write(result_string)
            request.finish()
            return
        else:
            session.expire()
            body = 'not logged'
            request.setResponseCode(http.UNAUTHORIZED)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.write(body)
            request.finish()
            return

class PokerAvatarResource(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.verbose = service.verbose
        self.deferred = defer.succeed(None)
        self.isLeaf = True

    def message(self, string):
        print "PokerAvatarResource: " + string

#    def error(self, string):
#        self.message("*ERROR* " + string)

    def render(self, request):
        if self.verbose > 3:
            self.message("render " + request.content.read())
        request.content.seek(0, 0)
        serial = int(request.path.split('/')[-1])
        self.deferred.addCallback(lambda result: self.deferRender(request, serial))
        def failed(reason):
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.expireSessionCookie()
            request.write(body)
            request.connectionLost(reason)
            return True
        self.deferred.addErrback(failed)
        return server.NOT_DONE_YET

    def deferRender(self, request, serial):
        packet  = self.service.getPlayerImage(serial)
        if len(packet.image):
            result_string = base64.b64decode(packet.image)
            request.setHeader("Content-length", str(len(result_string)))
            request.setHeader("Content-type", packet.image_type)
            request.write(result_string)
            request.finish()
            return
        else:
            body = 'not found'
            request.setResponseCode(http.NOT_FOUND)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.write(body)
            request.finish()
            return

class PokerSite(server.Site):

    requestFactory = Request
    sessionFactory = Session

    def __init__(self, settings, resource, **kwargs):
        server.Site.__init__(self, resource, **kwargs)
        cookieTimeout = settings.headerGetInt("/server/@cookie_timeout")
        if cookieTimeout > 0:
            self.cookieTimeout = cookieTimeout
        else:
            self.cookieTimeout = 1200
        sessionTimeout = settings.headerGetInt("/server/@session_timeout")
        if sessionTimeout > 0:
            self.sessionFactory.sessionTimeout = sessionTimeout
        sessionCheckTime = settings.headerGetInt("/server/@session_check")
        if sessionCheckTime > 0:
            self.sessionCheckTime = sessionCheckTime
        memcache_address = settings.headerGet("/server/@memcached")
        if memcache_address:
            self.memcache = pokermemcache.memcache.Client([memcache_address])
        else:
            self.memcache = pokermemcache.MemcacheMockup.Client([])
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
        
    def stopFactory(self): 
        for key in self.sessions.keys():
            self.sessions[key].expire()
        
    def updateSession(self, session):
        #
        # assert the session informations were not changed in memcache
        #
        if ( ( self.memcache.get(session.uid) != str(session.memcache_serial) ) or
             ( session.memcache_serial > 0 and
               self.memcache.get(str(session.memcache_serial)) != session.uid )):
            session.isLogged = False
            session.expire()
            return False

        serial = session.avatar.getSerial()
        if session.memcache_serial == 0:
            if serial > 0:
                #
                # if the user is now logged in, bind the serial to the session
                #
                self.memcache.replace(session.uid, str(serial))
                #
                # 'set' is used instead of 'add' because the latest session wins,
                # even if the previous is still active. When a session is
                # properly closed, the serial memecache entry is discarded.
                # But if the session is not closed, there is a spurious
                # serial entry referencing the old session. When a request
                # arrives with the old session uid (check getSession #xref1) it will
                # trigger an error and do nothing.
                #
                self.memcache.set(str(serial), session.uid)
        else:
            if serial == 0:
                #
                # if the user has logged out, unbind the serial that was in memcache
                #
                self.memcache.delete(str(session.memcache_serial))
                self.memcache.replace(session.uid, '0')
                self.deleteMemcacheCookie(session.uid)
            elif serial != session.memcache_serial:
                #
                # if the user changed personality, delete old serial, add new one and
                # update session
                #
                self.memcache.delete(str(session.memcache_serial))
                self.memcache.add(str(serial), session.uid)
                self.memcache.replace(session.uid, str(serial))
                self.deleteMemcacheCookie(session.uid)
                
        session.isLogged = session.avatar.isLogged()
        if session.isLogged:
            self.refreshMemcacheCookie(session.uid)
        if len(session.avatar.tables) <= 0 and len(session.avatar.tourneys) <= 0:
            session.expire()
        return True

    def getSession(self, uid):
        if not isinstance(uid, str):
            raise Exception("uid is not str: '%s' %s" % (uid, type(uid)))
        self.expireMemcacheCookie(uid)
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
            # #xref1
            # Safeguard against memcache inconsistency.
            # This happens when another session took over the serial (setting
            # a new session uid in this serial memcache entry). The policy is
            # that the newest session wins and the previous session must not
            # get any requests. 
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

    def deleteMemcacheCookie(self, uid):
        if not isinstance(uid, str):
            raise Exception("uid is not str: '%s' %s" % (uid, type(uid)))
        self.memcache.delete(uid2last_modified(uid))

    def refreshMemcacheCookie(self, uid):
        if not isinstance(uid, str):
            raise Exception("uid is not str: '%s' %s" % (uid, type(uid)))
        self.memcache.set(uid2last_modified(uid), str(int(seconds())))

    def expireMemcacheCookie(self, uid):
        if not isinstance(uid, str):
            raise Exception("uid is not str: '%s' %s" % (uid, type(uid)))
        last_modified = self.memcache.get(uid2last_modified(uid))
        if last_modified != None and seconds() - int(last_modified) > self.cookieTimeout:
            self.memcache.delete(uid2last_modified(uid))
            self.memcache.delete(self.memcache.get(uid))
            self.memcache.delete(uid)
