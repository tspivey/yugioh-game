def pay_lpcost(self, player, cost):
  self.lp[player] -= cost
  self.players[player].notify(self.players[player]._("You pay %d LP. Your LP is now %d.") % (cost, self.lp[player]))
  players = [self.players[1 - player]]
  players.extend(self.watchers)
  for pl in players:
    pl.notify(pl._("%s pays %d LP. Their LP is now %d.") % (self.players[player].nickname, cost, self.lp[player]))
