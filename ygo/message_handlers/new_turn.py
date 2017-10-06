def msg_new_turn(self, data):
  tp = int(data[1])
  self.cm.call_callbacks('new_turn', tp)
  return data[2:]

def new_turn(self, tp):
  self.tp = tp
  self.players[tp].notify(self.players[tp]._("Your turn."))
  op = self.players[1 - tp]
  op.notify(op._("%s's turn.") % self.players[tp].nickname)
  for w in self.watchers:
    w.notify(w._("%s's turn.") % self.players[tp].nickname)

MESSAGES = {40: msg_new_turn}

CALLBACKS = {'new_turn': new_turn}

