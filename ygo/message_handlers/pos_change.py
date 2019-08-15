import io

from ygo.card import Card
from ygo.constants import LOCATION

def msg_pos_change(self, data):
	data = io.BytesIO(data[1:])
	code = self.read_u32(data)
	card = Card(code)
	card.controller = self.read_u8(data)
	card.location = LOCATION(self.read_u8(data))
	card.sequence = self.read_u8(data)
	prevpos = self.read_u8(data)
	card.position = self.read_u8(data)
	self.cm.call_callbacks('pos_change', card, prevpos)
	return data.read()

def pos_change(self, card, prevpos):
	cpl = self.players[card.controller]
	op = self.players[1 - card.controller]
	cs = card.get_spec(cpl)
	cso = card.get_spec(op)
	cpl.notify(cpl._("The position of card %s (%s) was changed to %s.") % (cs, card.get_name(cpl), card.get_position(cpl)))
	op.notify(op._("The position of card %s (%s) was changed to %s.") % (cso, card.get_name(op), card.get_position(op)))
	for w in self.watchers:
		cs = card.get_spec(w)
		w.notify(w._("The position of card %s (%s) was changed to %s.") % (cs, card.get_name(w), card.get_position(w)))

MESSAGES = {53: msg_pos_change}

CALLBACKS = {'pos_change': pos_change}
