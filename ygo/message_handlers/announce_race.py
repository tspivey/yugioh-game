import io
from twisted.internet import reactor

from ygo.constants import RACES
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def msg_announce_race(self, data):
  data = io.BytesIO(data[1:])
  player = self.read_u8(data)
  count = self.read_u8(data)
  avail = self.read_u32(data)
  self.cm.call_callbacks('announce_race', player, count, avail)
  return data.read()

def announce_race(self, player, count, avail):
  racemap = {k: (1<<i) for i, k in enumerate(RACES)}
  avail_races = {k: v for k, v in racemap.items() if avail & v}
  pl = self.players[player]
  def prompt():
    pl.notify("Type %d races separated by spaces." % count)
    for i, s in enumerate(avail_races.keys()):
      pl.notify("%d: %s" % (i+1, s))
    pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=DuelParser)
  def error(text):
    pl.notify(text)
    pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=DuelParser)
  def r(caller):
    ints = []
    try:
      for i in caller.text.split():
        ints.append(int(i) - 1)
    except ValueError:
      return error("Invalid value.")
    if len(ints) != count:
      return error("%d items required." % count)
    if len(ints) != len(set(ints)):
      return error("Duplicate values not allowed.")
    if any(i > len(avail_races) - 1 or i < 0 for i in ints):
      return error("Invalid value.")
    result = 0
    for i in ints:
      result |= list(avail_races.values())[i]
    self.set_responsei(result)
    reactor.callLater(0, process_duel, self)
  prompt()

MESSAGES = {140: msg_announce_race}

CALLBACKS = {'announce_race': announce_race}
