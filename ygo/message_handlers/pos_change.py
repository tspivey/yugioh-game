def pos_change(self, card, prevpos):
  cs = self.card_to_spec(card.controller, card)
  cso = self.card_to_spec(1 - card.controller, card)
  cpl = self.players[card.controller]
  op = self.players[1 - card.controller]
  cpl.notify(cpl._("The position of card %s (%s) was changed to %s.") % (cs, card.get_name(cpl), card.get_position(cpl)))
  op.notify(op._("The position of card %s (%s) was changed to %s.") % (cso, card.get_name(op), card.get_position(op)))
  for w in self.watchers:
    cs = self.card_to_spec(w.duel_player, card)
    w.notify(w._("The position of card %s (%s) was changed to %s.") % (cs, card.get_name(w), card.get_position(w)))
