def select_battlecmd(self, player, activatable, attackable, to_m2, to_ep):
  self.state = "battle"
  self.activatable = activatable
  self.attackable = attackable
  self.to_m2 = bool(to_m2)
  self.to_ep = bool(to_ep)
  pl = self.players[player]
  self.display_battle_menu(pl)
