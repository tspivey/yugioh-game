import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import parse_ints, process_duel, check_sum

def msg_select_sum(self, data):
  data = io.BytesIO(data[1:])
  mode = self.read_u8(data)
  player = self.read_u8(data)
  val = self.read_u32(data)
  select_min = self.read_u8(data)
  select_max = self.read_u8(data)
  count = self.read_u8(data)
  must_select = []
  for i in range(count):
    code = self.read_u32(data)
    card = Card(code)
    card.controller = self.read_u8(data)
    card.location = self.read_u8(data)
    card.sequence = self.read_u8(data)
    card.param = self.read_u32(data)
    must_select.append(card)
  count = self.read_u8(data)
  select_some = []
  for i in range(count):
    code = self.read_u32(data)
    card = Card(code)
    card.controller = self.read_u8(data)
    card.location = self.read_u8(data)
    card.sequence = self.read_u8(data)
    card.param = self.read_u32(data)
    select_some.append(card)
  self.cm.call_callbacks('select_sum', mode, player, val, select_min, select_max, must_select, select_some)
  return data.read()

def select_sum(self, mode, player, val, select_min, select_max, must_select, select_some):
  pl = self.players[player]
  must_select_value = sum(c.param for c in must_select)
  def prompt():
    if mode == 0:
      pl.notify(pl._("Select cards with a total value of %d, seperated by spaces.") % (val - must_select_value))
    else:
      pl.notify(pl._("Select cards with a total value of at least %d, seperated by spaces.") % (val - must_select_value))
    for c in must_select:
      pl.notify("%s must be selected, automatically selected." % c.get_name(pl))
    for i, card in enumerate(select_some):
      pl.notify("%d: %s (%d)" % (i+1, card.get_name(pl), card.param & 0xffff))
    return pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=DuelParser)
  def error(t):
    pl.notify(t)
    return prompt()
  def r(caller):
    ints = [i - 1 for i in parse_ints(caller.text)]
    if len(ints) != len(set(ints)):
      return error(pl._("Duplicate values not allowed."))
    if any(i for i in ints if i < 1 or i > len(select_some) - 1):
      return error(pl._("Value out of range."))
    selected = [select_some[i] for i in ints]
    s = [select_some[i].param & 0xffff  for i in ints]
    if mode == 1 and (sum(s) < val or sum(s) - min(s) >= val):
      return error(pl._("Levels out of range."))
    if mode == 0 and not check_sum(selected, val - must_select_value):
      return error(pl._("Selected value does not equal %d.") % (val,))
    lst = [len(ints) + len(must_select)]
    lst.extend([0] * len(must_select))
    lst.extend(ints)
    b = bytes(lst)
    self.set_responseb(b)
    reactor.callLater(0, process_duel, self)
  prompt()

MESSAGES = {23: msg_select_sum}

CALLBACKS = {'select_sum': select_sum}
