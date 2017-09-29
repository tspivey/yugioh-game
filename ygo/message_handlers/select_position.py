def select_position(self, player, card, positions):
  pl = self.players[player]
  m = Menu(pl._("Select position for %s:") % (card.get_name(pl),), no_abort="Invalid option.", persistent=True, restore_parser=duel_parser)
  def set(caller, pos=None):
    self.set_responsei(pos)
    reactor.callLater(0, procduel, self)
  if positions & 1:
    m.item(pl._("Face-up attack"))(lambda caller: set(caller, 1))
  if positions & 2:
    m.item(pl._("Face-down attack"))(lambda caller: set(caller, 2))
  if positions & 4:
    m.item(pl._("Face-up defense"))(lambda caller: set(caller, 4))
  if positions & 8:
    m.item(pl._("Face-down defense"))(lambda caller: set(caller, 8))
  pl.notify(m)
