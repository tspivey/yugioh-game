def become_target(self, tc, tl, tseq):
  card = self.get_card(tc, tl, tseq)
  if not card:
    return
  name = self.players[self.chaining_player].nickname
  for pl in self.players + self.watchers:
    spec = card.get_spec(pl.duel_player)
    tcname = card.get_name(pl)
    if (pl.watching or card.controller != pl.duel_player) and card.position in (0x8, 0xa):
      tcname = pl._("%s card") % card.get_position(pl)
    pl.notify(pl._("%s targets %s (%s)") % (name, spec, tcname))
