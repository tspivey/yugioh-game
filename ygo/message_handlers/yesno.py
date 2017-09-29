def yesno(self, player, desc):
  pl = self.players[player]
  old_parser = pl.parser
  def yes(caller):
    self.set_responsei(1)
    reactor.callLater(0, procduel, self)
  def no(caller):
    self.set_responsei(0)
    reactor.callLater(0, procduel, self)
  if desc > 10000:
    code = desc >> 4
    opt = dm.Card.from_code(code).strings[desc & 0xf]
  else:
    opt = "String %d" % desc
    opt = strings[pl.language]['system'].get(desc, opt)
  pl.notify(YesOrNo, opt, yes, no=no, restore_parser=old_parser)
