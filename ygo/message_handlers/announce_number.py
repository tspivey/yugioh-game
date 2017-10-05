from twisted.internet import reactor

from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel, parse_ints

def announce_number(self, player, opts):
  pl = self.players[player]
  str_opts = [str(i) for i in opts]
  def prompt():
    pl.notify(pl._("Select a number, one of: {opts}")
      .format(opts=", ".join(str_opts)))
    return pl.notify(DuelReader, r, no_abort=pl._("Invalid command."), restore_parser=DuelParser)
  def r(caller):
    ints = parse_ints(caller.text)
    if not ints or ints[0] not in opts:
      return prompt()
    self.set_responsei(opts.index(ints[0]))
    reactor.callLater(0, process_duel, self)
  prompt()
