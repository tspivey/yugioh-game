from gsb.intercepts import Reader
from twisted.internet import reactor

from ..parsers.duel_parser import DuelParser
from ..utils import process_duel
from .. import globals

def announce_card(self, player, type):
  pl = self.players[player]
  def prompt():
    pl.notify(pl._("Enter the name of a card:"))
    return pl.notify(Reader, r, no_abort=pl._("Invalid command."), restore_parser=DuelParser)
  def error(text):
    pl.notify(text)
    return prompt()
  def r(caller):
    card = globals.server.get_card_by_name(pl, caller.text)
    if card is None:
      return error(pl._("No results found."))
    if not card.type & type:
      return error(pl._("Wrong type."))
    self.set_responsei(card.code)
    reactor.callLater(0, process_duel, self)
  prompt()
