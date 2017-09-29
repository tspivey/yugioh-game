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
