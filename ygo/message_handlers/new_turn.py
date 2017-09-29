def new_turn(self, tp):
  self.tp = tp
  self.players[tp].notify(self.players[tp]._("Your turn."))
  op = self.players[1 - tp]
  op.notify(op._("%s's turn.") % self.players[tp].nickname)
  for w in self.watchers:
    w.notify(w._("%s's turn.") % self.players[tp].nickname)
