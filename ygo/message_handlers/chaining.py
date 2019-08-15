import io

from ygo.card import Card
from ygo.constants import TYPE

def msg_chaining(self, data):
	data = io.BytesIO(data[1:])
	code = self.read_u32(data)
	card = Card(code)
	card.set_location(self.read_u32(data))
	tc = self.read_u8(data)
	tl = self.read_u8(data)
	ts = self.read_u8(data)
	desc = self.read_u32(data)
	cs = self.read_u8(data)
	self.cm.call_callbacks('chaining', card, tc, tl, ts, desc, cs)
	return data.read()

def chaining(self, card, tc, tl, ts, desc, cs):
	c = card.controller
	o = 1 - c
	n = self.players[c].nickname
	self.chaining_player = c
	if card.type & TYPE.SPELL:
		if self.players[c].soundpack:
			self.players[c].notify("### activate_spell")
		if self.players[o].soundpack:
			self.players[o].notify("### activate_spell")
	elif card.type & TYPE.TRAP:
		if self.players[c].soundpack:
			self.players[c].notify("### activate_trap")
		if self.players[o].soundpack:
			self.players[o].notify("### activate_trap")

	self.players[c].notify(self.players[c]._("Activating {0} ({1})").format(card.get_spec(self.players[c]), card.get_name(self.players[c])))
	self.players[o].notify(self.players[o]._("{0} activating {1} ({2})").format(n, card.get_spec(self.players[o]), card.get_name(self.players[o])))
	for pl in self.watchers:
		if card.type & TYPE.SPELL:
			if pl.soundpack:
				pl.notify("### activate_spell")
		if card.type & TYPE.TRAP:
			if pl.soundpack:
				pl.notify("### activate_trap")
		pl.notify(pl._("{0} activating {1} ({2})").format(n, card.get_spec(pl), card.get_name(pl)))

MESSAGES = {70: msg_chaining}

CALLBACKS = {'chaining': chaining}
