#
# Hand made test support for XML-RPC and SOAP server support
#
# python xmlrpc-soap.py SOAP
# python xmlrpc-soap.py XML-RPC
#
import sys
from twisted.web.xmlrpc import Proxy
from twisted.internet import reactor
import SOAPpy
from twisted.web import server, resource, client

def printValue(value):
    print repr(value)
    reactor.stop()

def printError(error):
    print 'error', error
    reactor.stop()

class SOAPProxy:
    """A Proxy for making remote SOAP calls.

    Pass the URL of the remote SOAP server to the constructor.

    Use proxy.callRemote('foobar', 1, 2) to call remote method
    'foobar' with args 1 and 2, proxy.callRemote('foobar', x=1)
    will call foobar with named argument 'x'.
    """

    # at some point this should have encoding etc. kwargs
    def __init__(self, url, namespace=None, header=None):
        self.url = url
        self.namespace = namespace
        self.header = header

    def _cbGotResult(self, result):
        return SOAPpy.simplify(SOAPpy.parseSOAPRPC(result))
        
    def callRemote(self, method, *args, **kwargs):
        payload = SOAPpy.buildSOAP(args=args, kw=kwargs, method=method,
                                   header=self.header, namespace=self.namespace)
        return client.getPage(self.url, postdata=payload, method="POST",
                              headers={'content-type': 'text/xml'}
                              ).addCallback(self._cbGotResult)


if sys.argv[1] == 'SOAP':
    print "SOAP"
    proxy = SOAPProxy('http://localhost:19482/SOAP')
else:
    print "XML-RPC"
    proxy = Proxy('http://localhost:19482/RPC2')
proxy.callRemote('packets', "use sessions",
                 {'type': 'PacketLogin', 'name': 'dachary2', 'password': 'dachary1' },
                 {'type': 'PacketPokerSetAccount', 'serial': 222, 'name': 'dachary2', 'password': 'dachary1', 'email': 'loicj@senga.org'},
                 
                 ).addCallbacks(printValue, printError)
reactor.run()

