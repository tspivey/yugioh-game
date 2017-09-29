def equip(self, card, target):
  for pl in self.players + self.watchers:
    c = self.cardlist_info_for_player(card, pl)
    t = self.cardlist_info_for_player(target, pl)
    pl.notify(pl._("{card} equipped to {target}.")
      .format(card=c, target=t))
