def pos_change(self, card, prevpos):
  cs = card.get_spec(card.controller)
  cso = card.get_spec(1 - card.controller)
  cpl = self.players[card.controller]
  op = self.players[1 - card.controller]
  cpl.notify(cpl._("The position of card %s (%s) was changed to %s.") % (cs, card.get_name(cpl), card.get_position(cpl)))
  op.notify(op._("The position of card %s (%s) was changed to %s.") % (cso, card.get_name(op), card.get_position(op)))
  for w in self.watchers:
    cs = card.get_spec(w.duel_player)
    w.notify(w._("The position of card %s (%s) was changed to %s.") % (cs, card.get_name(w), card.get_position(w)))
