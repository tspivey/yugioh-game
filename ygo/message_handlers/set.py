def set(self, card):
  c = card.controller
  cpl = self.players[c]
  opl = self.players[1 - c]
  cpl.notify(cpl._("You set %s (%s) in %s position.") %
  (self.card_to_spec(c, card), card.get_name(cpl), card.get_position(cpl)))
  op = 1 - c
  on = self.players[c].nickname
  opl.notify(opl._("%s sets %s in %s position.") %
  (on, self.card_to_spec(op, card), card.get_position(opl)))
  for pl in self.watchers:
    pl.notify(pl._("%s sets %s in %s position.") %
    (on, self.card_to_spec(pl, card), card.get_position(pl)))
