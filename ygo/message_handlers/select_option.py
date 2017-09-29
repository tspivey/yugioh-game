def select_option(self, player, options):
  pl = self.players[player]
  def select(caller, idx):
    self.set_responsei(idx)
    reactor.callLater(0, procduel, self)
  opts = []
  for opt in options:
    if opt > 10000:
      code = opt >> 4
      string = dm.Card.from_code(code).strings[opt & 0xf]
    else:
      string = "Unknown option %d" % opt
      string = strings[pl.language]['system'].get(opt, string)
    opts.append(string)
  m = Menu(pl._("Select option:"), no_abort=pl._("Invalid option."), persistent=True, prompt=pl._("Select option:"), restore_parser=duel_parser)
  for idx, opt in enumerate(opts):
    m.item(opt)(lambda caller, idx=idx: select(caller, idx))
  pl.notify(m)

