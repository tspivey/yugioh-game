from _duel import ffi, lib
import os
import io
import sqlite3
import struct
import random
import binascii
import callback_manager
from functools import partial

db = sqlite3.connect('locale/en/cards.cdb')
db.row_factory = sqlite3.Row
LOCATION_DECK = 1
LOCATION_HAND = 2
LOCATION_MZONE = 4
LOCATION_SZONE = 8
LOCATION_GRAVE = 0x10
LOCATION_REMOVED = 0x20
LOCATION_EXTRA = 0x40

POS_FACEUP_ATTACK = 1
POS_FACEDOWN_DEFENSE = 8
QUERY_CODE = 1
QUERY_POSITION = 0x2
QUERY_ATTACK = 0x100
QUERY_DEFENSE = 0x200
QUERY_COUNTERS = 0x20000

TYPE_FUSION = 0x40
TYPE_SYNCHRO = 0x2000
TYPE_XYZ = 0x800000
TYPE_PENDULUM = 0x1000000
TYPE_LINK = 0x4000000

@ffi.def_extern()
def card_reader_callback(code, data):
	cd = data[0]
	row = db.execute('select * from datas where id=?', (code,)).fetchone()
	cd.code = code
	cd.alias = row['alias']
	cd.setcode = row['setcode']
	cd.type = row['type']
	cd.level = row['level'] & 0xff
	cd.lscale = (row['level'] >> 24) & 0xff
	cd.rscale = (row['level'] >> 16) & 0xff
	cd.attack = row['atk']
	cd.defense = row['def']
	cd.race = row['race']
	cd.attribute = row['attribute']
	return 0

lib.set_card_reader(lib.card_reader_callback)

scriptbuf = ffi.new('char[131072]')
@ffi.def_extern()
def script_reader_callback(name, lenptr):
	fn = ffi.string(name)
	if not os.path.exists(fn):
		lenptr[0] = 0
		return ffi.new('byte *', None)
	s = open(fn, 'rb').read()
	buf = ffi.buffer(scriptbuf)
	buf[0:len(s)] = s
	lenptr[0] = len(s)
	return ffi.cast('byte *', scriptbuf)

lib.set_script_reader(lib.script_reader_callback)

class Card(object):
	@classmethod
	def from_code(cls, code):
		row = db.execute('select * from datas where id=?', (code,)).fetchone()
		cd = cls()
		cd.code = code
		cd.alias = row['alias']
		cd.setcode = row['setcode']
		cd.type = row['type']
		cd.level = row['level'] & 0xff
		cd.lscale = (row['level'] >> 24) & 0xff
		cd.rscale = (row['level'] >> 16) & 0xff
		cd.attack = row['atk']
		cd.defense = row['def']
		cd.race = row['race']
		cd.attribute = row['attribute']
		cd.category = row['category']
		row = db.execute('select * from texts where id=?', (code,)).fetchone()
		cd.name = row['name']
		cd.desc = row['desc']
		cd.strings = []
		for i in range(1, 17):
			cd.strings.append(row['str'+str(i)])
		return cd

	def set_location(self, location):
		self.controller = location & 0xff
		self.location = (location >> 8) & 0xff;
		self.sequence = (location >> 16) & 0xff
		self.position = (location >> 24) & 0xff

	def __eq__(self, other):
		return self.code == other.code and self.location == other.location and self.sequence == other.sequence

	def position_name(self):
		if self.position == 0x1:
			return "face-up attack"
		elif self.position == 0x2:
			return "face-down attack"
		elif self.position == 0x4:
			return "face-up defense"
		elif self.position == 0x5:
			return "face-up"
		elif self.position == 0x8:
			return "face-down defense"
		elif self.position == 0xa:
			return "face down"
		return str(self.position)

	RACES = ("Warrior", "Spellcaster", "Fairy", "Fiend", "Zombie", "Machine",
	"Aqua", "Pyro", "Rock", "Windbeast", "Plant", "Insect",
	"Thunder", "Dragon", "Beast", "Beast Warrior", "Dinosaur", "Fish",
	"Sea Serpent", "Reptile", "Psycho", "Divine", "Creator God", "Wyrm",
	"Cybers")
	def info(self):
		lst = []
		types = []
		t = str(self.type)
		if self.type & 1:
			types.append("Monster")
		elif self.type & 2:
			types.append("Spell")
		elif self.type & 4:
			types.append("Trap")
		if self.type & 0x20:
			types.append("Effect")
		if self.type & 0x40:
			types.append("Fusion")
		if self.attribute & 1:
			types.append("Earth")
		elif self.attribute & 2:
			types.append("Water")
		elif self.attribute & 4:
			types.append("Fire")
		elif self.attribute & 8:
			types.append("Wind")
		elif self.attribute & 0x10:
			types.append("Light")
		elif self.attribute & 0x20:
			types.append("Dark")
		elif self.attribute & 0x40:
			types.append("Divine")
		for i, race in enumerate(self.RACES):
			if self.race & (1 << i):
				types.append(race)
		lst.append("%s (%s)" % (self.name, ", ".join(types)))
		lst.append("Attack: %d Defense: %d Level: %d" % (self.attack, self.defense, self.level))
		lst.append(self.desc)
		return "\n".join(lst)

	def __repr__(self):
		return '<%s>' % self.name

class Duel:
	def __init__(self, seed=None):
		self.buf = ffi.new('char[]', 4096)
		if seed is None:
			seed = random.randint(0, 0xffffffff)
		self.seed = seed
		self.duel = lib.create_duel(seed)
		lib.set_player_info(self.duel, 0, 8000, 5, 1)
		lib.set_player_info(self.duel, 1, 8000, 5, 1)
		self.cm = callback_manager.CallbackManager()
		self.started = False
		self.message_map = {
			90: self.msg_draw,
			40: self.msg_new_turn,
		41: self.msg_new_phase,
		11: self.msg_idlecmd,
		1: self.msg_retry,
		2: self.msg_hint,
		18: self.msg_select_place,
		24: self.msg_select_place,
		50: self.msg_move,
		56: self.msg_field_disabled,
		60: self.msg_summoning,
		16: self.msg_select_chain,
		61: self.msg_summoned,
		64: self.msg_flipsummoning,
		54: self.msg_set,
		10: self.msg_select_battlecmd,
		110: self.msg_attack,
		113: self.msg_begin_damage,
		114: self.msg_end_damage,
		111: self.msg_battle,
		91: self.msg_damage,
		15: self.msg_select_card,
		14: self.msg_select_option,
		92: self.msg_recover,
		20: self.msg_select_tribute,
		53: self.msg_pos_change,
		70: self.msg_chaining,
		19: self.msg_select_position,
		13: self.msg_yesno,
		62: partial(self.msg_summoning, special=True),
		12: self.msg_select_effectyn,
		5: self.msg_win,
		100: self.msg_pay_lpcost,
		21: self.msg_sort_chain,
		141: self.msg_announce_attrib,
		142: self.msg_announce_card,
		143: self.msg_announce_number,
		144: self.msg_announce_card_filter,
		23: self.msg_select_sum,
		140: self.msg_announce_race,
		22: self.msg_select_counter,
		83: self.msg_become_target,
		25: self.msg_sort_card,
		130: self.msg_toss_coin,
		131: partial(self.msg_toss_coin, dice=True),
		31: self.msg_confirm_cards,
		73: self.msg_chain_solved,
		93: self.msg_equip,
		94: self.msg_lpupdate,
		}
		self.state = ''
		self.cards = [None, None]
		self.revealed = {}

	def load_deck(self, player, cards, shuffle=True):
		self.cards[player] = cards[:]
		if shuffle:
			random.shuffle(self.cards[player])
		for c in self.cards[player][::-1]:
			lib.new_card(self.duel, c, player, player, LOCATION_DECK, 0, POS_FACEDOWN_DEFENSE);

	def start(self):
		lib.start_duel(self.duel, 0)
		self.started = True

	def end(self):
		lib.end_duel(self.duel)
		self.started = False

	def process(self):
		res = lib.process(self.duel)
		l = lib.get_message(self.duel, ffi.cast('byte *', self.buf))
		data = ffi.unpack(self.buf, l)
		self.cm.call_callbacks('debug', event_type='process', result=res, data=data.decode('latin1'))
		data = self.process_messages(data)
		return res

	def process_messages(self, data):
		while data:
			msg = int(data[0])
			fn = self.message_map.get(msg)
			if fn:
				data = fn(data)
			else:
				print("msg %d unhandled" % msg)
				data = b''
		return data

	def msg_draw(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		drawed = self.read_u8(data)
		cards = []
		for i in range(drawed):
			c = self.read_u32(data)
			card = Card.from_code(c & 0x7fffffff)
			cards.append(card)
		self.cm.call_callbacks('draw', player, cards)
		return data.read()

	def msg_new_turn(self, data):
		tp = int(data[1])
		self.cm.call_callbacks('new_turn', tp)
		return data[2:]

	def msg_new_phase(self, data):
		phase = struct.unpack('h', data[1:])[0]
		self.cm.call_callbacks('phase', phase)
		return b''

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
		return b''

	def read_cardlist(self, data, extra=False, extra8=False):
		res = []
		size = self.read_u8(data)
		for i in range(size):
			code = self.read_u32(data)
			controller = self.read_u8(data)
			location = self.read_u8(data)
			sequence = self.read_u8(data)
			card = self.get_card(controller, location, sequence)
			card.extra = 0
			if extra:
				if extra8:
					card.extra = self.read_u8(data)
				else:
					card.extra = self.read_u32(data)
			res.append(card)
		return res

	def msg_retry(self, buf):
		print("retry")
		return ''

	def msg_hint(self, data):
		data = io.BytesIO(data[1:])
		msg = self.read_u8(data)
		player = self.read_u8(data)
		value = self.read_u32(data)
		self.cm.call_callbacks('hint', msg, player, value)
		return b''

	def msg_select_place(self, data):
		data = io.BytesIO(data)
		msg = self.read_u8(data)
		player = self.read_u8(data)
		count = self.read_u8(data)
		flag = self.read_u32(data)
		self.cm.call_callbacks('select_place', player, count, flag)
		return b''

	def msg_select_battlecmd(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		activatable = self.read_cardlist(data, True)
		attackable = self.read_cardlist(data, True, True)
		to_m2 = self.read_u8(data)
		to_ep = self.read_u8(data)
		self.cm.call_callbacks('select_battlecmd', player, activatable, attackable, to_m2, to_ep)
		return b''

	def msg_attack(self, data):
		data = io.BytesIO(data[1:])
		attacker = self.read_u32(data)
		ac = attacker & 0xff
		al = (attacker >> 8) & 0xff
		aseq = (attacker >> 16) & 0xff
		apos = (attacker >> 24) & 0xff
		target = self.read_u32(data)
		tc = target & 0xff
		tl = (target >> 8) & 0xff
		tseq = (target >> 16) & 0xff
		tpos = (target >> 24) & 0xff
		self.cm.call_callbacks('attack', ac, al, aseq, apos, tc, tl, tseq, tpos)
		return b''

	def msg_begin_damage(self, data):
		self.cm.call_callbacks('begin_damage')

	def msg_end_damage(self, data):
		self.cm.call_callbacks('end_damage')

	def msg_battle(self, data):
		data = io.BytesIO(data[1:])
		attacker = self.read_u32(data)
		aa = self.read_u32(data)
		ad = self.read_u32(data)
		bd0 = self.read_u8(data)
		tloc = self.read_u32(data)
		da = self.read_u32(data)
		dd = self.read_u32(data)
		bd1 = self.read_u8(data)
		self.cm.call_callbacks('battle', attacker, aa, ad, bd0, tloc, da, dd, bd1)
		return b''

	def msg_select_card(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		cancelable = self.read_u8(data)
		min = self.read_u8(data)
		max = self.read_u8(data)
		size = self.read_u8(data)
		cards = []
		for i in range(size):
			code = self.read_u32(data)
			loc = self.read_u32(data)
			c = loc & 0xff
			l = (loc >> 8) & 0xff;
			s = (loc >> 16) & 0xff
			card = self.get_card(c, l, s)
			card = Card.from_code(code)
			card.set_location(loc)
			cards.append(card)
		self.cm.call_callbacks('select_card', player, cancelable, min, max, cards)
		return b''

	def msg_select_tribute(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		cancelable = self.read_u8(data)
		min = self.read_u8(data)
		max = self.read_u8(data)
		size = self.read_u8(data)
		cards = []
		for i in range(size):
			code = self.read_u32(data)
			card = Card.from_code(code)
			card.controller = self.read_u8(data)
			card.location = self.read_u8(data)
			card.sequence = self.read_u8(data)
			card.position = self.get_card(card.controller, card.location, card.sequence).position
			card.release_param = self.read_u8(data)
			cards.append(card)
		self.cm.call_callbacks('select_tribute', player, cancelable, min, max, cards)
		return b''

	def msg_damage(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		amount = self.read_u32(data)
		self.cm.call_callbacks('damage', player, amount)

	def msg_recover(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		amount = self.read_u32(data)
		self.cm.call_callbacks('recover', player, amount)

	def msg_move(self, data):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		location = self.read_u32(data)
		newloc = self.read_u32(data)
		reason = self.read_u32(data)
		self.cm.call_callbacks('move', code, location, newloc, reason)
		return b''

	def msg_field_disabled(self, data):
		data = io.BytesIO(data[1:])
		locations = self.read_u32(data)
		self.cm.call_callbacks('field_disabled', locations)
		return b''

	def msg_summoning(self, data, special=False):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		card = Card.from_code(code)
		card.set_location(self.read_u32(data))
		self.cm.call_callbacks('summoning', card, special=special)
		return b''

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
			card = Card.from_code(code)
			card.set_location(loc)
			desc = self.read_u32(data)
			chains.append((et, card, desc))
		self.cm.call_callbacks('select_chain', player, size, spe_count, forced, chains)
		return b''

	def msg_summoned(self, data):
		data = io.BytesIO(data[1:])
		return b''

	def msg_set(self, data):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		loc = self.read_u32(data)
		card = Card.from_code(code)
		card.set_location(loc)
		self.cm.call_callbacks('set', card)
		return b''

	def msg_select_option(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		size = self.read_u8(data)
		options = []
		for i in range(size):
			options.append(self.read_u32(data))
		self.cm.call_callbacks("select_option", player, options)
		return b''

	def msg_pos_change(self, data):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		card = Card.from_code(code)
		card.controller = self.read_u8(data)
		card.location = self.read_u8(data)
		card.sequence = self.read_u8(data)
		prevpos = self.read_u8(data)
		card.position = self.read_u8(data)
		self.cm.call_callbacks('pos_change', card, prevpos)
		return b''

	def msg_chaining(self, data):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		card = Card.from_code(code)
		card.set_location(self.read_u32(data))
		tc = self.read_u8(data)
		tl = self.read_u8(data)
		ts = self.read_u8(data)
		desc = self.read_u32(data)
		cs = self.read_u8(data)
		self.cm.call_callbacks('chaining', card, tc, tl, ts, desc, cs)
		return b''

	def msg_select_position(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		code = self.read_u32(data)
		card = Card.from_code(code)
		positions = self.read_u8(data)
		self.cm.call_callbacks('select_position', player, card, positions)
		return b''

	def msg_yesno(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		desc = self.read_u32(data)
		self.cm.call_callbacks('yesno', player, desc)
		return b''

	def msg_select_effectyn(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		card = Card.from_code(self.read_u32(data))
		card.set_location(self.read_u32(data))
		self.cm.call_callbacks('select_effectyn', player, card)
		return b''

	def msg_win(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		reason = self.read_u8(data)
		self.cm.call_callbacks('win', player, reason)
		return b''

	def msg_pay_lpcost(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		cost = self.read_u32(data)
		self.cm.call_callbacks('pay_lpcost', player, cost)
		return b''

	def msg_sort_chain(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		size = self.read_u8(data)
		cards = []
		for i in range(size):
			code = self.read_u32(data)
			card = Card.from_code(code)
			card.controller = self.read_u8(data)
			card.location = self.read_u8(data)
			card.sequence = self.read_u8(data)
			cards.append(card)
		self.cm.call_callbacks('sort_chain', player, cards)
		return b''

	def msg_announce_attrib(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		count = self.read_u8(data)
		avail = self.read_u32(data)
		self.cm.call_callbacks('announce_attrib', player, count, avail)
		return b''

	def msg_announce_card(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		type = self.read_u32(data)
		self.cm.call_callbacks('announce_card', player, type)
		return b''

	def msg_announce_number(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		size = self.read_u8(data)
		opts = [self.read_u32(data) for i in range(size)]
		self.cm.call_callbacks('announce_number', player, opts)
		return b''

	def msg_announce_card_filter(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		size = self.read_u8(data)
		options = []
		for i in range(size):
			options.append(self.read_u32(data))
		self.cm.call_callbacks('announce_card_filter', player, options)
		return b''

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
			card = Card.from_code(code)
			card.controller = self.read_u8(data)
			card.location = self.read_u8(data)
			card.sequence = self.read_u8(data)
			card.param = self.read_u32(data)
			must_select.append(card)
		count = self.read_u8(data)
		select_some = []
		for i in range(count):
			code = self.read_u32(data)
			card = Card.from_code(code)
			card.controller = self.read_u8(data)
			card.location = self.read_u8(data)
			card.sequence = self.read_u8(data)
			card.param = self.read_u32(data)
			select_some.append(card)
		self.cm.call_callbacks('select_sum', mode, player, val, select_min, select_max, must_select, select_some)
		return b''

	def msg_select_counter(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		countertype = self.read_u16(data)
		count = self.read_u16(data)
		size = self.read_u8(data)
		cards = []
		for i in range(size):
			card = Card.from_code(self.read_u32(data))
			card.controller = self.read_u8(data)
			card.location = self.read_u8(data)
			card.sequence = self.read_u8(data)
			card.counter = self.read_u16(data)
			cards.append(card)
		self.cm.call_callbacks('select_counter', player, countertype, count, cards)
		return b''

	def msg_become_target(self, data):
		data = io.BytesIO(data[1:])
		u = self.read_u8(data)
		target = self.read_u32(data)
		tc = target & 0xff
		tl = (target >> 8) & 0xff
		tseq = (target >> 16) & 0xff
		tpos = (target >> 24) & 0xff
		self.cm.call_callbacks('become_target', tc, tl, tseq)
		return data.read()

	def msg_announce_race(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		count = self.read_u8(data)
		avail = self.read_u32(data)
		self.cm.call_callbacks('announce_race', player, count, avail)
		return b''

	def msg_sort_card(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		size = self.read_u8(data)
		cards = []
		for i in range(size):
			card = Card.from_code(self.read_u32(data))
			card.controller = self.read_u8(data)
			card.location = self.read_u8(data)
			card.sequence = self.read_u8(data)
			cards.append(card)
		self.cm.call_callbacks('sort_card', player, cards)
		return b''

	def msg_toss_coin(self, data, dice=False):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		count = self.read_u8(data)
		options = [self.read_u8(data) for i in range(count)]
		if dice:
			self.cm.call_callbacks('toss_dice', player, options)
		else:
			self.cm.call_callbacks('toss_coin', player, options)
		return b''

	def msg_confirm_cards(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		size = self.read_u8(data)
		cards = []
		for i in range(size):
			code = self.read_u32(data)
			c = self.read_u8(data)
			l = self.read_u8(data)
			s = self.read_u8(data)
			card = self.get_card(c, l, s)
			cards.append(card)
		self.cm.call_callbacks('confirm_cards', player, cards)
		return b''

	def msg_chain_solved(self, data):
		data = io.BytesIO(data[1:])
		count = self.read_u8(data)
		self.cm.call_callbacks('chain_solved', count)
		return b''

	def msg_equip(self, data):
		data = io.BytesIO(data[1:])
		loc = self.read_u32(data)
		target = self.read_u32(data)
		u = self.unpack_location(loc)
		card = self.get_card(u[0], u[1], u[2])
		u = self.unpack_location(target)
		target = self.get_card(u[0], u[1], u[2])
		self.cm.call_callbacks('equip', card, target)
		return b''

	def msg_lpupdate(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		lp = self.read_u32(data)
		self.cm.call_callbacks('lpupdate', player, lp)
		return b''

	def msg_flipsummoning(self, data):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		location = self.read_u32(data)
		c = location & 0xff
		loc = (location >> 8) & 0xff;
		seq = (location >> 16) & 0xff
		card = self.get_card(c, loc, seq)
		self.cm.call_callbacks('flipsummoning', card)
		return b''

	def read_u8(self, buf):
		return struct.unpack('b', buf.read(1))[0]

	def read_u16(self, buf):
		return struct.unpack('h', buf.read(2))[0]

	def read_u32(self, buf):
		return struct.unpack('I', buf.read(4))[0]

	def set_responsei(self, r):
		lib.set_responsei(self.duel, r)
		self.cm.call_callbacks('debug', event_type='set_responsei', response=r)

	def set_responseb(self, r):
		buf = ffi.new('char[64]', r)
		lib.set_responseb(self.duel, ffi.cast('byte *', buf))
		self.cm.call_callbacks('debug', event_type='set_responseb', response=r.decode('latin1'))

	def get_cards_in_location(self, player, location):
		cards = []
		flags = QUERY_CODE | QUERY_POSITION | QUERY_ATTACK | QUERY_DEFENSE | QUERY_COUNTERS
		bl = lib.query_field_card(self.duel, player, location, flags, ffi.cast('byte *', self.buf), False)
		buf = io.BytesIO(ffi.unpack(self.buf, bl))
		while True:
			if buf.tell() == bl:
				break
			length = self.read_u32(buf)
			if length == 4:
				continue #No card here
			f = self.read_u32(buf)
			code = self.read_u32(buf)
			card = Card.from_code(code)
			position = self.read_u32(buf)
			card.set_location(position)
			card.attack = self.read_u32(buf)
			card.defense = self.read_u32(buf)
			cs = self.read_u32(buf)
			card.counters = []
			for i in range(cs):
				card.counters.append(self.read_u32(buf))
			cards.append(card)
		return cards

	def get_card(self, player, loc, seq):
		flags = QUERY_CODE | QUERY_ATTACK | QUERY_DEFENSE | QUERY_POSITION
		bl = lib.query_card(self.duel, player, loc, seq, flags, ffi.cast('byte *', self.buf), False)
		buf = io.BytesIO(ffi.unpack(self.buf, bl))
		f = self.read_u32(buf)
		if f == 4:
			return
		f = self.read_u32(buf)
		code = self.read_u32(buf)
		card = Card.from_code(code)
		position = self.read_u32(buf)
		card.set_location(position)
		card.attack = self.read_u32(buf)
		card.defense = self.read_u32(buf)
		return card

	def unpack_location(self, loc):
		controller = loc & 0xff
		location = (loc >> 8) & 0xff
		sequence = (loc >> 16) & 0xff
		position = (loc >> 24) & 0xff
		return (controller, location, sequence, position)

class TestDuel(Duel):
	def __init__(self):
		super(TestDuel, self).__init__()
		self.cm.register_callback('draw', self.on_draw)

	def on_draw(self, player, cards):
		print("player %d draw %d cards:" % (player, len(cards)))
		for c in cards:
			print(c.name + ": " + c.desc)

if __name__ == '__main__':
	d = TestDuel()
	d.load_deck(0, deck)
	d.load_deck(1, deck)
	d.start()

	while True:
		flag = d.process()
		if flag & 0x10000:
			resp = input()
			if resp.startswith('`'):
				b = binascii.unhexlify(resp[1:])
				d.set_responseb(b)
			else:
				resp = int(resp, 16)
				d.set_responsei(resp)
