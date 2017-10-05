from gsb.intercepts import Reader
from twisted.internet import reactor

from ..parsers.duel_parser import DuelParser
from ..utils import process_duel
from .. import globals
from .. import duel

def announce_card_filter(self, player, options):
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
    cd = duel.ffi.new('struct card_data *')
    duel.card_reader_callback(card.code, cd)
    if not duel.lib.declarable(cd, len(options), options):
      return error(pl._("Wrong type."))
    self.set_responsei(card.code)
    reactor.callLater(0, process_duel, self)
  prompt()
