import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel, parse_ints

def msg_select_tribute(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  cancelable = self.read_u8(data)
  min = self.read_u8(data)
  max = self.read_u8(data)
  size = self.read_u8(data)
  cards = []
  for i in range(size):
    code = self.read_u32(data)
    card = Card(code)
    card.controller = self.read_u8(data)
    card.location = self.read_u8(data)
    card.sequence = self.read_u8(data)
    card.position = self.get_card(card.controller, card.location, card.sequence).position
    card.release_param = self.read_u8(data)
    cards.append(card)
  self.cm.call_callbacks('select_tribute', player, cancelable, min, max, cards)
  return data.read()

def msg_select_card(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  cancelable = self.read_u8(data)
  min = self.read_u8(data)
  max = self.read_u8(data)
  size = self.read_u8(data)
  cards = []
  for i in range(size):
    code = self.read_u32(data)
    loc = self.read_u32(data)
    card = Card(code)
    card.set_location(loc)
    cards.append(card)
  self.cm.call_callbacks('select_card', player, cancelable, min, max, cards)
  return data.read()

def select_card(self, player, cancelable, min_cards, max_cards, cards, is_tribute=False):
  pl = self.players[player]
  pl.card_list = cards
  def prompt():
    if is_tribute:
      pl.notify(pl._("Select %d to %d cards to tribute separated by spaces:") % (min_cards, max_cards))
    else:
      pl.notify(pl._("Select %d to %d cards separated by spaces:") % (min_cards, max_cards))
    for i, c in enumerate(cards):
      name = self.cardlist_info_for_player(c, pl)
      pl.notify("%d: %s" % (i+1, name))
    pl.notify(DuelReader, f, no_abort="Invalid command", restore_parser=DuelParser)
  def error(text):
    pl.notify(text)
    return prompt()
  def f(caller):
    cds = [i - 1 for i in parse_ints(caller.text)]
    if len(cds) != len(set(cds)):
      return error(con._("Duplicate values not allowed."))
    if (not is_tribute and len(cds) < min_cards) or len(cds) > max_cards:
      return error(con._("Please enter between %d and %d cards.") % (min_cards, max_cards))
    if cds and (min(cds) < 0 or max(cds) > len(cards) - 1):
      return error(con._("Invalid value."))
    buf = bytes([len(cds)])
    tribute_value = 0
    for i in cds:
      tribute_value += (cards[i].release_param if is_tribute else 0)
      buf += bytes([i])
    if is_tribute and tribute_value < min_cards:
      return error(con._("Not enough tributes."))
    self.set_responseb(buf)
    reactor.callLater(0, process_duel, self)
  return prompt()

def select_tribute(self, *args, **kwargs):
  kwargs['is_tribute'] = True
  self.select_card(*args, **kwargs)

MESSAGES = {15: msg_select_card, 20: msg_select_tribute}

CALLBACKS = {'select_card': select_card, 'select_tribute': select_tribute}
