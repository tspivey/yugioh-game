def sort_card(self, player, cards):
  pl = self.players[player]
  def prompt():
    pl.notify(pl._("Sort %d cards by entering numbers separated by spaces (c = cancel):") % len(cards))
    for i, c in enumerate(cards):
      pl.notify("%d: %s" % (i+1, c.get_name(pl)))
    return pl.notify(DuelReader, r, no_abort=pl._("Invalid command."), restore_parser=duel_parser)
  def error(text):
    pl.notify(text)
    return prompt()
  def r(caller):
    if caller.text == 'c':
      self.set_responseb(bytes([255]))
      reactor.callLater(0, procduel, self)
      return
    ints = [i - 1 for i in self.parse_ints(caller.text)]
    if len(ints) != len(cards):
      return error(pl._("Please enter %d values.") % len(cards))
    if len(ints) != len(set(ints)):
      return error(pl._("Duplicate values not allowed."))
    if any(i < 0 or i > len(cards) - 1 for i in ints):
      return error(pl._("Please enter values between 1 and %d.") % len(cards))
    self.set_responseb(bytes(ints))
    reactor.callLater(0, procduel, self)
  prompt()
