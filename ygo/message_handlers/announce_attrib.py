import io
import natsort
from twisted.internet import reactor

from ygo.constants import AMOUNT_ATTRIBUTES, ATTRIBUTES_OFFSET
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def msg_announce_attrib(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	count = self.read_u8(data)
	avail = self.read_u32(data)
	self.cm.call_callbacks('announce_attrib', player, count, avail)
	return data.read()

def announce_attrib(self, player, count, avail):
	pl = self.players[player]
	attrmap = {pl.strings['system'][ATTRIBUTES_OFFSET+i]: (1<<i) for i in range(AMOUNT_ATTRIBUTES)}
	avail_attributes = {k: v for k, v in attrmap.items() if avail & v}
	avail_attributes_keys = natsort.natsorted(list(avail_attributes.keys()))
	avail_attributes_values = [avail_attributes[r] for r in avail_attributes_keys]
	def prompt():
		pl.notify("Type %d attributes separated by spaces." % count)
		for i, attrib in enumerate(avail_attributes_keys):
			pl.notify("%d. %s" % (i + 1, attrib))
		pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=DuelParser)
	def r(caller):
		items = caller.text.split()
		ints = []
		try:
			ints = [int(i) for i in items]
		except ValueError:
			pass
		ints = [i for i in ints if i > 0 <= len(avail_attributes_keys)]
		ints = set(ints)
		if len(ints) != count:
			pl.notify("Invalid attributes.")
			return prompt()
		value = sum(avail_attributes_values[i - 1] for i in ints)
		self.set_responsei(value)
		reactor.callLater(0, process_duel, self)
	return prompt()

MESSAGES = {141: msg_announce_attrib}

CALLBACKS = {'announce_attrib': announce_attrib}
