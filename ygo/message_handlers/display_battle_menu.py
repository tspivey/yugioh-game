def display_battle_menu(self, pl):
  pl.notify(pl._("Battle menu:"))
  if self.attackable:
    pl.notify(pl._("a: Attack."))
  if self.activatable:
    pl.notify(pl._("c: activate."))
  if self.to_m2:
    pl.notify(pl._("m: Main phase 2."))
  if self.to_ep:
    pl.notify(pl._("e: End phase."))
  def r(caller):
    if caller.text == 'a' and self.attackable:
      self.battle_attack(caller.connection)
    elif caller.text == 'c' and self.activatable:
      self.battle_activate(caller.connection)
    elif caller.text == 'e' and self.to_ep:
      self.set_responsei(3)
      reactor.callLater(0, procduel, self)
    elif caller.text == 'm' and self.to_m2:
      self.set_responsei(2)
      reactor.callLater(0, procduel, self)
    else:
      pl.notify("Invalid option.")
      return self.display_battle_menu(pl)
  pl.notify(DuelReader, r, no_abort=pl._("Invalid command."), prompt=pl._("Select an option:"), restore_parser=duel_parser)
