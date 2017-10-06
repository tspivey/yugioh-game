import io
from twisted.internet import reactor

from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def msg_select_place(self, data):
	data = io.BytesIO(data)
	msg = self.read_u8(data)
	player = self.read_u8(data)
	count = self.read_u8(data)
	flag = self.read_u32(data)
	self.cm.call_callbacks('select_place', player, count, flag)
	return data.read()

def select_place(self, player, count, flag):
	pl = self.players[player]
	specs = self.flag_to_usable_cardspecs(flag)
	if count == 1:
		pl.notify(pl._("Select place for card, one of %s.") % ", ".join(specs))
	else:
		pl.notify(pl._("Select %d places for card, from %s.") % (count, ", ".join(specs)))
	def r(caller):
		values = caller.text.split()
		if len(set(values)) != len(values):
			pl.notify(pl._("Duplicate values not allowed."))
			return pl.notify(DuelReader, r, no_abort=pl._("Invalid command"), restore_parser=duel_parser)
		if len(values) != count:
			pl.notify(pl._("Please enter %d values.") % count)
			return pl.notify(DuelReader, r, no_abort=pl._("Invalid command"), restore_parser=DuelParser)
		if any(value not in specs for value in values):
			pl.notify(pl._("Invalid cardspec. Try again."))
			pl.notify(DuelReader, r, no_abort=pl._("Invalid command"), restore_parser=DuelParser)
			return
		resp = b''
		for value in values:
			l, s = self.cardspec_to_ls(value)
			if value.startswith('o'):
				plr = 1 - player
			else:
				plr = player
			resp += bytes([plr, l, s])
		self.set_responseb(resp)
		reactor.callLater(0, process_duel, self)
	pl.notify(DuelReader, r, no_abort=pl._("Invalid command"), restore_parser=DuelParser)

MESSAGES = {18: msg_select_place, 24: msg_select_place}

CALLBACKS = {'select_place': select_place}
