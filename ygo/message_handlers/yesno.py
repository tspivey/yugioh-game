from twisted.internet import reactor

from ygo.card import Card
from ygo.parsers.yes_or_no_parser import yes_or_no_parser
from ygo.utils import process_duel

def yesno(self, player, desc):
  pl = self.players[player]
  old_parser = pl.connection.parser
  def yes(caller):
    self.set_responsei(1)
    reactor.callLater(0, process_duel, self)
  def no(caller):
    self.set_responsei(0)
    reactor.callLater(0, process_duel, self)
  if desc > 10000:
    code = desc >> 4
    opt = Card(code).get_strings(pl)[desc & 0xf]
  else:
    opt = "String %d" % desc
    opt = globals.strings[pl.language]['system'].get(desc, opt)
  pl.notify(yes_or_no_parser, opt, yes, no=no, restore_parser=old_parser)
