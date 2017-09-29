def summoning(self, card, special=False):
  if special:
    action = "Special summoning"
  else:
    action = "Summoning"
  nick = self.players[card.controller].nickname
  for pl in self.players + self.watchers:
    pos = card.get_position(pl)
    if special:
      pl.notify(pl._("%s special summoning %s (%d/%d) in %s position.") % (nick, card.get_name(pl), card.attack, card.defense, pos))
    else:
      pl.notify(pl._("%s summoning %s (%d/%d) in %s position.") % (nick, card.get_name(pl), card.attack, card.defense, pos))
