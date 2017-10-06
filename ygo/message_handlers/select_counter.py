import io
import struct
from twisted.internet import reactor

from ygo.card import Card
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import parse_ints, process_duel
from ygo import globals

def msg_select_counter(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  countertype = self.read_u16(data)
  count = self.read_u16(data)
  size = self.read_u8(data)
  cards = []
  for i in range(size):
    card = Card(self.read_u32(data))
    card.controller = self.read_u8(data)
    card.location = self.read_u8(data)
    card.sequence = self.read_u8(data)
    card.counter = self.read_u16(data)
    cards.append(card)
  self.cm.call_callbacks('select_counter', player, countertype, count, cards)
  return data.read()

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

MESSAGES = {22: msg_select_counter}

CALLBACKS = {'select_counter': select_counter}
