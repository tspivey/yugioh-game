import io

from ygo.constants import __
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
			pl0 = "team "+self.players[0].nickname+", "+self.tag_players[0].nickname
			pl1 = "team "+self.players[1].nickname+", "+self.tag_players[1].nickname
		else:
			pl0 = self.players[0].nickname
			pl1 = self.players[1].nickname
		if not self.private:
			globals.server.challenge.send_message(None, __("{player1} and {player2} ended up in a draw."), player1 = pl0, player2 = pl1)

		self.end()
		return
	losers = []
	if self.tag is True:
		winners = [self.players[player], self.tag_players[player]]
		losers = [self.players[1 - player], self.tag_players[1 - player]]
	else:
		winners = [self.players[player]]
		losers = [self.players[1 - player]]
	l_reason = lambda p: globals.strings[p.language]['victory'][reason]
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
	if not self.private:
		if self.tag is True:
			w = "team "+winners[0].nickname+", "+winners[1].nickname
			l = "team "+losers[0].nickname+", "+losers[1].nickname
		else:
			w = winners[0].nickname
			l = losers[0].nickname
		globals.server.challenge.send_message(None, __("{winner} won the duel between {player1} and {player2} ({reason})."), winner = w, player1 = w, player2 = l, reason = l_reason)
	self.end()

MESSAGES = {5: msg_win}

CALLBACKS = {'win': win}
