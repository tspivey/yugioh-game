def chaining(self, card, tc, tl, ts, desc, cs):
  c = card.controller
  o = 1 - c
  n = self.players[c].nickname
  self.chaining_player = c
  if card.type & 0x2:
    if self.players[c].soundpack:
      self.players[c].notify("### activate_spell")
    if self.players[o].soundpack:
      self.players[o].notify("### activate_spell")
  elif card.type & 0x4:
    if self.players[c].soundpack:
      self.players[c].notify("### activate_trap")
    if self.players[o].soundpack:
      self.players[o].notify("### activate_trap")

  self.players[c].notify(self.players[c]._("Activating %s") % card.get_name(self.players[c]))
  self.players[o].notify(self.players[o]._("%s activating %s") % (n, card.get_name(self.players[o])))
  for pl in self.watchers:
    if card.type & 0x2:
      if pl.soundpack:
        pl.notify("### activate_spell")
    if card.type & 0x4:
      if pl.soundpack:
        pl.notify("### activate_trap")
    pl.notify(pl._("%s activating %s") % (n, card.get_name(pl)))
