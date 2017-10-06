from gsb.intercept import Menu
import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel
from ygo import globals

def msg_select_option(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  size = self.read_u8(data)
  options = []
  for i in range(size):
    options.append(self.read_u32(data))
  self.cm.call_callbacks("select_option", player, options)
  return data.read()

def select_option(self, player, options):
  pl = self.players[player]
  def select(caller, idx):
    self.set_responsei(idx)
    reactor.callLater(0, process_duel, self)
  opts = []
  for opt in options:
    if opt > 10000:
      code = opt >> 4
      string = Card(code).get_strings(pl)[opt & 0xf]
    else:
      string = "Unknown option %d" % opt
      string = globals.strings[pl.language]['system'].get(opt, string)
    opts.append(string)
  m = Menu(pl._("Select option:"), no_abort=pl._("Invalid option."), persistent=True, prompt=pl._("Select option:"), restore_parser=DuelParser)
  for idx, opt in enumerate(opts):
    m.item(opt)(lambda caller, idx=idx: select(caller, idx))
  pl.notify(m)

MESSAGES = {14: msg_select_option}

CALLBACKS = {'select_option': select_option}
