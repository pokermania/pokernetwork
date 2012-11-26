
from zope.interface import Interface, implements

from twisted.internet.interfaces import ITransport
from twisted.internet import error, reactor
from twisted.python.failure import Failure

class PairedTransport:
    implements(ITransport)
    
    def __init__(self, hostAddress=None, peerAddress=None, protocol=None, foreignProtocol=None):
        self.hostAddr = hostAddress
        self.peerAddr = peerAddress
        self.protocol = protocol
        self.foreignProtocol = foreignProtocol
        self.connected = True
    
    def write(self, data):
        if isinstance(data, unicode):
            raise TypeError("Data must not be unicode")
        if not self.foreignProtocol:
            raise Exception("Need a foreign protocol")
        self._write(data)
    
    def _write(self, data):
        self.foreignProtocol.dataReceived(data)
        
    def writeSequence(self, data):
        self.write(''.join(data))
        
    def loseConnection(self):
        if self.connected:
            self.connected = False
            self.protocol.connectionLost(Failure(error.ConnectionDone("Bye.")))
            
    def setTcpKeepAlive(self, *a, **kw):
        pass

class PairedDeferredTransport(PairedTransport):
    def _write(self, data):
        reactor.callLater(0, self.foreignProtocol.dataReceived, data)
    
    def loseConnection(self):
        if self.connected:
            self.connected = False
            reactor.callLater(0, self._loseConnection)
    
    def _loseConnection(self):
        self.protocol.connectionLost(Failure(error.ConnectionDone("Bye.")))
        self.foreignProtocol.transport.loseConnection()