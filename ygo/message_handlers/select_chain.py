import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import process_duel

def msg_select_chain(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	size = self.read_u8(data)
	spe_count = self.read_u8(data)
	forced = self.read_u8(data)
	hint_timing = self.read_u32(data)
	other_timing = self.read_u32(data)
	chains = []
	for i in range(size):
		et = self.read_u8(data)
		code = self.read_u32(data)
		loc = self.read_u32(data)
		card = Card(code)
		card.set_location(loc)
		desc = self.read_u32(data)
		chains.append((et, card, desc))
	self.cm.call_callbacks('select_chain', player, size, spe_count, forced, chains)
	return data.read()

def select_chain(self, player, size, spe_count, forced, chains):
	if size == 0 and spe_count == 0:
		self.keep_processing = True
		self.set_responsei(-1)
		return
	pl = self.players[player]
	self.chaining_player = player
	op = self.players[1 - player]
	if not op.seen_waiting:
		op.notify(op._("Waiting for opponent."))
		op.seen_waiting = True
	chain_cards = [c[1] for c in chains]
	specs = {}
	for i in range(len(chains)):
		card = chains[i][1]
		card.chain_index = i
		desc = chains[i][2]
		cs = card.get_spec(pl)
		chain_count = chain_cards.count(card)
		if chain_count > 1:
			cs += chr(ord('a')+list(specs.values()).count(card))
		specs[cs] = card
		card.chain_spec = cs
		card.effect_description = card.get_effect_description(pl, desc, True)
	def prompt():
		if forced:
			pl.notify(pl._("Select chain:"))
		else:
			pl.notify(pl._("Select chain (c to cancel):"))
		for card in chain_cards:
			if card.effect_description == '':
				pl.notify("%s: %s" % (card.chain_spec, card.get_name(pl)))
			else:
				pl.notify("%s (%s): %s"%(card.chain_spec, card.get_name(pl), card.effect_description))
		if forced:
			prompt = pl._("Select card to chain:")
		else:
			prompt = pl._("Select card to chain (c = cancel):")
		pl.notify(DuelReader, r, no_abort=pl._("Invalid command."),
		prompt=prompt, restore_parser=DuelParser)
	def r(caller):
		if caller.text == 'c' and not forced:
			self.set_responsei(-1)
			reactor.callLater(0, process_duel, self)
			return
		if caller.text.startswith('i'):
			info = True
			caller.text = caller.text[1:]
		else:
			info = False
		if caller.text not in specs:
			pl.notify(pl._("Invalid spec."))
			return prompt()
		card = specs[caller.text]
		idx = card.chain_index
		if info:
			self.show_info(card, pl)
			return prompt()
		self.set_responsei(idx)
		reactor.callLater(0, process_duel, self)
	prompt()

MESSAGES = {16: msg_select_chain}

CALLBACKS = {'select_chain': select_chain}
