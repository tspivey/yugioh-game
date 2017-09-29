def decktop(self, player, card):
  player = self.players[player]
  for pl in self.players+self.watchers:
    if pl is player:
      pl.notify(pl._("you reveal your top deck card to be %s")%(card.get_name(pl)))
    else:
      pl.notify(pl._("%s reveals their top deck card to be %s")%(player.nickname, card.get_name(pl)))
