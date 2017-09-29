def flipsummoning(self, card):
  cpl = self.players[card.controller]
  players = self.players + self.watchers
  for pl in players:
    spec = self.card_to_spec(pl.duel_player, card)
    pl.notify(pl._("{player} flip summons {card} ({spec}).")
    .format(player=cpl.nickname, card=card.get_name(pl), spec=spec))
