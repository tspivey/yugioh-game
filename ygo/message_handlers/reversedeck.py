def msg_reversedeck(self, data):
  for pl in self.players+self.watchers:
    pl.notify(pl._("all decks are now reversed."))
  return data[1:]

MESSAGES = {37: msg_reversedeck}
