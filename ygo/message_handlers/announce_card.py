from gsb.intercept import Reader
import io
from twisted.internet import reactor

from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel
from ygo import globals
from ygo import duel

def msg_announce_card(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	size = self.read_u8(data)
	options = []
	for i in range(size):
		options.append(self.read_u32(data))
	self.cm.call_callbacks('announce_card', player, options)
	return data.read()

def announce_card(self, player, options):
	pl = self.players[player]
	def prompt():
		pl.notify(pl._("Enter the name of a card:"))
		return pl.notify(Reader, r, no_abort=pl._("Invalid command."), restore_parser=DuelParser)
	def error(text):
		pl.notify(text)
		return prompt()
	def r(caller):
		card = globals.server.get_card_by_name(pl, caller.text)
		if card is None:
			return error(pl._("No results found."))
		cd = duel.ffi.new('struct card_data *')
		duel.card_reader_callback(card.code, cd)
		if not duel.lib.declarable(cd, len(options), options):
			return error(pl._("Wrong type."))
		self.set_responsei(card.code)
		reactor.callLater(0, process_duel, self)
	prompt()

MESSAGES = {142: msg_announce_card}

CALLBACKS = {'announce_card': announce_card}
