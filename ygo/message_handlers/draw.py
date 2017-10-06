import io

from ygo.card import Card

def msg_draw(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	drawed = self.read_u8(data)
	cards = []
	for i in range(drawed):
		c = self.read_u32(data)
		card = Card(c & 0x7fffffff)
		cards.append(card)
	self.cm.call_callbacks('draw', player, cards)
	return data.read()

def draw(self, player, cards):
	pl = self.players[player]
	pl.notify(pl._("Drew %d cards:") % len(cards))
	for i, c in enumerate(cards):
		pl.notify("%d: %s" % (i+1, c.get_name(pl)))
	op = self.players[1 - player]
	op.notify(op._("Opponent drew %d cards.") % len(cards))
	for w in self.watchers:
		w.notify(w._("%s drew %d cards.") % (pl.nickname, len(cards)))

MESSAGES = {90: msg_draw}

CALLBACKS = {'draw': draw}
