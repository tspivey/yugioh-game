import io

from ygo import globals

def msg_win(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	reason = self.read_u8(data)
	self.cm.call_callbacks('win', player, reason)
	return data.read()

def win(self, player, reason):
	if player == 2:
		if self.tag is True:
			pl0 = self.players[0].nickname+", "+self.tag_players[0].nickname
			pl1 = self.players[1].nickname+", "+self.tag_players[1].nickname
		else:
			pl0 = self.players[0].nickname
			pl1 = self.players[1].nickname
		if not self.private:
			for pl in globals.server.get_all_players():
				globals.server.announce_challenge(pl, pl._("%s and %s ended up in a draw.")%(pl._("team %s")%(pl0), pl._("team %s")%(pl1)))

		self.end()
		return
	losers = []
	if self.tag is True:
		winners = [self.players[player], self.tag_players[player]]
		losers = [self.players[1 - player], self.tag_players[1 - player]]
	else:
		winners = [self.players[player]]
		losers = [self.players[1 - player]]
	for w in winners:
		reason_str = globals.strings[w.language]['victory'][reason]
		if self.tag:
			w.notify(w._("%s and you won (%s).")%(winners[1 - winners.index(w)].nickname, reason_str))
		else:
			w.notify(w._("You won (%s).") % reason_str)
	for l in losers:
		reason_str = globals.strings[l.language]['victory'][reason]
		if self.tag is True:
			l.notify(l._("%s and you lost (%s).")%(losers[1 - losers.index(l)].nickname, reason_str))
		else:
			l.notify(l._("You lost (%s).") % reason_str)

	for pl in self.watchers:
		if pl.watching is True:
			reason_str = globals.strings[pl.language]['victory'][reason]
			if self.tag is True:
				w = pl._("team %s")%(winners[0].nickname+", "+winners[1].nickname)
			else:
				w = winners[0].nickname
			pl.notify(pl._("%s won (%s).") % (w, reason_str))
	if not self.private:
		for pl in globals.server.get_all_players():
			reason_str = globals.strings[pl.language]['victory'][reason]
			if self.tag is True:
				w = pl._("team %s")%(winners[0].nickname+", "+winners[1].nickname)
				l = pl._("team %s")%(losers[0].nickname+", "+losers[1].nickname)
			else:
				w = winners[0].nickname
				l = losers[0].nickname
			globals.server.announce_challenge(pl, pl._("%s won the duel between %s and %s (%s).") % (w, w, l, reason_str))
	self.end()

MESSAGES = {5: msg_win}

CALLBACKS = {'win': win}
