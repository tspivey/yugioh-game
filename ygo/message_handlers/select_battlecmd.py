import io

def msg_select_battlecmd(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	activatable = self.read_cardlist(data, True)
	attackable = self.read_cardlist(data, True, True, seq8=True)
	to_m2 = self.read_u8(data)
	to_ep = self.read_u8(data)
	self.cm.call_callbacks('select_battlecmd', player, activatable, attackable, to_m2, to_ep)
	return data.read()

def select_battlecmd(self, player, activatable, attackable, to_m2, to_ep):
	self.state = "battle"
	self.activatable = activatable
	self.attackable = attackable
	self.to_m2 = bool(to_m2)
	self.to_ep = bool(to_ep)
	pl = self.players[player]
	self.display_battle_menu(pl)

MESSAGES = {10: msg_select_battlecmd}

CALLBACKS = {'select_battlecmd': select_battlecmd}
