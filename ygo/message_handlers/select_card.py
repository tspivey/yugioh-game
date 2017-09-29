def select_card(self, player, cancelable, min_cards, max_cards, cards, is_tribute=False):
  con = self.players[player]
  con.card_list = cards
  def prompt():
    if is_tribute:
      con.notify(con._("Select %d to %d cards to tribute separated by spaces:") % (min_cards, max_cards))
    else:
      con.notify(con._("Select %d to %d cards separated by spaces:") % (min_cards, max_cards))
    for i, c in enumerate(cards):
      name = self.cardlist_info_for_player(c, con)
      con.notify("%d: %s" % (i+1, name))
    con.notify(DuelReader, f, no_abort="Invalid command", restore_parser=duel_parser)
  def error(text):
    con.notify(text)
    return prompt()
  def f(caller):
    cds = [i - 1 for i in self.parse_ints(caller.text)]
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
    reactor.callLater(0, procduel, self)
  return prompt()
