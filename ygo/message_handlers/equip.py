import io

def msg_equip(self, data):
	data = io.BytesIO(data[1:])
	loc = self.read_location(data)
	target = self.read_location(data)
	card = self.get_card(loc.controller, loc.location, loc.sequence)
	target = self.get_card(target.controller, target.location, target.sequence)
	self.cm.call_callbacks('equip', card, target)
	return data.read()

def equip(self, card, target):
	for pl in self.players + self.watchers:
		c = self.cardlist_info_for_player(card, pl)
		t = self.cardlist_info_for_player(target, pl)
		pl.notify(pl._("{card} equipped to {target}.")
			.format(card=c, target=t))

MESSAGES = {93: msg_equip}

CALLBACKS = {'equip': equip}
