import logging
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerFactory, \
     WebSocketServerProtocol
from gsb import Caller
import game


class WSProtocol(WebSocketServerProtocol):

	def onMessage(self, payload, isBinary):
		if not isBinary:
			self.parser.handle_line(self, payload.decode())

	def sendLine(self, line):
		if hasattr(line, 'encode'):
			line = line.encode()
		self.sendMessage(line)

	def onOpen(self):
		game.server.on_connect(Caller(self))
		self.web = True
		self.parser = game.server.default_parser

	def onConnect(self, request):
		self.server = game.server
		self.server.connections.append(self)
		self._parser = None
		self.encode_args = ('utf-8', 'replace')
		self.decode_args = ('utf-8', 'ignore')


	def onClose(self, wasClean, code, reason):
		if self in game.server.connections:
			game.server.connections.remove(self)
			game.server.on_disconnect(Caller(self))

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
