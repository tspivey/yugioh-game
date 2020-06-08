import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.duel_menu import DuelMenu
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def msg_select_option(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	size = self.read_u8(data)
	options = []
	for i in range(size):
		options.append(self.read_u32(data))
	self.cm.call_callbacks("select_option", player, options)
	return data.read()

def select_option(self, player, options):
	pl = self.players[player]
	def select(caller, idx):

		opt = options[idx]

		for p in self.players+self.watchers:

			if opt > 10000:
				string = card.get_strings(p)[opt & 0xf]
			else:
				string = p._("Unknown option %d" % opt)
				string = p.strings['system'].get(opt, string)

			if p is pl:
				p.notify(p._("You selected option {0}: {1}").format(idx + 1, string))
			else:
				p.notify(p._("{0} selected option {1}: {2}").format(pl.nickname, idx + 1, string))

		self.set_responsei(idx)
		reactor.callLater(0, process_duel, self)

	card = None
	opts = []
	for opt in options:
		if opt > 10000:
			code = opt >> 4
			card = Card(code)
			string = card.get_strings(pl)[opt & 0xf]
		else:
			string = pl._("Unknown option %d" % opt)
			string = pl.strings['system'].get(opt, string)
		opts.append(string)
	m = DuelMenu(pl._("Select option:"), no_abort=pl._("Invalid option."), prompt=pl._("Select option:"), persistent=True, restore_parser=DuelParser)
	for idx, opt in enumerate(opts):
		m.item(opt)(lambda caller, idx=idx: select(caller, idx))
	pl.notify(m)

MESSAGES = {14: msg_select_option}

CALLBACKS = {'select_option': select_option}
