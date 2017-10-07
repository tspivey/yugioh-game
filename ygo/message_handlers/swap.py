import io

from ygo.card import Card

def msg_swap(self, data):
	data = io.BytesIO(data[1:])

	code1 = self.read_u32(data)
	location1 = self.read_u32(data)
	code2 = self.read_u32(data)
	location2 = self.read_u32(data)

	card1 = Card(code1)
	card1.set_location(location1)
	card2 = Card(code2)
	card2.set_location(location2)
	self.cm.call_callbacks('swap', card1, card2)

	return data.read()

def swap(self, card1, card2):
	for p in self.watchers+self.players:
		for card in (card1, card2):
			plname = self.players[card.controller].nickname
			s = card.get_spec(p.duel_player)
			p.notify(p._("card {name} swapped control towards {plname} and is now located at {targetspec}.").format(plname=plname, targetspec=s, name=card.get_name(p)))

MESSAGES = {55: msg_swap}

CALLBACKS = {'swap': swap}
