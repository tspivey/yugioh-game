import io

def msg_damage(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	amount = self.read_u32(data)
	self.cm.call_callbacks('damage', player, amount)
	return data.read()

def damage(self, player, amount):
	new_lp = self.lp[player]-amount
	pl = self.players[player]
	op = self.players[1 - player]
	pl.notify(pl._("Your lp decreased by %d, now %d") % (amount, new_lp))
	op.notify(op._("%s's lp decreased by %d, now %d") % (self.players[player].nickname, amount, new_lp))
	for pl in self.watchers:
		pl.notify(pl._("%s's lp decreased by %d, now %d") % (self.players[player].nickname, amount, new_lp))
	self.lp[player] -= amount

MESSAGES = {91: msg_damage}

CALLBACKS = {'damage': damage}
