import io

def msg_battle(self, data):
	data = io.BytesIO(data[1:])
	attacker = self.read_u32(data)
	aa = self.read_u32(data)
	ad = self.read_u32(data)
	bd0 = self.read_u8(data)
	tloc = self.read_u32(data)
	da = self.read_u32(data)
	dd = self.read_u32(data)
	bd1 = self.read_u8(data)
	self.cm.call_callbacks('battle', attacker, aa, ad, bd0, tloc, da, dd, bd1)
	return data.read()

def battle(self, attacker, aa, ad, bd0, tloc, da, dd, bd1):
	loc = (attacker >> 8) & 0xff
	seq = (attacker >> 16) & 0xff
	c2 = attacker & 0xff
	card = self.get_card(c2, loc, seq)
	tc = tloc & 0xff
	tl = (tloc >> 8) & 0xff
	tseq = (tloc >> 16) & 0xff
	if tloc:
		target = self.get_card(tc, tl, tseq)
	else:
		target = None
	for pl in self.players + self.watchers:
		if target:
			pl.notify(pl._("%s (%d/%d) attacks %s (%d/%d)") % (card.get_name(pl), aa, ad, target.get_name(pl), da, dd))
		else:
			pl.notify(pl._("%s (%d/%d) attacks") % (card.get_name(pl), aa, ad))

MESSAGES = {111: msg_battle}

CALLBACKS = {'battle': battle}
