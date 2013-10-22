
import twisted.application.service as _service
import twisted.internet.protocol as _protocol
import msgpack as _msgpack
from twisted.internet import reactor

class PubService(_service.Service):
    
    def __init__(self, service):
        service.pub = self
        self._service = service
        self._avatars = set()
        self._subscriptions = set()
        # self.dummy()

    def createAvatar(self):
        return PubAvatar(self)

    def doStart(self):
        pass

    def doStop(self):
        pass

    def buildProtocol(self, address):
        avatar = self.createAvatar()
        protocol = PubProtocol(avatar)
        avatar.setProtocol(protocol)
        return protocol

    def publish(self, channel, message):
        for avatar, subscription in self._subscriptions:
            if channel.startswith(subscription):
                avatar.send(channel, message)

    def dummy(self):
        self.publish('user.2', {'test': 1})
        self.publish('user.177', {'test': 1})
        reactor.callLater(1, self.dummy)

    def subscribe(self, avatar, subscription):
        s = (avatar, subscription)
        self._subscriptions.add(s)

    def unsubscribe(self, avatar, subscription):
        s = (avatar, subscription)
        self._subscriptions.remove(s)        

class PubAvatar():

    def __init__(self, service):
        self._service = service
        self._protocol = None
        self._subscriptions = set()

    def setProtocol(self, protocol):
        self._protocol = protocol

    def handleCommand(self, cmd, args):
        if cmd == 'subscribe':
            subscription, = args
            self._subscriptions.add(subscription)
            self._service.subscribe(self, subscription)
        elif cmd == 'unsubscribe':
            subscription, = args
            self._subscriptions.remove(subscription)
            self._service.unsubscribe(self, subscription)
        else:
            raise Exception("Command not defined")

    def handleConnectionLost(self, reason):
        for subscription in self._subscriptions:
            self._service.unsubscribe(self, subscription)

    def send(self, channel, message):
        if self._protocol:
            self._protocol.send(channel, message)

class PubProtocol(_protocol.Protocol):

    def __init__(self, avatar):
        self._unpacker = _msgpack.Unpacker()
        self._avatar = avatar

    def connectionLost(self, reason):
        self._avatar.handleConnectionLost(reason)

    def dataReceived(self, data):
        self._unpacker.feed(data)
        for cmd, args in self._unpacker:
            self._avatar.handleCommand(cmd, args)

    def send(self, channel, message):
        if self.transport:
            self.transport.write(_msgpack.packb((channel, message)))

