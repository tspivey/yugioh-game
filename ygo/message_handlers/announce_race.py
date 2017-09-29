def announce_race(self, player, count, avail):
  races = (
    "Warrior", "Spellcaster", "Fairy", "Fiend", "Zombie",
    "Machine", "Aqua", "Pyro", "Rock", "Wind Beast",
    "Plant", "Insect", "Thunder", "Dragon", "Beast",
    "Beast Warrior", "Dinosaur", "Fish", "Sea Serpent", "Reptile",
    "psycho", "Divine", "Creator god", "Wyrm", "Cybers",
  )
  racemap = {k: (1<<i) for i, k in enumerate(races)}
  avail_races = {k: v for k, v in racemap.items() if avail & v}
  pl = self.players[player]
  def prompt():
    pl.notify("Type %d races separated by spaces." % count)
    for i, s in enumerate(avail_races.keys()):
      pl.notify("%d: %s" % (i+1, s))
    pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=duel_parser)
  def error(text):
    pl.notify(text)
    pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=duel_parser)
  def r(caller):
    ints = []
    try:
      for i in caller.text.split():
        ints.append(int(i) - 1)
    except ValueError:
      return error("Invalid value.")
    if len(ints) != count:
      return error("%d items required." % count)
    if len(ints) != len(set(ints)):
      return error("Duplicate values not allowed.")
    if any(i > len(avail_races) - 1 or i < 0 for i in ints):
      return error("Invalid value.")
    result = 0
    for i in ints:
      result |= list(avail_races.values())[i]
    self.set_responsei(result)
    reactor.callLater(0, procduel, self)
  prompt()
