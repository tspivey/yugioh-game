def announce_card_filter(self, player, options):
  pl = self.players[player]
  def prompt():
    pl.notify(pl._("Enter the name of a card:"))
    return pl.notify(Reader, r, no_abort=pl._("Invalid command."), restore_parser=duel_parser)
  def error(text):
    pl.notify(text)
    return prompt()
  def r(caller):
    card = get_card_by_name(pl, caller.text)
    if card is None:
      return error(pl._("No results found."))
    cd = dm.ffi.new('struct card_data *')
    dm.card_reader_callback(card.code, cd)
    if not dm.lib.declarable(cd, len(options), options):
      return error(pl._("Wrong type."))
    self.set_responsei(card.code)
    reactor.callLater(0, procduel, self)
  prompt()

