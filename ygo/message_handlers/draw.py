def draw(self, player, cards):
  pl = self.players[player]
  pl.notify(pl._("Drew %d cards:") % len(cards))
  for i, c in enumerate(cards):
    pl.notify("%d: %s" % (i+1, c.get_name(pl)))
  op = self.players[1 - player]
  op.notify(op._("Opponent drew %d cards.") % len(cards))
  for w in self.watchers:
    w.notify(w._("%s drew %d cards.") % (pl.nickname, len(cards)))
