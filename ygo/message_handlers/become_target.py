import io

from ygo.constants import LOCATION, POSITION

def msg_become_target(self, data):
	data = io.BytesIO(data[1:])
	u = self.read_u8(data)
	target = self.read_u32(data)
	tc = target & 0xff
	tl = LOCATION((target >> 8) & 0xff)
	tseq = (target >> 16) & 0xff
	tpos = POSITION((target >> 24) & 0xff)
	self.cm.call_callbacks('become_target', tc, tl, tseq)
	return data.read()

def become_target(self, tc, tl, tseq):
	card = self.get_card(tc, tl, tseq)
	if not card:
		return
	name = self.players[self.chaining_player].nickname
	for pl in self.players + self.watchers:
		spec = card.get_spec(pl)
		tcname = card.get_name(pl)
		if (pl.watching or card.controller != pl.duel_player) and card.position & POSITION.FACEDOWN:
			tcname = pl._("%s card") % card.get_position(pl)
		pl.notify(pl._("%s targets %s (%s)") % (name, spec, tcname))

MESSAGES = {83: msg_become_target}

CALLBACKS = {'become_target': become_target}
