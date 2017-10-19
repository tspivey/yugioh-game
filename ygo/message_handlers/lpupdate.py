import io

def msg_lpupdate(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	lp = self.read_u32(data)
	self.cm.call_callbacks('lpupdate', player, lp)
	return data.read()

def lpupdate(self, player, lp):
	if lp > self.lp[player]:
		self.recover(player, lp - self.lp[player])
	else:
		self.damage(player, self.lp[player] - lp)

MESSAGES = {94: msg_lpupdate}

CALLBACKS = {'lpupdate': lpupdate}
