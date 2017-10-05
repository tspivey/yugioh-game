from twisted.internet import reactor

from ..utils import process_duel

def sort_chain(self, player, cards):
  self.set_responsei(-1)
  reactor.callLater(0, process_duel, self)
