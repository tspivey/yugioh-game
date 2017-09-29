def hint(self, msg, player, data):
  pl = self.players[player]
  op = self.players[1 - player]
  if msg == 3 and data in strings[pl.language]['system']:
    self.players[player].notify(strings[pl.language]['system'][data])
  elif msg == 6 or msg == 7 or msg == 8:
    reactor.callLater(0, procduel, self)
  elif msg == 9:
    op.notify(strings[op.language]['system'][1512] % data)
    reactor.callLater(0, procduel, self)
