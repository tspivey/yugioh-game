import gsb

from .utils import forward_error

class Parser(gsb.Parser):

	def on_error(self, caller):
		forward_error()
		gsb.Parser.on_error(self, caller)
