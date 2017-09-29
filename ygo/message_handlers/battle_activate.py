def battle_activate(self, con):
  pl = self.players[con.duel_player]
  pln = con.duel_player
  pl.notify(pl._("Select card to activate:"))
  specs = {}
  for c in self.activatable:
    spec = self.card_to_spec(pln, c)
    pl.notify("%s: %s (%d/%d)" % (spec, c.get_name(pl), c.attack, c.defense))
    specs[spec] = c
  pl.notify(pl._("z: back."))
  def r(caller):
    if caller.text == 'z':
      self.display_battle_menu(pl)
      return
    if caller.text not in specs:
      pl.notify(pl._("Invalid cardspec. Retry."))
      pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
      return
    card = specs[caller.text]
    seq = self.activatable.index(card)
    self.set_responsei((seq << 16))
    reactor.callLater(0, procduel, self)
  pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
