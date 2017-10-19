import io

from ygo.card import Card

def msg_tag_swap(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	main_deck_count = self.read_u8(data)
	extra_deck_count = self.read_u8(data)
	extra_p_count = self.read_u8(data)
	hand_count = self.read_u8(data)
	top_card = self.read_u32(data)
	# we don't need the following information, so we trash it
	# that allows us to process all following messages too (if any)
	for i in range(hand_count):
		self.read_u32(data)
	for i in range(extra_deck_count):
		self.read_u32(data)
	self.cm.call_callbacks('tag_swap', player)
	if top_card > 0:
		self.cm.call_callbacks('decktop', player, Card(top_card))
	return data.read()

def tag_swap(self, player):

	# we need to swap around players in
	# 1. self.players
	# 2. self.tag_players
	# 3. self.watchers
	# but because we knew about that, all players have the same indices
	# no matter in which list we'll check them

	current_player = self.players[player]
	new_player = self.tag_players[player]

	self.players[player] = new_player
	self.tag_players[player] = current_player
	self.watchers[player] = current_player

	# we need to inform all players about it

	new_player.notify(new_player._("You switch places with %s and get ready to duel.")%(current_player.nickname))
	current_player.notify(current_player._("You switch places with %s and watch carefully.")%(new_player.nickname))

	for pl in self.players+self.watchers:
		if pl is not current_player and pl is not new_player:
			pl.notify(pl._("%s switches in for %s and continues the duel.")%(new_player.nickname, current_player.nickname))

MESSAGES = {161: msg_tag_swap}

CALLBACKS = {'tag_swap': tag_swap}
