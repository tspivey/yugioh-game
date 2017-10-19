import gsb

from .duel_parser import DuelParser

class yes_or_no_parser(gsb.Parser):

	def __init__(self, question, yes=None, no=None, restore_parser=None, *args, **kwargs):
		self.question = question
		self.yes = yes
		self.no = no
		self.restore_parser = restore_parser
		super().__init__(*args, **kwargs)

	def on_attach(self, connection, old_parser):
		for key in DuelParser.commands.keys():
			self.commands[key] = DuelParser.commands[key]
		connection.notify(self.question)

	def huh(self, caller):
		if caller.text.lower().startswith('y'):
			self.yes(caller)
		elif caller.text.lower().startswith('n'):
			self.no(caller)
		else:
			caller.connection.notify(caller.connection.player._("Please enter y or n."))
			caller.connection.notify(self.question)
			return
		caller.connection.parser = self.restore_parser
