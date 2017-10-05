def swap(self, card1, card2):
  for p in self.watchers+self.players:
    for card in (card1, card2):
      plname = self.players[card.controller].nickname
      s = card.get_spec(p.duel_player)
      p.notify(p._("card {name} swapped control towards {plname} and is now located at {targetspec}.").format(plname=plname, targetspec=s, name=card.get_name(p)))
