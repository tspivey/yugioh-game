import io

def msg_flipsummoning(self, data):
	data = io.BytesIO(data[1:])
	code = self.read_u32(data)
	location = self.read_u32(data)
	c = location & 0xff
	loc = (location >> 8) & 0xff;
	seq = (location >> 16) & 0xff
	card = self.get_card(c, loc, seq)
	self.cm.call_callbacks('flipsummoning', card)
	return data.read()

def flipsummoning(self, card):
	cpl = self.players[card.controller]
	players = self.players + self.watchers
	for pl in players:
		spec = card.get_spec(pl)
		pl.notify(pl._("{player} flip summons {card} ({spec}).")
		.format(player=cpl.nickname, card=card.get_name(pl), spec=spec))

MESSAGES = {64: msg_flipsummoning}

CALLBACKS = {'flipsummoning': flipsummoning}
