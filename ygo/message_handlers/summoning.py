import io

from ygo.card import Card
from ygo.constants import TYPE

def msg_summoned(self, data):
	return data[1:]

def msg_summoning(self, data, special=False):
	data = io.BytesIO(data[1:])
	code = self.read_u32(data)
	card = Card(code)
	card.set_location(self.read_u32(data))
	self.cm.call_callbacks('summoning', card, special=special)
	return data.read()

def summoning(self, card, special=False):
	nick = self.players[card.controller].nickname
	for pl in self.players + self.watchers:
		pos = card.get_position(pl)
		if special:
			if card.type & TYPE.LINK:
				pl.notify(pl._("%s special summoning %s (%d) in %s position.") % (nick, card.get_name(pl), card.attack, pos))
			else:
				pl.notify(pl._("%s special summoning %s (%d/%d) in %s position.") % (nick, card.get_name(pl), card.attack, card.defense, pos))
		else:
			pl.notify(pl._("%s summoning %s (%d/%d) in %s position.") % (nick, card.get_name(pl), card.attack, card.defense, pos))

def msg_summoning_special(self, *args, **kwargs):
	kwargs['special'] = True
	self.msg_summoning(*args, **kwargs)

MESSAGES = {60: msg_summoning, 62: msg_summoning_special, 61: msg_summoned}

CALLBACKS = {'summoning': summoning}
