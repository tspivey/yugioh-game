import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.parsers.yes_or_no_parser import yes_or_no_parser
from ygo.utils import process_duel

def msg_select_effectyn(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	card = Card(self.read_u32(data))
	card.set_location(self.read_location(data))
	desc = self.read_u64(data)
	self.cm.call_callbacks('select_effectyn', player, card, desc)
	return data.read()

def select_effectyn(self, player, card, desc):
	pl = self.players[player]
	old_parser = pl.connection.parser
	def yes(caller):
		self.set_responsei(1)
		reactor.callLater(0, process_duel, self)
	def no(caller):
		self.set_responsei(0)
		reactor.callLater(0, process_duel, self)
	spec = card.get_spec(pl)
	question = pl._("Do you want to use the effect from {card} in {spec}?").format(card=card.get_name(pl), spec=spec)
	s = card.get_effect_description(pl, desc, True)
	if s != '':
		question += '\n'+s
	pl.notify(yes_or_no_parser, question, yes, no=no, restore_parser=old_parser)

MESSAGES = {12: msg_select_effectyn}

CALLBACKS = {'select_effectyn': select_effectyn}
