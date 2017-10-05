from twisted.internet import reactor

from ygo.constants import *
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def idle_action(self, pl):
  def prompt():
    pl.notify(pl._("Select a card on which to perform an action."))
    pl.notify(pl._("h shows your hand, tab and tab2 shows your or the opponent's table, ? shows usable cards."))
    if self.to_bp:
      pl.notify(pl._("b: Enter the battle phase."))
    if self.to_ep:
      pl.notify(pl._("e: End phase."))
    pl.notify(DuelReader, r,
    no_abort=pl._("Invalid specifier. Retry."),
    prompt=pl._("Select a card:"),
    restore_parser=DuelParser)
  cards = []
  for i in (0, 1):
    for j in (LOCATION_HAND, LOCATION_MZONE, LOCATION_SZONE, LOCATION_GRAVE, LOCATION_EXTRA):
      cards.extend(self.get_cards_in_location(i, j))
  specs = set(card.get_spec(self.tp) for card in cards)
  def r(caller):
    if caller.text == 'b' and self.to_bp:
      self.set_responsei(6)
      reactor.callLater(0, process_duel, self)
      return
    elif caller.text == 'e' and self.to_ep:
      self.set_responsei(7)
      reactor.callLater(0, process_duel, self)
      return
    elif caller.text == '?':
      self.show_usable(pl)
      return pl.notify(DuelReader, r,
      no_abort=pl._("Invalid specifier. Retry."),
      prompt=pl._("Select a card:"),
      restore_parser=DuelParser)
    if caller.text not in specs:
      pl.notify(pl._("Invalid specifier. Retry."))
      prompt()
      return
    loc, seq = self.cardspec_to_ls(caller.text)

    if caller.text.startswith('o'):
      plr = 1 - self.tp
    else:
      plr = self.tp
    card = self.get_card(plr, loc, seq)
    if not card:
      pl.notify(pl._("There is no card in that position."))
      prompt()
      return
    if plr == 1 - self.tp:
      if card.position in (0x8, 0xa):
        pl.notify(pl._("Face-down card."))
        return prompt()
    self.act_on_card(caller, card)
  prompt()
