import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def msg_select_unselect_card(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  finishable = self.read_u8(data)
  cancelable = self.read_u8(data)
  min = self.read_u8(data)
  max = self.read_u8(data)
  select_size = self.read_u8(data)
  select_cards = []
  for i in range(select_size):
    code = self.read_u32(data)
    loc = self.read_u32(data)
    card = Card(code)
    card.set_location(loc)
    select_cards.append(card)
  unselect_size = self.read_u8(data)
  unselect_cards = []
  for i in range(unselect_size):
    code = self.read_u32(data)
    loc = self.read_u32(data)
    card = Card(code)
    card.set_location(loc)
    unselect_cards.append(card)
  self.cm.call_callbacks('select_unselect_card', player, finishable, cancelable, min, max, select_cards, unselect_cards)
  return data.read()

def select_unselect_card(self, player, finishable, cancelable, min, max, select_cards, unselect_cards):
  pl = self.players[player]
  pl.card_list = select_cards+unselect_cards
  def prompt():
    text = pl._("Check or uncheck %d to %d cards by entering their number")%(min, max)
    if cancelable and not finishable:
      text += "\n"+pl._("Enter c to cancel")
    if finishable:
      text += "\n"+pl._("Enter f to finish")
    pl.notify(text)
    for i, c in enumerate(pl.card_list):
      name = self.cardlist_info_for_player(c, pl)
      if c in select_cards:
        state = pl._("unchecked")
      else:
        state = pl._("checked")
      pl.notify("%d: %s (%s)" % (i+1, name, state))
    pl.notify(DuelReader, f, no_abort="Invalid command", restore_parser=DuelParser)

  def error(text):
    pl.notify(text)
    return prompt()
  def f(caller):
    if caller.text == 'c' and (cancelable and not finishable) or caller.text == 'f' and finishable:
      self.set_responsei(-1)
      reactor.callLater(0, process_duel, self)
      return
    try:
      c = int(caller.text, 10)
    except ValueError:
      return error(pl._("Invalid command"))
    if c < 1 or c > len(pl.card_list):
      return error(pl._("Number not in range"))
    buf = bytes([1, c - 1])
    self.set_responseb(buf)
    reactor.callLater(0, process_duel, self)
  return prompt()

MESSAGES = {26: msg_select_unselect_card}

CALLBACKS = {'select_unselect_card': select_unselect_card}
