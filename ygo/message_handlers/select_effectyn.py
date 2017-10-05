from twisted.internet import reactor

from ygo.parsers.yes_or_no_parser import yes_or_no_parser
from ygo.utils import process_duel

def select_effectyn(self, player, card, desc):
  pl = self.players[player]
  old_parser = pl.connection.parser
  def yes(caller):
    self.set_responsei(1)
    reactor.callLater(0, process_duel, self)
  def no(caller):
    self.set_responsei(0)
    reactor.callLater(0, process_duel, self)
  spec = card.get_spec(player)
  question = pl._("Do you want to use the effect from {card} in {spec}?").format(card=card.get_name(pl), spec=spec)
  s = card.get_effect_description(pl, desc, True)
  if s != '':
    question += '\n'+s
  pl.notify(yes_or_no_parser, question, yes, no=no, restore_parser=old_parser)
