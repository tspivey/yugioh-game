import io

from ygo import globals

def msg_counters(self, data):
  data = io.BytesIO(data[0:])

  msg = self.read_u8(data)

  ctype = self.read_u16(data)

  pl = self.read_u8(data)

  loc = self.read_u8(data)

  seq = self.read_u8(data)

  count = self.read_u16(data)

  card = self.get_card(pl, loc, seq)

  self.cm.call_callbacks('counters', card, ctype, count, msg==101)
      
  return data.read()

def counters(self, card, type, count, added):

  for pl in self.players+self.watchers:

    stype = globals.strings[pl.language]['counter'][type]

    if added:
       pl.notify(pl._("{amount} counters of type {counter} placed on {card}").format(amount=count, counter=stype, card=card.get_name(pl)))

    else:
       pl.notify(pl._("{amount} counters of type {counter} removed from {card}").format(amount=count, counter=stype, card=card.get_name(pl)))

MESSAGES = {101: msg_counters, 102: msg_counters}

CALLBACKS = {'counters': counters}
