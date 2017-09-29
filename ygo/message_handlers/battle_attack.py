def battle_attack(self, con):
  pl = self.players[con.duel_player]
  pln = con.duel_player
  pl.notify(pl._("Select card to attack with:"))
  specs = {}
  for c in self.attackable:
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
      return self.battle_attack(pl)
    card = specs[caller.text]
    seq = self.attackable.index(card)
    self.set_responsei((seq << 16) + 1)
    reactor.callLater(0, procduel, self)
  pl.notify(DuelReader, r, no_abort=pl._("Invalid command."), prompt=pl._("Select a card:"), restore_parser=duel_parser)
