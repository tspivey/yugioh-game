import io

def msg_win(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	reason = self.read_u8(data)
	self.cm.call_callbacks('win', player, reason)
	return data.read()

def win(self, player, reason):
	if player == 2:
		self.room.announce_draw()
		self.end()
		return

	if self.tag is True:
		winners = [self.players[player], self.tag_players[player]]
		losers = [self.players[1 - player], self.tag_players[1 - player]]
	else:
		winners = [self.players[player]]
		losers = [self.players[1 - player]]

	l_reason = lambda p: p.strings['victory'][reason]

	for w in winners:
		if self.tag:
			w.notify(w._("%s and you won (%s).")%(winners[1 - winners.index(w)].nickname, l_reason(w)))
		else:
			w.notify(w._("You won (%s).") % l_reason(w))
	for l in losers:
		if self.tag is True:
			l.notify(l._("%s and you lost (%s).")%(losers[1 - losers.index(l)].nickname, l_reason(l)))
		else:
			l.notify(l._("You lost (%s).") % l_reason(l))

	for pl in self.watchers:
		if pl.watching is True:
			if self.tag is True:
				w = "team "+winners[0].nickname+", "+winners[1].nickname
			else:
				w = winners[0].nickname
			pl.notify(pl._("%s won (%s).") % (w, l_reason(pl)))

	self.room.announce_victory(self.players[player])
	self.end()

MESSAGES = {5: msg_win}

CALLBACKS = {'win': win}
