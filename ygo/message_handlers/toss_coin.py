from .. import globals

def toss_coin(self, player, options):
  players = []
  players.extend(self.players + self.watchers)
  for pl in players:
    s = globals.strings[pl.language]['system'][1623] + " "
    opts = [globals.strings[pl.language]['system'][60] if opt else globals.strings[pl.language]['system'][61] for opt in options]
    s += ", ".join(opts)
    pl.notify(s)

