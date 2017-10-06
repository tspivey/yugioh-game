import io

from ygo import globals

def msg_toss_coin(self, data, dice=False):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	count = self.read_u8(data)
	options = [self.read_u8(data) for i in range(count)]
	if dice:
		self.cm.call_callbacks('toss_dice', player, options)
	else:
		self.cm.call_callbacks('toss_coin', player, options)
	return data.read()

def toss_coin(self, player, options):
	players = []
	players.extend(self.players + self.watchers)
	for pl in players:
		s = globals.strings[pl.language]['system'][1623] + " "
		opts = [globals.strings[pl.language]['system'][60] if opt else globals.strings[pl.language]['system'][61] for opt in options]
		s += ", ".join(opts)
		pl.notify(s)

def toss_dice(self, player, options):
	opts = [str(opt) for opt in options]
	players = []
	players.extend(self.players + self.watchers)
	for pl in players:
		s = globals.strings[pl.language]['system'][1624] + " "
		s += ", ".join(opts)
		pl.notify(s)

def msg_toss_dice(self, *args, **kwargs):
	kwargs['dice'] = True
	self.msg_toss_coin(*args, **kwargs)

MESSAGES = {130: msg_toss_coin, 131: msg_toss_dice}

CALLBACKS = {'toss_coin': toss_coin, 'toss_dice': toss_dice}
