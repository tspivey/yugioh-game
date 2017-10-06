import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel, parse_ints

def msg_sort_card(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  size = self.read_u8(data)
  cards = []
  for i in range(size):
    card = Card(self.read_u32(data))
    card.controller = self.read_u8(data)
    card.location = self.read_u8(data)
    card.sequence = self.read_u8(data)
    cards.append(card)
  self.cm.call_callbacks('sort_card', player, cards)
  return data.read()

def sort_card(self, player, cards):
  pl = self.players[player]
  def prompt():
    pl.notify(pl._("Sort %d cards by entering numbers separated by spaces (c = cancel):") % len(cards))
    for i, c in enumerate(cards):
      pl.notify("%d: %s" % (i+1, c.get_name(pl)))
    return pl.notify(DuelReader, r, no_abort=pl._("Invalid command."), restore_parser=DuelParser)
  def error(text):
    pl.notify(text)
    return prompt()
  def r(caller):
    if caller.text == 'c':
      self.set_responseb(bytes([255]))
      reactor.callLater(0, process_duel, self)
      return
    ints = [i - 1 for i in parse_ints(caller.text)]
    if len(ints) != len(cards):
      return error(pl._("Please enter %d values.") % len(cards))
    if len(ints) != len(set(ints)):
      return error(pl._("Duplicate values not allowed."))
    if any(i < 0 or i > len(cards) - 1 for i in ints):
      return error(pl._("Please enter values between 1 and %d.") % len(cards))
    self.set_responseb(bytes(ints))
    reactor.callLater(0, process_duel, self)
  prompt()

MESSAGES = {25: msg_sort_card}

CALLBACKS = {'sort_card': sort_card}
