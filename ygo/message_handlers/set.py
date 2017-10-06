import io

from ygo.card import Card

def msg_set(self, data):
  data = io.BytesIO(data[1:])
  code = self.read_u32(data)
  loc = self.read_u32(data)
  card = Card(code)
  card.set_location(loc)
  self.cm.call_callbacks('set', card)
  return data.read()

def set(self, card):
  c = card.controller
  cpl = self.players[c]
  opl = self.players[1 - c]
  cpl.notify(cpl._("You set %s (%s) in %s position.") %
  (card.get_spec(c), card.get_name(cpl), card.get_position(cpl)))
  op = 1 - c
  on = self.players[c].nickname
  opl.notify(opl._("%s sets %s in %s position.") %
  (on, card.get_spec(op), card.get_position(opl)))
  for pl in self.watchers:
    pl.notify(pl._("%s sets %s in %s position.") %
    (on, card.get_spec(pl), card.get_position(pl)))

MESSAGES = {54: msg_set}

CALLBACKS = {'set': set}
