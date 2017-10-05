import struct
from twisted.internet import reactor

from ..duel_reader import DuelReader
from ..parsers.duel_parser import DuelParser
from ..utils import parse_ints, process_duel
from .. import globals

def select_counter(self, player, countertype, count, cards):
  pl = self.players[player]
  counter_str = globals.strings[pl.language]['counter'][countertype]
  def prompt():
    pl.notify(pl._("Type new {counter} for {cards} cards, separated by spaces.")
      .format(counter=counter_str, cards=len(cards)))
    for c in cards:
      pl.notify("%s (%d)" % (c.get_name(pl), c.counter))
    pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=DuelParser)
  def error(text):
    pl.notify(text)
    return prompt()
  def r(caller):
    ints = parse_ints(caller.text)
    ints = [i & 0xffff for i in ints]
    if len(ints) != len(cards):
      return error(pl._("Please specify %d values.") % len(cards))
    if any(cards[i].counter < val for i, val in enumerate(ints)):
      return error(pl._("Values cannot be greater than counter."))
    if sum(ints) != count:
      return error(pl._("Please specify %d values with a sum of %d.") % (len(cards), count))
    bytes = struct.pack('h' * len(cards), *ints)
    self.set_responseb(bytes)
    reactor.callLater(0, process_duel, self)
  prompt()
