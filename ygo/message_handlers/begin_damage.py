def msg_begin_damage(self, data):
	self.cm.call_callbacks('begin_damage')
	return data[1:]

def begin_damage(self):
	for pl in self.players + self.watchers:
		pl.notify(pl._("begin damage"))

MESSAGES = {113: msg_begin_damage}

CALLBACKS = {'begin_damage': begin_damage}
