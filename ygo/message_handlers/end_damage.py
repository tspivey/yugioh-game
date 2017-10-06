def msg_end_damage(self, data):
  self.cm.call_callbacks('end_damage')
  return data[1:]

def end_damage(self):
  for pl in self.players + self.watchers:
    pl.notify(pl._("end damage"))

MESSAGES = {114: msg_end_damage}

CALLBACKS = {'end_damage': end_damage}
