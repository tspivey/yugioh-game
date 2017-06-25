from _duel import ffi, lib
import os
import io
import sqlite3
import struct
import random
import binascii
import callback_manager

deck = [int(l.strip()) for l in open('deck.ydk')]
db = sqlite3.connect('cards.cdb')
db.row_factory = sqlite3.Row
LOCATION_DECK = 1
LOCATION_HAND = 2
LOCATION_MZONE = 4
LOCATION_SZONE = 8

POS_FACEUP_ATTACK = 1
POS_FACEDOWN_DEFENSE = 8
QUERY_CODE = 1
QUERY_POSITION = 0x2
QUERY_ATTACK = 0x100
QUERY_DEFENSE = 0x200

@ffi.def_extern()
def card_reader_callback(code, data):
	cd = data[0]
	row = db.execute('select * from datas where id=?', (code,)).fetchone()
	cd.code = code
	cd.alias = row['alias']
	cd.setcode = row['setcode']
	cd.type = row['type']
	cd.level = row['level']
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
		cd.level = row['level']
		cd.attack = row['atk']
		cd.defense = row['def']
		cd.race = row['race']
		cd.attribute = row['attribute']
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

class Duel:
	def __init__(self):
		self.buf = ffi.new('char[]', 4096)
		self.duel = lib.create_duel(0)
		lib.set_player_info(self.duel, 0, 8000, 5, 1)
		lib.set_player_info(self.duel, 1, 8000, 5, 1)
		self.cm = callback_manager.CallbackManager()
		self.message_map = {
			90: self.msg_draw,
			40: self.msg_new_turn,
		41: self.msg_new_phase,
		11: self.msg_idlecmd,
		1: self.msg_retry,
		2: self.msg_hint,
		18: self.msg_select_place,
		50: self.msg_move,
		60: self.msg_summoning,
		16: self.msg_select_chain,
		61: self.msg_summoned,
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
		}
		self.state = ''

	def load_deck(self, player, cards):
		random.shuffle(cards)
		for c in cards:
			lib.new_card(self.duel, c, player, player, LOCATION_DECK, 0, POS_FACEDOWN_DEFENSE);

	def start(self):
		lib.start_duel(self.duel, 0)

	def process(self):
		res = lib.process(self.duel)
		self.process_messages()
		return res

	def process_messages(self):
		l = lib.get_message(self.duel, ffi.cast('byte *', self.buf))
		data = ffi.unpack(self.buf, l)
#		print("received: %r" % data)
		while data:
			msg = int(data[0])
			fn = self.message_map.get(msg)
			if fn:
				data = fn(data)
			else:
				print("msg %d unhandled" % msg)
				data = b''

	def msg_draw(self, data):
		data = io.BytesIO(data[1:])
		player = self.read_u8(data)
		drawed = self.read_u8(data)
		cards = []
		for i in range(drawed):
			c = self.read_u32(data)
			card = Card.from_code(c)
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
			card = Card.from_code(code)
			card.controller = self.read_u8(data)
			card.location = self.read_u8(data)
			card.sequence = self.read_u8(data)
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
		target = self.read_u32(data)
		self.cm.call_callbacks('attack', attacker, target)
		return b''

	def msg_begin_damage(self, data):
		print("%r", data)
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
		print("Move: code=%d loc=%x newloc=%x reason=%x" % (code, location, newloc, reason))
		return b''

	def msg_summoning(self, data):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		location = self.read_u32(data)
		self.cm.call_callbacks('summoning', Card.from_code(code), location)
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
		self.cm.call_callbacks('select_chain', player, size, spe_count, chains)
		return b''

	def msg_summoned(self, data):
		data = io.BytesIO(data[1:])
		print("summoned: %r" % data.read())
		return b''

	def msg_set(self, data):
		data = io.BytesIO(data[1:])
		code = self.read_u32(data)
		loc = self.read_u32(data)
		print("Set: code=%d loc=%d" % (code, loc))
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

	def read_u8(self, buf):
		return struct.unpack('b', buf.read(1))[0]

	def read_u32(self, buf):
		return struct.unpack('I', buf.read(4))[0]

	def set_responsei(self, r):
		lib.set_responsei(self.duel, r)

	def set_responseb(self, r):
		buf = ffi.new('char[64]', r)
		lib.set_responseb(self.duel, ffi.cast('byte *', buf))

	def get_cards_in_location(self, player, location):
		cards = []
		flags = QUERY_CODE | QUERY_POSITION | QUERY_ATTACK | QUERY_DEFENSE
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
			cards.append(card)
		return cards

	def get_card(self, player, loc, seq):
		flags = QUERY_CODE | QUERY_POSITION
		bl = lib.query_card(self.duel, player, loc, seq, flags, ffi.cast('byte *', self.buf), False)
		buf = io.BytesIO(ffi.unpack(self.buf, bl))
		f = self.read_u32(buf)
		if f == 4:
			return
		f = self.read_u32(buf)
		code = self.read_u32(buf)
		position = self.read_u32(buf)
		card = Card.from_code(code)
		card.set_location(position)
		return card

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
