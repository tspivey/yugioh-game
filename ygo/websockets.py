import logging
from twisted.internet import reactor
from twisted.internet import ssl
from autobahn.twisted.websocket import WebSocketServerFactory, \
     WebSocketServerProtocol
from gsb import Caller

import globals

class WSProtocol(WebSocketServerProtocol):

	def onMessage(self, payload, isBinary):
		if not isBinary:
			self.parser.handle_line(self, payload.decode())

	def sendLine(self, line):
		if hasattr(line, 'encode'):
			line = line.encode()
		self.sendMessage(line)

	def onOpen(self):
		globals.server.on_connect(Caller(self))
		self.web = True
		self.parser = globals.server.default_parser

	def onConnect(self, request):
		self.server = globals.server
		self.server.connections.append(self)
		self._parser = None
		self.encode_args = ('utf-8', 'replace')
		self.decode_args = ('utf-8', 'ignore')


	def onClose(self, wasClean, code, reason):
		if self in globals.server.connections:
			globals.server.connections.remove(self)
			globals.server.on_disconnect(Caller(self))

	@property
	def parser(self):
		"""Get the current parser."""
		return self._parser

	@parser.setter
	def parser(self, value):
		"""Set self._parser."""
		old_parser = self._parser
		if old_parser is not None:
			old_parser.on_detach(self, value)
		self._parser = value
		if value is not None:
			value.on_attach(self, old_parser)

	def notify(self, *args, **kwargs):
		"""Notify this connection of something."""
		self.server.notify(self, *args, **kwargs)

def start_websocket_server(port, cert, key):
	if cert:
		context_factory = ssl.DefaultOpenSSLContextFactory(key, cert)
		url = 'wss://0.0.0.0:%d' % port
	else:
		context_factory = None
		url = 'ws://0.0.0.0:%d' % port
	factory = WebSocketServerFactory(url)
	factory.protocol = WSProtocol
	if context_factory:
		globals.websocket_server = reactor.listenSSL(port, factory, context_factory)
	else:
		globals.websocket_server = reactor.listenTCP(port, factory)
