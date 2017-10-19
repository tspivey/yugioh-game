import io

def msg_recover(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	amount = self.read_u32(data)
	self.cm.call_callbacks('recover', player, amount)
	return data.read()

def recover(self, player, amount):
	new_lp = self.lp[player] + amount
	pl = self.players[player]
	op = self.players[1 - player]
	pl.notify(pl._("Your lp increased by %d, now %d") % (amount, new_lp))
	op.notify(op._("%s's lp increased by %d, now %d") % (self.players[player].nickname, amount, new_lp))
	for pl in self.watchers:
		pl.notify(pl._("%s's lp increased by %d, now %d") % (self.players[player].nickname, amount, new_lp))
	self.lp[player] += amount

MESSAGES = {92: msg_recover}

CALLBACKS = {'recover': recover}
