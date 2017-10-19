import io

def msg_idlecmd(self, data):
	self.state = 'idle'
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	summonable = self.read_cardlist(data)
	spsummon = self.read_cardlist(data)
	repos = self.read_cardlist(data)
	idle_mset = self.read_cardlist(data)
	idle_set = self.read_cardlist(data)
	idle_activate = self.read_cardlist(data, True)
	to_bp = self.read_u8(data)
	to_ep = self.read_u8(data)
	cs = self.read_u8(data)
	self.cm.call_callbacks('idle', summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs)
	return data.read()

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

MESSAGES = {11: msg_idlecmd}

CALLBACKS = {'idle': idle}
