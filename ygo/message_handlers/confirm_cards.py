def confirm_cards(self, player, cards):
  pl = self.players[player]
  op = self.players[1 - player]
  players = [pl] + self.watchers
  for pl in players:
    pl.notify(pl._("{player} shows you {count} cards.")
      .format(player=op.nickname, count=len(cards)))
    for i, c in enumerate(cards):
      pl.notify("%s: %s" % (i + 1, c.get_name(pl)))
      self.revealed[(c.controller, c.location, c.sequence)] = True
