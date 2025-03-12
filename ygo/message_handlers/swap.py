import io

from ygo.card import Card
from ygo.constants import *

def msg_swap(self, data):
	data = io.BytesIO(data[1:])

	code1 = self.read_u32(data)
	location1 = self.read_location(data)
	code2 = self.read_u32(data)
	location2 = self.read_location(data)

	card1 = Card(code1)
	card1.set_location(location1)
	card2 = Card(code2)
	card2.set_location(location2)
	self.cm.call_callbacks('swap', card1, card2)

	return data.read()

def swap(self, card1, card2):
	for p in self.watchers+self.players:
		for card in (card1, card2):
			plname = self.players[1 - card.controller].nickname
			s = card.get_spec(p)
			if card.position & POSITION.FACEDOWN and p.watching is True:
				cname = p._("%s card")%(card.get_position(p))
			else:
				cname = card.get_name(p)
			p.notify(p._("card {name} swapped control towards {plname} and is now located at {targetspec}.").format(plname=plname, targetspec=s, name=cname))

MESSAGES = {55: msg_swap}

CALLBACKS = {'swap': swap}
