import io

def msg_decktop(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  self.read_u8(data) # don't know what this number does
  code = self.read_u32(data)
  if code & 0x80000000:
    code = code ^ 0x80000000 # don't know what this actually does
  self.cm.call_callbacks('decktop', player, Card(code))
  return data.read()

def decktop(self, player, card):
  player = self.players[player]
  for pl in self.players+self.watchers:
    if pl is player:
      pl.notify(pl._("you reveal your top deck card to be %s")%(card.get_name(pl)))
    else:
      pl.notify(pl._("%s reveals their top deck card to be %s")%(player.nickname, card.get_name(pl)))

MESSAGES = {38: msg_decktop}

CALLBACKS = {'decktop': decktop}
