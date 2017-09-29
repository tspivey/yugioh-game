def attack(self, ac, al, aseq, apos, tc, tl, tseq, tpos):
  acard = self.get_card(ac, al, aseq)
  if not acard:
    return
  name = self.players[ac].nickname
  if tc == 0 and tl == 0 and tseq == 0 and tpos == 0:
    for pl in self.players + self.watchers:
      aspec = self.card_to_spec(pl.duel_player, acard)
      pl.notify(pl._("%s prepares to attack with %s (%s)") % (name, aspec, acard.get_name(pl)))
    return
  tcard = self.get_card(tc, tl, tseq)
  if not tcard:
    return
  for pl in self.players + self.watchers:
    aspec = self.card_to_spec(pl.duel_player, acard)
    tspec = self.card_to_spec(pl.duel_player, tcard)
    tcname = tcard.get_name(pl)
    if (tcard.controller != pl.duel_player or pl.watching) and tcard.position in (0x8, 0xa):
      tcname = pl._("%s card") % tcard.get_position(pl)
    pl.notify(pl._("%s prepares to attack %s (%s) with %s (%s)") % (name, tspec, tcname, aspec, acard.get_name(pl)))
