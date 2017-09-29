def damage(self, player, amount):
  new_lp = self.lp[player]-amount
  pl = self.players[player]
  op = self.players[1 - player]
  pl.notify(pl._("Your lp decreased by %d, now %d") % (amount, new_lp))
  op.notify(op._("%s's lp decreased by %d, now %d") % (self.players[player].nickname, amount, new_lp))
  for pl in self.watchers:
    pl.notify(pl._("%s's lp decreased by %d, now %d") % (self.players[player].nickname, amount, new_lp))
  self.lp[player] -= amount

