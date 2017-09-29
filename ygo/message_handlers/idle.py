def idle(self, summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs):
  self.state = "idle"
  pl = self.players[self.tp]
  self.summonable = summonable
  self.spsummon = spsummon
  self.repos = repos
  self.idle_mset = idle_mset
  self.idle_set = idle_set
  self.idle_activate = idle_activate
  self.to_bp = bool(to_bp)
  self.to_ep = bool(to_ep)
  self.idle_action(pl)
