import io
from twisted.internet import reactor

from ygo.card import Card
from ygo.constants import LOCATION
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import parse_ints, process_duel, check_sum, handle_error

def msg_select_sum(self, data):
	data = io.BytesIO(data[1:])
	mode = self.read_u8(data)
	player = self.read_u8(data)
	val = self.read_u32(data)
	select_min = self.read_u8(data)
	select_max = self.read_u8(data)
	count = self.read_u8(data)
	must_select = []
	for i in range(count):
		code = self.read_u32(data)
		card = Card(code)
		card.controller = self.read_u8(data)
		card.location = LOCATION(self.read_u8(data))
		card.sequence = self.read_u8(data)
		param = self.read_u32(data)
		card.param = (param&0xff, param>>16, )
		must_select.append(card)
	count = self.read_u8(data)
	select_some = []
	for i in range(count):
		code = self.read_u32(data)
		card = Card(code)
		card.controller = self.read_u8(data)
		card.location = LOCATION(self.read_u8(data))
		card.sequence = self.read_u8(data)
		param = self.read_u32(data)
		card.param = (param&0xff, param>>16, )
		select_some.append(card)
	self.cm.call_callbacks('select_sum', mode, player, val, select_min, select_max, must_select, select_some)
	return data.read()

def select_sum(self, mode, player, val, select_min, select_max, must_select, select_some):
	pl = self.players[player]

	must_select_levels = []

	if len(must_select) == 1:
		must_select_levels = list(must_select[0].param)
	elif len(must_select) > 1:
		for i in range(len(must_select)):
			if i == len(must_select) - 1:
				break
			c = must_select[i]
			for j in range(i + 1, len(must_select)):
				c2 = must_select[j]
				for l in c.param:
					for l2 in c2.param:
						must_select_levels.append(l + l2)

	else:
		must_select_levels = [0]

	if len(must_select_levels) > 1:
		must_select_levels = sorted(set(filter(lambda l: l, must_select_levels)))

	def prompt():
		if mode == 0:
			if len(must_select_levels) == 1:
				pl.notify(pl._("Select cards with a total value of %d, seperated by spaces.") % (val - must_select_levels[0]))
			else:
				pl.notify(pl._("Select cards with a total value being one of the following, seperated by spaces: %s") % (', '.join([str(val - l) for l in must_select_levels])))
		else:
			pl.notify(pl._("Select cards with a total value of at least %d, seperated by spaces.") % (val - must_select_levels[0]))
		for c in must_select:
			pl.notify(pl._("%s must be selected, automatically selected.") % c.get_name(pl))
		for i, card in enumerate(select_some):
			pl.notify("%d: %s (%s)" % (i+1, card.get_name(pl), (' ' + pl._('or') + ' ').join([str(p) for p in card.param if p > 0])))
		return pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=DuelParser)
	def error(t):
		pl.notify(t)
		return prompt()

	@handle_error
	def r(caller):
		ints = [i - 1 for i in parse_ints(caller.text)]
		if len(ints) != len(set(ints)):
			return error(pl._("Duplicate values not allowed."))
		if any(i for i in ints if i < 1 or i > len(select_some) - 1):
			return error(pl._("Value out of range."))
		selected = [select_some[i] for i in ints]
		s = []

		for i in range(len(selected)):
			if i == len(selected) - 1:
				break
			c = selected[i]
			for j in range(i + 1, len(selected)):
				c2 = selected[j]
				for l in c.param:
					for l2 in c2.param:
						s.append(l + l2)
		
		s = sorted(set(s))

		if mode == 1 and not check(must_select + selected, val):
			return error(pl._("Levels out of range."))
		if mode == 0 and not any([check_sum(selected, val - m) for m in must_select_levels]):
			return error(pl._("Selected value does not equal %d.") % (val,))
		lst = [len(ints) + len(must_select)]
		lst.extend([0] * len(must_select))
		lst.extend(ints)
		b = bytes(lst)
		self.set_responseb(b)
		reactor.callLater(0, process_duel, self)
	prompt()

def check(cards, acc):
	sum = 0
	mx = 0
	mn = 0x7fffffff
	for c in cards:
		o1 = c.param[0]
		o2 = c.param[1]
		if o2 and o2 < o1:
			ms = o2
		else:
			ms = o1
		sum += ms
		mx += max(o2, o1)
		if ms < mn:
			mn = ms
	if mx < acc or sum - mn >= acc:
		return False
	return True

MESSAGES = {23: msg_select_sum}

CALLBACKS = {'select_sum': select_sum}
