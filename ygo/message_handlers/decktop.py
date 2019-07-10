import io

from ygo.card import Card

def msg_confirm_decktop(self, data):
	cards = []
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	count = self.read_u8(data)
	for i in range(count):
		code = self.read_u32(data)
		if code & 0x80000000:
			code = code ^ 0x80000000 # don't know what this actually does
		card = Card(code)
		card.controller = self.read_u8(data)
		card.location = self.read_u8(data)
		card.sequence = self.read_u8(data)
		cards.append(card)
		
	self.cm.call_callbacks('confirm_decktop', player, cards)
	return data.read()

def msg_decktop(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	self.read_u8(data) # don't know what this number does
	code = self.read_u32(data)
	if code & 0x80000000:
		code = code ^ 0x80000000 # don't know what this actually does
	self.cm.call_callbacks('decktop', player, Card(code))
	return data.read()

def decktop(self, player, card):
	player = self.players[player]
	for pl in self.players+self.watchers:
		if pl is player:
			pl.notify(pl._("you reveal your top deck card to be %s")%(card.get_name(pl)))
		else:
			pl.notify(pl._("%s reveals their top deck card to be %s")%(player.nickname, card.get_name(pl)))

def confirm_decktop(self, player, cards):
	player = self.players[player]
	for pl in self.players+self.watchers:
		if pl is player:
			pl.notify(pl._("you reveal the following cards from your deck:"))
		else:
			pl.notify(pl._("%s reveals the following cards from their deck:")%(player.nickname))
		for i, c in enumerate(cards):
			pl.notify("%d: %s"%(i+1, c.get_name(pl)))

MESSAGES = {38: msg_decktop, 30: msg_confirm_decktop}

CALLBACKS = {'decktop': decktop, 'confirm_decktop': confirm_decktop}
