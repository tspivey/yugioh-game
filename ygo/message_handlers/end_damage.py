def end_damage(self):
  for pl in self.players + self.watchers:
    pl.notify(pl._("end damage"))
