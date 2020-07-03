import io

from ygo.constants import LOCATION

def msg_confirm_cards(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	size = self.read_u8(data)
	cards = []
	for i in range(size):
		code = self.read_u32(data)
		c = self.read_u8(data)
		l = LOCATION(self.read_u8(data))
		s = self.read_u8(data)
		card = self.get_card(c, l, s)
		cards.append(card)
	self.cm.call_callbacks('confirm_cards', player, cards)
	return data.read()

def confirm_cards(self, player, cards):
	player = self.players[cards[0].controller]
	op = self.players[1 - cards[0].controller]
	players = [op] + self.watchers
	for pl in players:
		pl.notify(pl._("{player} shows you {count} cards.")
			.format(player=player.nickname, count=len(cards)))
		for i, c in enumerate(cards):
			pl.notify("%s: %s" % (i + 1, c.get_name(pl)))
			self.revealed[(c.controller, c.location, c.sequence)] = True

MESSAGES = {31: msg_confirm_cards}

CALLBACKS = {'confirm_cards': confirm_cards}
