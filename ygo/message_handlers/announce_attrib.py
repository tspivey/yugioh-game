def announce_attrib(self, player, count, avail):
  attributes = ('Earth', 'Water', 'Fire', 'Wind', 'Light', 'Dark', 'Divine')
  attrmap = {k: (1<<i) for i, k in enumerate(attributes)}
  avail_attributes = {k: v for k, v in attrmap.items() if avail & v}
  avail_attributes_keys = avail_attributes.keys()
  avail_attributes_values = list(avail_attributes.values())
  pl = self.players[player]
  def prompt():
    pl.notify("Type %d attributes separated by spaces." % count)
    for i, attrib in enumerate(avail_attributes_keys):
      pl.notify("%d. %s" % (i + 1, attrib))
    pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
  def r(caller):
    items = caller.text.split()
    ints = []
    try:
      ints = [int(i) for i in items]
    except ValueError:
      pass
    ints = [i for i in ints if i > 0 <= len(avail_attributes_keys)]
    ints = set(ints)
    if len(ints) != count:
      pl.notify("Invalid attributes.")
      return prompt()
    value = sum(avail_attributes_values[i - 1] for i in ints)
    self.set_responsei(value)
    reactor.callLater(0, procduel, self)
  return prompt()
