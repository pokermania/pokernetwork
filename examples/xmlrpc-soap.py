#
# Hand made test support for XML-RPC and SOAP server support
#
# python xmlrpc-soap.py SOAP
# python xmlrpc-soap.py XML-RPC
#
import sys
from pprint import pprint
from re import match
from twisted.web.xmlrpc import Proxy
from twisted.internet import reactor
import SOAPpy
from twisted.web import server, resource, client

data = {}

def printValue(value):
    pprint(value)

def printError(error):
    print 'error', error

class SOAPProxy:
    """A Proxy for making remote SOAP calls.

    Pass the URL of the remote SOAP server to the constructor.

    Use proxy.callRemote('foobar', 1, 2) to call remote method
    'foobar' with args 1 and 2, proxy.callRemote('foobar', x=1)
    will call foobar with named argument 'x'.
    """

    # at some point this should have encoding etc. kwargs
    def __init__(self, url, namespace=None):
        self.url = url

    def _cbGotResult(self, result):
        return SOAPpy.simplify(SOAPpy.parseSOAPRPC(result))
        
    def callRemote(self, method, *args, **kwargs):
        print "callRemote: " + str(args)
        kwargs.setdefault('headers', {})['Content-Type'] = 'text/xml'
        payload = SOAPpy.buildSOAP(args=args, kw=kwargs, method=method,
                                   header=None, namespace=None)
        return client.getPage(self.url, postdata=payload, method="POST",
                              headers = kwargs['headers']
                              ).addCallback(self._cbGotResult)


if sys.argv[1] == 'SOAP':
    print "SOAP"
    proxy = SOAPProxy('http://localhost:19482/SOAP')
else:
    print "XML-RPC"
    proxy = Proxy('http://localhost:19482/RPC2')

def accountCreated(value):
    printValue(value)
    data['serial'] = value['Result'][0]['serial']
    print "Account created, got serial %d" % data['serial']
    
    proxy.callRemote('packets', ("use sessions",
                                 { 'type': 'PacketLogin', 'name': 'dachary11', 'password': 'dachary1' }
                                 )).addCallbacks(loggedIn, printError)

def loggedIn(value):
    printValue(value)
#    data['cookie'] = { 'TWISTED_SESSION': match("TWISTED_SESSION=(.*);", value['Result'][1]['cookie']).group(1) }
    data['cookie'] = { 'Cookie': value['Result'][1]['cookie'] }
    print "Logged in, session " + str(data['cookie'])
    
    proxy.callRemote('packets', ("use sessions",
                                 { 'type': 'PacketPokerTourneySelect', 'string': 'n\tsit_n_go' }
                                 ), headers = data['cookie']).addCallbacks(tableList, printError)

def tableList(value):
    printValue(value)

    proxy.callRemote('packets', ("use sessions",
                                 { 'type': 'PacketLogout' }
                                 ), headers = data['cookie']).addCallbacks(printValue, printError)
    
#
# The arguments MUST be in a list. If they are not the server will
# bark. When using the nusoap php module, this inclusion is implicit.
#
proxy.callRemote('packets', ("no sessions",
                 {'type': 'PacketPokerCreateAccount', 'name': 'dachary11', 'password': 'dachary1', 'email': 'loi@senga.org'}
                 )).addCallbacks(accountCreated, printError)


reactor.callLater(10, reactor.stop)
reactor.run()

