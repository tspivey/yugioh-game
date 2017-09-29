def begin_damage(self):
  for pl in self.players + self.watchers:
    pl.notify(pl._("begin damage"))
