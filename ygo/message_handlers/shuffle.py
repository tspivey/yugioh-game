def shuffle(self, player):
  pl = self.players[player]
  pl.notify(pl._("you shuffled your deck."))
  for pl in self.watchers+[self.players[1 - player]]:
    pl.notify(pl._("%s shuffled their deck.")%(self.players[player].nickname))
