def lpupdate(self, player, lp):
  if lp > self.lp[player]:
    self.recover(player, lp - self.lp[player])
  else:
    self.damage(player, self.lp[player] - lp)
