from twisted.internet import reactor

from ..utils import process_duel
from .. import globals

def hint(self, msg, player, data):
  pl = self.players[player]
  op = self.players[1 - player]
  if msg == 3 and data in globals.strings[pl.language]['system']:
    self.players[player].notify(globals.strings[pl.language]['system'][data])
  elif msg == 6 or msg == 7 or msg == 8:
    reactor.callLater(0, process_duel, self)
  elif msg == 9:
    op.notify(globals.strings[op.language]['system'][1512] % data)
    reactor.callLater(0, process_duel, self)
