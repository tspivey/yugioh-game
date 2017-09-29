from ..duel_reader import DuelReader
from ..parsers.duel_parser import DuelParser

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
    restore_parser=duel_parser)
  cards = []
  for i in (0, 1):
    for j in (dm.LOCATION_HAND, dm.LOCATION_MZONE, dm.LOCATION_SZONE, dm.LOCATION_GRAVE, dm.LOCATION_EXTRA):
      cards.extend(self.get_cards_in_location(i, j))
  specs = set(self.card_to_spec(self.tp, card) for card in cards)
  def r(caller):
    if caller.text == 'b' and self.to_bp:
      self.set_responsei(6)
      reactor.callLater(0, procduel, self)
      return
    elif caller.text == 'e' and self.to_ep:
      self.set_responsei(7)
      reactor.callLater(0, procduel, self)
      return
    elif caller.text == '?':
      self.show_usable(pl)
      return pl.notify(DuelReader, r,
      no_abort=pl._("Invalid specifier. Retry."),
      prompt=pl._("Select a card:"),
      restore_parser=duel_parser)
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
