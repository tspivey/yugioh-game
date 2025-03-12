import io

from ygo.constants import LOCATION, TYPE

def msg_battle(self, data):
	data = io.BytesIO(data[1:])
	attacker = self.read_location(data)
	aa = self.read_u32(data)
	ad = self.read_u32(data)
	bd0 = self.read_u8(data)
	tloc = self.read_location(data)
	da = self.read_u32(data)
	dd = self.read_u32(data)
	bd1 = self.read_u8(data)
	self.cm.call_callbacks('battle', attacker, aa, ad, bd0, tloc, da, dd, bd1)
	return data.read()

def battle(self, attacker, aa, ad, bd0, tloc, da, dd, bd1):
	loc = attacker.location
	seq = attacker.sequence
	c2 = attacker.controller
	card = self.get_card(c2, loc, seq)
	tc = tloc.controller
	tl = tloc.location
	tseq = tloc.sequence
	if tloc:
		target = self.get_card(tc, tl, tseq)
	else:
		target = None
	for pl in self.players + self.watchers:
		if card.type & TYPE.LINK:
			attacker_points = "%d"%aa
		else:
			attacker_points = "%d/%d"%(aa, ad)

		if target:
			if target.type & TYPE.LINK:
				defender_points = "%d"%da
			else:
				defender_points = "%d/%d"%(da, dd)

		if target:
			pl.notify(pl._("%s (%s) attacks %s (%s)") % (card.get_name(pl), attacker_points, target.get_name(pl), defender_points))
		else:
			pl.notify(pl._("%s (%s) attacks") % (card.get_name(pl), attacker_points))

MESSAGES = {111: msg_battle}

CALLBACKS = {'battle': battle}
