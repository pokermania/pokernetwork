#
# -*- py-indent-offset: 4; coding: iso-8859-1 -*-
#
# Copyright (C) 2008, 2009 Loic Dachary <loic@dachary.org>
# Copyright (C) 2009 Johan Euphrosine <proppy@aminche.com>
# Copyright (C) 2008 Bradley M. Kuhn <bkuhn@ebb.org>
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
import re
import imp
import base64

from traceback import format_exc

from twisted.web import server, resource, http
from twisted.internet import defer

from pokernetwork.packets import packets2maps

from pokernetwork.packets import *
from pokernetwork.pokerpackets import *
PacketFactoryWithNames = dict((packet_class.__name__,packet_class) for packet_class in PacketFactory.itervalues())

from pokernetwork import log as network_log
log = network_log.getChild('site')

# Disabled Unicode encoding. It is not required anymore since it is only used
# for the (dealer) chat. We measured a higher sit out count with Unicode
# activated FIXME a better solution would be to refactor the engine to only
# encode chat packets than to disable it altogether
def fromutf8(tree, encoding = 'ISO-8859-1'):
    return tree

def toutf8(tree, encoding = 'ISO-8859-1'):
    return tree

def __walk(tree, convert):
    if type(tree) is tuple or type(tree) is list:
        result = map(lambda x: __walk(x, convert), tree)
        if type(tree) is tuple:
            return tuple(result)
        else:
            return result
    elif type(tree) is dict:
        new_tree = {}
        for (key, value) in tree.iteritems():
            converted_key = convert(str(key))
            new_tree[converted_key] = __walk(value, convert)
        return new_tree
    elif type(tree) is unicode or type(tree) is str:
        return convert(tree)
    else:
        return tree

_arg2packet_re = re.compile("^[a-zA-Z]+$")

def args2packets(args):
    return (arg2packet(arg)[0] for arg in args)

def arg2packet(arg):
    packet_class = None
    packet = None
    packet_type_numeric = None
    
    if type(arg['type']) == int:
        try: 
            packet_class = PacketFactory[arg['type']]
            packet_type_numeric = True
        except Exception: pass
    
    elif type(arg['type']) == str and _arg2packet_re.match(arg['type']):
        try:
            packet_class = PacketFactoryWithNames[arg['type']]
            packet_type_numeric = False
        except Exception: pass
        
    if packet_class is None:
        packet = PacketError(message = "Invalid type name %s" % arg.get('type',None))
    else:
        if 'packets' in arg: arg['packets'] = list(args2packets(arg['packets']))
        
        try: packet = packet_class(**arg) if len(arg)>1 else packet_class()
        except Exception: 
            packet = PacketError(message = "Unable to instantiate %s(%s): %s" % ( arg['type'], arg, format_exc()))
            
    return (packet, packet_type_numeric)
    
class Request(server.Request):

    def getSession(self):
        uid = self.args.get('uid', [self.site._mkuid()])[0]
        auth = self.args.get('auth', [self.site._mkuid()])[0]
        explain = self.args.get('explain', ['yes'])[0] == 'yes'
        try:
            self.session = self.site.getSession(uid, auth, explain)
        except KeyError:
            self.session = self.site.makeSession(uid, auth, explain)
        self.session.touch()
        return self.session

    def findProxiedIP(self):
        """Return the IP address of the client who submitted this request,
        making an attempt to determine the actual IP through the proxy.
        Returns the client IP address (type: str )"""

        # FIXME: we shouldn't trust these headers so completely because
        # they can be easily forged.  Loic had the idea that we should
        # have a list of trusted proxies.  bkuhn was thinking we should
        # figure a way to log both the real IP and proxier IP.  Anyway,
        # sr#2157 remains open for this reason.

        if self.getHeader('x-forwarded-for'):
            return ('x-forwarded-for', self.getHeader('x-forwarded-for'))
        elif self.getHeader('x-cluster-client-ip'):
            return ('x-cluster-client-ip', self.getHeader('x-cluster-client-ip'))
        else:
            return ('client-ip', server.Request.getClientIP(self))

class Session(server.Session):

    def __init__(self, site, uid, auth, explain):
        server.Session.__init__(self, site, uid)
        self._log = log.getChild(self.__class__.__name__)
        self.auth = auth
        self.avatar = site.resource.service.createAvatar()
        self.explain_default = explain
        self.avatar.queuePackets()
        self.avatar.setDistributedArgs(uid, auth)
        if self.explain_default:
            self.avatar.setExplain(PacketPokerExplain.ALL)
        self.avatar.roles.add(PacketPokerRoles.PLAY)
        self.expired = False

    def expire(self):
        server.Session.expire(self)
        self.site.resource.service.forceAvatarDestroy(self.avatar)
        del self.avatar
        self.expired = True
        
    def logout(self):
        assert self.expired == True
        self.site.logoutSession(self)
            
class PokerResource(resource.Resource):

    def __init__(self, service):
        self._log = log.getChild(self.__class__.__name__)
        resource.Resource.__init__(self)
        self.service = service
        self.isLeaf = True

    def render(self, request):
        arg = ""
        request.content.seek(0, 0)
        jsonp = request.args.get('jsonp', [''])[0]
        if jsonp:
            data = request.args.get('packet', [''])[0]
        elif 'packet' in request.args:
            data = request.args['packet'][0];
        else:
            data = request.content.read()
        if "PacketPing" not in data:
            host, port = request.findProxiedIP()
            self._log.debug("(%s:%s) render %s", host, port, data)

        try:
            arg = simplejson.loads(data, encoding = 'utf-8')
        except Exception:
            resp = 'invalid request'
            request.setResponseCode(http.BAD_REQUEST)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(resp)))
            return resp
        
        arg = fromutf8(arg)
        
        (packet, packet_type_numeric) = arg2packet(arg)
        
        deferred = defer.succeed(None)

        if request.site.pipes:
            request.site.pipe(deferred, request, packet)

        def pipesFailed(reason):
            #
            # Report only if the request has not been finished already.
            # It is the responsibility of each filter to handle errors
            # either by passing them on the errback chain or by filling
            # the request with a proper report.
            #
            body = reason.getTraceback()
            if not request.finished:
                request.setResponseCode(http.INTERNAL_SERVER_ERROR)
                request.setHeader('content-type',"text/html")
                request.setHeader('content-length', str(len(body)))
                request.write(body)
            if request.code != 200:
                host, port = request.findProxiedIP()
                self._log.warn("(%s:%s) %s", host, port, body)
            if not (request.finished or request._disconnected):
                request.finish()
                    
            #
            # Return a value that is not a Failure so that the next
            # incoming request is accepted (otherwise the server keeps
            # returning error on every request)
            #
            return True

        deferred.addCallback(lambda result: self.deferRender(request, jsonp, packet, data, packet_type_numeric))
        deferred.addErrback(pipesFailed)
        return server.NOT_DONE_YET

    def deferRender(self, request, jsonp, packet, data, packet_type_numeric):
        if request.finished:
            #
            # For instance : the request was reverse-proxied to a server.
            #
            return True
        
        session = request.getSession()
        d = defer.maybeDeferred(session.avatar.handleDistributedPacket, request, packet, data)
        
        def render(packets,session = None):
            host, port = request.findProxiedIP()
            self._log.debug("(%s:%s) render %s returns %s", host, port, data, packets)
            #
            # update the session information if the avatar changed
            # session is reloaded because the session object could have changed in the meantime
            #
            # *do not* update/expire/persist session if handling
            # PacketPokerLongPollReturn
            #
            if packet.type != PACKET_POKER_LONG_POLL_RETURN:
                if not session or not hasattr(session,'avatar'):
                    self._log.debug("(%s:%s) recreating session", host, port)
                    session = request.getSession()
                session.site.updateSession(session)
                session.site.persistSession(session)
            
            #
            # if the sent packet was a logout packet, expire his session 
            # and log the user out.
            # 
            if packet.type == PACKET_LOGOUT:
                session.expire()
                session.logout()
            #
            # Format answer
            #
            

            packets_encoded = Packet.JSON.encode(list(packets2maps(packets, packet_type_numeric)))
            result = '%s(%s)' % (jsonp,packets_encoded) if jsonp else packets_encoded

            content_type = 'application/javascript' if jsonp else 'application/json'
             
            request.setHeader("content-type", '%s; charset=utf-8' % content_type)
            request.setHeader("content-length", str(len(result)))
            request.write(result)
            
            if not (request.finished or request._disconnected):
                request.finish()
                
            return True
        def processingFailed(reason):
            # session was reloaded (and expired) because the session object could have changed in the meantime
            # no manual session expiration anymore!
            # request.getSession().expire()
            
            error_trace = reason.getTraceback()
            host = request.findProxiedIP()[1]
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            
            body = "Internal Server Error" if host != '127.0.0.1' else error_trace
            request.setHeader('content-length', str(len(body)))
            request.setHeader('content-type',"text/plain")
            request.write(body)
            request.finish()
            
            self._log.error("%s => %s", host, error_trace)
            
            return True
        d.addCallbacks(render, processingFailed, (session,))
        return d

class PokerImageUpload(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self._log = log.getChild(self.__class__.__name__)
        self.service = service
        self.deferred = defer.succeed(None)
        self.isLeaf = True

    def render(self, request):
        self._log.debug("render %s", request.content.read())
        request.content.seek(0, 0)
        self.deferred.addCallback(lambda result: self.deferRender(request))
        def failed(reason):
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.write(body)
            request.connectionLost(reason)
            self._log.error("%s", body)
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

class PokerTourneyStartResource(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self._log = log.getChild(self.__class__.__name__)
        self.service = service
        self.deferred = defer.succeed(None)
        self.isLeaf = True

    def render(self, request):
        self._log.debug("render %s", request)
        tourney_serial = request.args['tourney_serial'][0]
        self.service.tourneyNotifyStart(int(tourney_serial))
        body = 'OK'
        request.setHeader('content-type',"text/html")
        request.setHeader('content-length', str(len(body)))
        request.write(body)
        return True

class PokerAvatarResource(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self._log = log.getChild(self.__class__.__name__)
        self.service = service
        self.deferred = defer.succeed(None)
        self.isLeaf = True

    def render(self, request):
        self._log.debug("render %s", request.content.read())
        request.content.seek(0, 0)
        serial = int(request.path.split('/')[-1])
        self.deferred.addCallback(lambda result: self.deferRender(request, serial))
        def failed(reason):
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.write(body)
            request.connectionLost(reason)
            self._log.error("%s", body)
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
        self._log = log.getChild(self.__class__.__name__)
        cookieTimeout = settings.headerGetInt("/server/@cookie_timeout")
        if cookieTimeout > 0:
            self.cookieTimeout = cookieTimeout
        else:
            self.cookieTimeout = 1200
        sessionTimeout = settings.headerGetInt("/server/@session_timeout")
        if sessionTimeout > 0:
            self.sessionFactory.sessionTimeout = sessionTimeout
        self.memcache = None
        self.pipes = []
        for path in settings.header.xpathEval("/server/rest_filter"):
            module = imp.load_source("poker_pipe", path.content)
            self.pipes.append(getattr(module, "rest_filter"))
        resthost = settings.headerGetProperties("/server/resthost")
        if resthost:
            resthost = resthost[0]
            self.resthost = ( resthost['host'], int(resthost['port']), resthost['path'] )
        else:
            self.resthost = None

    def pipe(self, d, request, packet):
        if self.pipes:
            for pipe in self.pipes:
                d.addCallback(lambda x: defer.maybeDeferred(pipe, self, request, packet))

    #
    # prevent calling the startFactory method of site.Server
    # to disable logging.
    #
    def startFactory(self):
#       FIXME !
#        self.memcache = self.resource.service.memcache
        from twisted.internet import reactor
        def loadLater(): 
            self.memcache = self.resource.service.memcache
        reactor.callLater(0,loadLater)
        
    def stopFactory(self): 
        for key in self.sessions.keys():
            self.sessions[key].expire()
        
    def persistSession(self, session):
        if len(session.avatar.tables) <= 0 and len(session.avatar.tourneys) <= 0 and (not session.avatar.explain or len(session.avatar.explain.games.getAll()) <= 0):
            session.expire()
            return False
        is_explain_resthost = self.resthost and session.avatar.explain
        if is_explain_resthost:
            session_resthost = self.memcache.get(session.uid)
            is_new_or_same_resthost = not session_resthost or session_resthost == self.resthost
            if is_new_or_same_resthost:
                self.memcache.set(session.uid, self.resthost, time = self.cookieTimeout)
        return True
        
    def updateSession(self, session):
        serial = session.avatar.getSerial()
        #
        # the session is only updated if the session's avatar object is
        # associated with a user (i.e. it does not have a serial of 0)
        #
        if serial > 0:
            #
            # refresh the memcache entry each time a request is handled
            # because it is how each poker server is informed that
            # a given user is logged in
            #
            self.memcache.set(session.auth, str(serial), time = self.cookieTimeout)

    def logoutSession(self,session):
        session_resthost = self.memcache.get(session.uid)
        is_new_or_same_resthost = not session_resthost or session_resthost == self.resthost
        if is_new_or_same_resthost:
            self.memcache.delete(session.uid)
            self.memcache.delete(session.auth)            
        
    def getSession(self, uid, auth, explain):
        if not isinstance(uid, str):
            raise Exception("uid is not str: '%s' %s" % (uid, type(uid)))
        if not isinstance(auth, str):
            raise Exception("auth is not str: '%s' %s" % (auth, type(auth)))
        memcache_serial = self.memcache.get(auth)
        if memcache_serial == None:
            #
            # If the memcache session is gone, trash the current session
            # if it exists.
            #
            if uid in self.sessions:
                self.sessions[uid].expire()
        else:
            memcache_serial = int(memcache_serial)
            #
            # If a session exists, make sure it is in sync with the memcache
            # serial.
            #
            if uid in self.sessions:
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
                    # If the avatar logout or logged into another serial,
                    # expire the session
                    #
                    if session.avatar.getSerial() != memcache_serial:
                        session.expire()
            if uid not in self.sessions:
                #
                # Create a session with an uid that matches the memcache
                # key
                #
                self.makeSessionFromUidAuth(uid, auth, explain).memcache_serial = memcache_serial
                if memcache_serial > 0:
                    self.sessions[uid].avatar.relogin(memcache_serial)
                
        return self.sessions[uid]
    
    def makeSessionFromUidAuth(self, uid, auth, explain):
        session = self.sessions[uid] = self.sessionFactory(self, uid, auth, explain)
        session.startCheckingExpiration()
        return session
        
    def makeSession(self, uid, auth, explain):
        session = self.makeSessionFromUidAuth(uid, auth, explain)
        session.memcache_serial = 0
        self.memcache.add(auth, str(session.memcache_serial))
        return session

