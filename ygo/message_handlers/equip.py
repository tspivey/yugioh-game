import io

def msg_equip(self, data):
  data = io.BytesIO(data[1:])
  loc = self.read_u32(data)
  target = self.read_u32(data)
  u = self.unpack_location(loc)
  card = self.get_card(u[0], u[1], u[2])
  u = self.unpack_location(target)
  target = self.get_card(u[0], u[1], u[2])
  self.cm.call_callbacks('equip', card, target)
  return data.read()

def equip(self, card, target):
  for pl in self.players + self.watchers:
    c = self.cardlist_info_for_player(card, pl)
    t = self.cardlist_info_for_player(target, pl)
    pl.notify(pl._("{card} equipped to {target}.")
      .format(card=c, target=t))

MESSAGES = {93: msg_equip}

CALLBACKS = {'equip': equip}
