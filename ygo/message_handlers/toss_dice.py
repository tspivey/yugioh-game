from ygo import globals

def toss_dice(self, player, options):
  opts = [str(opt) for opt in options]
  players = []
  players.extend(self.players + self.watchers)
  for pl in players:
    s = globals.strings[pl.language]['system'][1624] + " "
    s += ", ".join(opts)
    pl.notify(s)
