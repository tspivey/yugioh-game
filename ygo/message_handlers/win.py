import io

from ygo import globals

def msg_win(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  reason = self.read_u8(data)
  self.cm.call_callbacks('win', player, reason)
  return data.read()

def win(self, player, reason):
  if player == 2:
    self.notify_all("The duel was a draw.")
    self.end()
    return
  winner = self.players[player]
  loser = self.players[1 - player]
  reason_str = globals.strings[winner.language]['victory'][reason]
  winner.notify(winner._("You won (%s).") % reason_str)
  reason_str = globals.strings[loser.language]['victory'][reason]
  loser.notify(loser._("You lost (%s).") % reason_str)
  for pl in self.watchers:
    reason_str = globals.strings[pl.language]['victory'][reason]
    pl.notify(pl._("%s won (%s).") % (winner.nickname, reason_str))
  if not self.private:
    for pl in globals.server.get_all_players():
      reason_str = globals.strings[pl.language]['victory'][reason]
      globals.server.announce_challenge(pl, pl._("%s won the duel between %s and %s (%s).") % (winner.nickname, self.players[0].nickname, self.players[1].nickname, reason_str))
  self.end()

MESSAGES = {5: msg_win}

CALLBACKS = {'win': win}
