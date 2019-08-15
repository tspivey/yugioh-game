import io

from ygo.constants import POSITION

def msg_attack(self, data):
	data = io.BytesIO(data[1:])
	attacker = self.read_u32(data)
	ac = attacker & 0xff
	al = (attacker >> 8) & 0xff
	aseq = (attacker >> 16) & 0xff
	apos = (attacker >> 24) & 0xff
	target = self.read_u32(data)
	tc = target & 0xff
	tl = (target >> 8) & 0xff
	tseq = (target >> 16) & 0xff
	tpos = (target >> 24) & 0xff
	self.cm.call_callbacks('attack', ac, al, aseq, apos, tc, tl, tseq, tpos)
	return data.read()

def attack(self, ac, al, aseq, apos, tc, tl, tseq, tpos):
	acard = self.get_card(ac, al, aseq)
	if not acard:
		return
	name = self.players[ac].nickname
	if tc == 0 and tl == 0 and tseq == 0 and tpos == 0:
		for pl in self.players + self.watchers:
			aspec = acard.get_spec(pl)
			pl.notify(pl._("%s prepares to attack with %s (%s)") % (name, aspec, acard.get_name(pl)))
		return
	tcard = self.get_card(tc, tl, tseq)
	if not tcard:
		return
	for pl in self.players + self.watchers:
		aspec = acard.get_spec(pl)
		tspec = tcard.get_spec(pl)
		tcname = tcard.get_name(pl)
		if (tcard.controller != pl.duel_player or pl.watching) and tcard.position & POSITION.FACEDOWN:
			tcname = pl._("%s card") % tcard.get_position(pl)
		pl.notify(pl._("%s prepares to attack %s (%s) with %s (%s)") % (name, tspec, tcname, aspec, acard.get_name(pl)))

MESSAGES = {110: msg_attack}

CALLBACKS = {'attack': attack}
