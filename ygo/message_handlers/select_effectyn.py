def select_effectyn(self, player, card, desc):
  pl = self.players[player]
  old_parser = pl.parser
  def yes(caller):
    self.set_responsei(1)
    reactor.callLater(0, procduel, self)
  def no(caller):
    self.set_responsei(0)
    reactor.callLater(0, procduel, self)
  spec = self.card_to_spec(player, card)
  question = pl._("Do you want to use the effect from {card} in {spec}?").format(card=card.get_name(pl), spec=spec)
  s = card.get_effect_description(pl, desc, True)
  if s != '':
    question += '\n'+s
  pl.notify(YesOrNo, question, yes, no=no, restore_parser=old_parser)
