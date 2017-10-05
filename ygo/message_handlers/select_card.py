from twisted.internet import reactor

from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel, parse_ints

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
