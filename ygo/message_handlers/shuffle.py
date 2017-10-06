import io

def msg_shuffle(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	self.cm.call_callbacks('shuffle', player)
	return data.read()

def shuffle(self, player):
	pl = self.players[player]
	pl.notify(pl._("you shuffled your deck."))
	for pl in self.watchers+[self.players[1 - player]]:
		pl.notify(pl._("%s shuffled their deck.")%(self.players[player].nickname))

MESSAGES = {32: msg_shuffle}

CALLBACKS = {'shuffle': shuffle}
