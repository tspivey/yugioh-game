def select_sum(self, mode, player, val, select_min, select_max, must_select, select_some):
  pl = self.players[player]
  must_select_value = sum(c.param for c in must_select)
  def prompt():
    if mode == 0:
      pl.notify(pl._("Select cards with a total value of %d, seperated by spaces.") % (val - must_select_value))
    else:
      pl.notify(pl._("Select cards with a total value of at least %d, seperated by spaces.") % (val - must_select_value))
    for c in must_select:
      pl.notify("%s must be selected, automatically selected." % c.get_name(pl))
    for i, card in enumerate(select_some):
      pl.notify("%d: %s (%d)" % (i+1, card.get_name(pl), card.param & 0xffff))
    return pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=duel_parser)
  def error(t):
    pl.notify(t)
    return prompt()
  def r(caller):
    ints = [i - 1 for i in self.parse_ints(caller.text)]
    if len(ints) != len(set(ints)):
      return error(pl._("Duplicate values not allowed."))
    if any(i for i in ints if i < 1 or i > len(select_some) - 1):
      return error(pl._("Value out of range."))
    selected = [select_some[i] for i in ints]
    s = [select_some[i].param & 0xffff  for i in ints]
    if mode == 1 and (sum(s) < val or sum(s) - min(s) >= val):
      return error(pl._("Levels out of range."))
    if mode == 0 and not check_sum(selected, val - must_select_value):
      return error(pl._("Selected value does not equal %d.") % (val,))
    lst = [len(ints) + len(must_select)]
    lst.extend([0] * len(must_select))
    lst.extend(ints)
    b = bytes(lst)
    self.set_responseb(b)
    reactor.callLater(0, procduel, self)
  prompt()
