from gsb.intercept import Menu
import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def msg_select_position(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	code = self.read_u32(data)
	card = Card(code)
	positions = self.read_u8(data)
	self.cm.call_callbacks('select_position', player, card, positions)
	return data.read()

def select_position(self, player, card, positions):
	pl = self.players[player]
	m = Menu(pl._("Select position for %s:") % (card.get_name(pl),), no_abort="Invalid option.", persistent=True, restore_parser=DuelParser)
	def set(caller, pos=None):
		self.set_responsei(pos)
		reactor.callLater(0, process_duel, self)
	if positions & 1:
		m.item(pl._("Face-up attack"))(lambda caller: set(caller, 1))
	if positions & 2:
		m.item(pl._("Face-down attack"))(lambda caller: set(caller, 2))
	if positions & 4:
		m.item(pl._("Face-up defense"))(lambda caller: set(caller, 4))
	if positions & 8:
		m.item(pl._("Face-down defense"))(lambda caller: set(caller, 8))
	pl.notify(m)

MESSAGES = {19: msg_select_position}

CALLBACKS = {'select_position': select_position}
