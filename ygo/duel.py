try:
	from _duel import ffi, lib
	DUEL_AVAILABLE = True
except ImportError as exc:
	print(exc)
	DUEL_AVAILABLE = False

import os
import io
import struct
import random
import binascii
import pkgutil
import re
import datetime
import natsort
from twisted.internet import reactor

from . import callback_manager
from .card import Card, Location
from .constants import *
from .constants import __
from .duel_reader import DuelReader
from .invite.joinable import Joinable
from .utils import process_duel, handle_error
from . import globals
from . import message_handlers
from .channels.say import Say
from .channels.tag import Tag
from .channels.watchers import Watchers

if DUEL_AVAILABLE:
	setcodes = ffi.new("uint16_t[9]")
	@ffi.def_extern()
	def card_reader_callback(payload, code, data):
		cd = data[0]
		row = globals.language_handler.primary_database.execute('select * from datas where id=?', (code,)).fetchone()
		cd.code = code
		cd.alias = row['alias']
		setcode = row['setcode']
		i = 0
		while setcode != 0:
			setcodes[i] = setcode & 0xffff
			setcode >>= 16
			i += 1
		setcodes[i] = 0
		cd.setcodes = setcodes
		cd.type = row['type']
		cd.level = row['level'] & 0xff
		cd.lscale = (row['level'] >> 24) & 0xff
		cd.rscale = (row['level'] >> 16) & 0xff
		cd.attack = row['atk']
		cd.defense = row['def']
		if cd.type & TYPE.LINK:
			cd.link_marker = cd.defense
			cd.defense = 0
		else:
			cd.link_marker = 0
		cd.race = row['race']
		cd.attribute = row['attribute']

	scriptbuf = ffi.new('char[131072]')
	@ffi.def_extern()
	def script_reader_callback(payload, duel, name):
		fn = ffi.string(name).decode('utf-8')
#		print(f"script reader: {fn}")
		path = find_script(fn)
		if path is None:
			return 0
		load_script(duel, path, fn)
		return 1

	@ffi.def_extern()
	def log_handler_callback(payload, msg, type):
		msg = ffi.string(msg)
		print(f"log: {type} {msg}")
		return None

def find_script(fn):
	path = os.path.join('script', fn)
	if os.path.exists(path):
		return path
	path = os.path.join('script', 'official', fn)
	if os.path.exists(path):
		return path
	path = os.path.join('script', 'unofficial', fn)
	if os.path.exists(path):
		return path
	print(f"Script {fn} not found")

def load_script(duel, path, name):
		s = open(path, 'rb').read()
		buf = ffi.buffer(scriptbuf)
		buf[0:len(s)] = s
		lib.OCG_LoadScript(duel, ffi.cast('char *', scriptbuf), len(s), name.encode('utf-8'))

class Duel(Joinable):
	def __init__(self, seed=None):
		Joinable.__init__(self)
		self.buf = ffi.new('char[]', 4096)
		if seed is None:
			seed = (random.randint(0, 2**64), random.randint(0, 2**64), random.randint(0, 2**64), random.randint(0, 2**64))
		self.seed = seed
		options = ffi.new("OCG_DuelOptions  *")
		for i in range(4):
			options.seed[i] = seed[i]
		options.flags = DuelOptions.DUEL_MODE_MR5
		options.team1.startingLP = 8000
		options.team1.startingDrawCount = 5
		options.team1.drawCountPerTurn = 1
		options.team2.startingLP = 8000
		options.team2.startingDrawCount = 5
		options.team2.drawCountPerTurn = 1
		options.cardReader = lib.card_reader_callback
		options.scriptReader = lib.script_reader_callback
		options.logHandler = lib.log_handler_callback
		options.enableUnsafeLibraries = 1
		self.options = options
		self.cm = callback_manager.CallbackManager()
		self.keep_processing = False
		self.to_ep = False
		self.to_m2 = False
		self.current_phase = 0
		self.watchers = []
		self.private = False
		self.started = False
		self.debug_mode = False
		self.debug_fp = None
		self.players = [None, None]
		self.tag_players = []
		self.lp = [8000, 8000]
		self.started = False
		self.message_map = {}
		self.state = ''
		self.cards = [None, None]
		self.tag_cards = [None, None]
		self.revealed = {}
		self.say = Say()
		self.watch = Watchers()
		self.tags = [Tag(), Tag()]
		self.bind_message_handlers()
		self.pause_timer = None
		self.revealing = [False, False]

	def set_player_info(self, player, lp):
		self.lp[player] = lp
		if player == 0:
			self.options.team1.startingLP = lp
		elif player == 1:
			self.options.team2.startingLP = lp

	def load_deck(self, player, shuffle = True, tag = False):
		full_deck = player.deck['cards'][:]
		c = []
		fusion = []
		xyz = []
		synchro = []
		link = []

		for tc in full_deck[::-1]:
			cc = Card(tc)
			if cc.extra:
				if cc.type & TYPE.FUSION:
					fusion.append([tc, cc.level])
				if cc.type & TYPE.XYZ:
					xyz.append([tc, cc.level])
				if cc.type & TYPE.SYNCHRO:
					synchro.append([tc, cc.level])
				if cc.type & TYPE.LINK:
					link.append([tc, cc.level])
			else:
				c.append(tc)

		if shuffle is True:
			random.shuffle(c)

		conv = lambda lvl: lvl[1]
		fusion.sort(key=conv, reverse=True)
		xyz.sort(key=conv, reverse=True)
		synchro.sort(key=conv, reverse=True)
		link.sort(key=conv, reverse=True)

		for tc in fusion:
			c.append(tc[0])
		for tc in xyz:
			c.append(tc[0])
		for tc in synchro:
			c.append(tc[0])
		for tc in link:
			c.append(tc[0])

		if tag is True:
			self.tag_cards[player.duel_player] = c
		else:
			self.cards[player.duel_player] = c
		for sc in c[::-1]:
			info = ffi.new("OCG_NewCardInfo *")
			info.team = player.duel_player
			info.con = player.duel_player
			info.duelist = 0
			info.code = sc
			info.pos = POSITION.FACEDOWN_DEFENSE.value
			if tag is True:
				if Card(sc).extra:
					info.loc = LOCATION.EXTRA.value
				else:
					info.loc = LOCATION.DECK.value
			else:
				info.loc = LOCATION.DECK.value
			lib.OCG_DuelNewCard(self.duel, info[0])

	def add_players(self, players, shuffle_players=True, shuffle_decks = True):
		if len(players) == 4:
			teams = [[players[0], players[1]], [players[2], players[3]]]
			if shuffle_players is True:
				random.shuffle(teams)
				random.shuffle(teams[0])
				random.shuffle(teams[1])
			self.players = [teams[0][0], teams[1][0]]
			self.tag_players = [teams[0][1], teams[1][1]]
		else:
			self.players = list(players)
			if shuffle_players is True:
				random.shuffle(self.players)

		self.watchers = self.tag_players[:]

		for i in range(2):
			self.players[i].duel_player = i
			self.players[i].duel = self
			self.players[i].set_parser('DuelParser')
			self.say.add_recipient(self.players[i])
			self.watch.add_recipient(self.players[i])
			self.tags[i].add_recipient(self.players[i])
			self.load_deck(self.players[i], shuffle_decks)
			if len(self.tag_players) > i:
				self.tag_players[i].duel_player = i
				self.tag_players[i].duel = self
				self.tag_players[i].set_parser('DuelParser')
				self.say.add_recipient(self.tag_players[i])
				self.watch.add_recipient(self.tag_players[i])
				self.tags[i].add_recipient(self.tag_players[i])
				self.load_deck(self.tag_players[i], shuffle_decks, True)

	def create(self, rules):
		duel_ptr = ffi.new("OCG_Duel*")
		res = lib.OCG_CreateDuel(duel_ptr, self.options[0])
		self.duel = duel_ptr[0]
		load_script(self.duel, "script/constant.lua", "constant.lua")
		load_script(self.duel, "script/utility.lua", "utility.lua")

	def start(self):
		if os.environ.get('DEBUG', 0):
			self.start_debug(options)
		lib.OCG_StartDuel(self.duel)
		self.started = True
		for i, pl in enumerate(self.players):
			pl.notify(pl._("Duel created. You are player %d.") % i)
			pl.notify(pl._("Type help dueling for a list of usable commands."))
			if len(self.tag_players) > i:
				pl = self.tag_players[i]
				pl.notify(pl._("Duel created. You are player %d.") % i)
				pl.notify(pl._("Type help dueling for a list of usable commands."))
				pl.notify(pl._("%s will go first.")%(self.players[i].nickname))
		reactor.callLater(0, process_duel, self)

	def end(self, timeout=False):
		if not timeout and self.pause_timer:
			self.pause_timer.cancel()
		self.pause_timer = None
		lib.OCG_DestroyDuel(self.duel)
		self.started = False
		for pl in self.watchers:
			if pl.watching is True:
				pl.notify(pl._("Watching stopped."))
		for pl in self.players + self.watchers:
			pl.duel = None
			pl.duel_player = 0
			pl.watching = False
			pl.card_list = []
			self.say.remove_recipient(pl)
			self.watch.remove_recipient(pl)
			self.tags[0].remove_recipient(pl)
			self.tags[1].remove_recipient(pl)
			self.room.restore(pl)
		if self.debug_mode is True and self.debug_fp is not None:
			self.debug_fp.close()
		self.room.process()
		self.room = None
		self.duel = None

	def process(self):
		res = lib.OCG_DuelProcess(self.duel)
		length = ffi.new('uint32_t *')
		buf = lib.OCG_DuelGetMessage(self.duel, length)
		data = ffi.unpack(ffi.cast('char *', buf), length[0])
		self.cm.call_callbacks('debug', event_type='process', result=res, data=data.decode('latin1'))
		print(f"process: res={res} length={length[0]}")
		data = self.process_messages(data)
		return res

	@handle_error
	def process_messages(self, data):
		while data:
			length = struct.unpack('i', data[:4])[0]
			data = data[4:]
			if not data: break
			msg = int(data[0])
			print(f"process {msg}")
			fn = self.message_map.get(msg)
			if fn:
				data = fn(data)
			else:
				print("msg %d unhandled" % msg)
				data = b''
		return data

	def read_cardlist(self, data, extra=False, extra8=False, seq8=False):
		res = []
		size = self.read_u32(data)
		for i in range(size):
			code = self.read_u32(data)
			controller = self.read_u8(data)
			location = LOCATION(self.read_u8(data))
			if seq8: # for repositionable in MSG_SELECT_IDLECMD
				sequence = self.read_u8(data)
			else:
				sequence = self.read_u32(data)
			card = self.get_card(controller, location, sequence)
			if extra:
				if extra8:
					card.data = self.read_u8(data)
				else:
					card.data = self.read_u64(data)
					card.client_mode = self.read_u8(data)
			res.append(card)
		return res

	def read_u8(self, buf):
		return struct.unpack('b', buf.read(1))[0]

	def read_u16(self, buf):
		return struct.unpack('h', buf.read(2))[0]

	def read_u32(self, buf):
		return struct.unpack('I', buf.read(4))[0]

	def read_u64(self, buf):
		return struct.unpack('Q', buf.read(8))[0]

	def read_query(self, buf):
		begin = buf.tell()
		size = self.read_u16(buf)
		if size == 0:
			return None, None
		type = QUERY(self.read_u32(buf))
		if type in (QUERY.CODE, QUERY.POSITION, QUERY.ALIAS, QUERY.TYPE, QUERY.LEVEL, QUERY.RANK,
		QUERY.ATTRIBUTE, QUERY.ATTACK, QUERY.DEFENSE, QUERY.BASE_ATTACK, QUERY.BASE_DEFENSE,
		QUERY.REASON, QUERY.COVER, QUERY.LSCALE, QUERY.RSCALE):
			data = (self.read_u32(buf),)
		elif type == QUERY.EQUIP_CARD:
			# Controller, location, sequence, position
			data = (self.read_u8(buf), self.read_u8(buf), self.read_u32(buf), self.read_u32(buf))
		elif type == QUERY.OVERLAY_CARD:
			xyz_list = []
			xyz = self.read_u32(buf)
			for i in range(xyz):
				xyz_list.append(self.read_u32(buf))
			data = (xyz_list,)
		elif type == QUERY.COUNTERS:
			counters = []
			num_counters = self.read_u32(buf)
			for i in range(num_counters):
				counters.append(self.read_u32(buf))
			data = (counters,)
		elif type == QUERY.LINK:
			data = (self.read_u32(buf), self.read_u32(buf))
		elif type == QUERY.END:
			data = ()
		else: # Unknown flag
			raise RuntimeError(f"Unknown flag: {type}")
		# Check if we read all the data.
		expected = 2 + size
		data_read = buf.tell() - begin
		if data_read != expected:
			raise RuntimeError(f"Unexpected length read: type {type} expected {expected} read {data_read}")
		return type, data

	def read_queries(self, buf):
		d = {}
		while True:
			type, data = self.read_query(buf)
			if type is None:
				break
			if type == QUERY.END:
				break
			d[type] = data
		return d

	def read_location(self, data):
		controller = self.read_u8(data)
		location = LOCATION(self.read_u8(data))
		sequence = self.read_u32(data)
		position = POSITION(self.read_u32(data))
		return Location(controller, location, sequence, position)

	def set_responsei(self, r):
		buf = struct.pack('i', r)
		lib.OCG_DuelSetResponse(self.duel, buf, 4)
		self.cm.call_callbacks('debug', event_type='set_responsei', response=r)

	def set_responseb(self, r):
		lib.OCG_DuelSetResponse(self.duel, r, len(r))
		self.cm.call_callbacks('debug', event_type='set_responseb', response=r.decode('latin1'))

	@handle_error
	def get_cards_in_location(self, player, location):
		cards = []
		info = ffi.new('OCG_QueryInfo *')
		info.flags = (QUERY.CODE | QUERY.POSITION | QUERY.LEVEL | QUERY.RANK | QUERY.ATTACK | QUERY.DEFENSE | QUERY.EQUIP_CARD | QUERY.OVERLAY_CARD | QUERY.COUNTERS | QUERY.LSCALE | QUERY.RSCALE | QUERY.LINK).value
		info.con = player
		info.loc = location.value
		length = ffi.new('uint32_t *')
		data = lib.OCG_DuelQueryLocation(self.duel, length, info[0])
		buf = io.BytesIO(ffi.unpack(ffi.cast('char *', data), length[0]))
		size = self.read_u32(buf)
		begin = buf.tell()
		seq = -1
		while True:
			if buf.tell() == begin + size:
				break
			queries = self.read_queries(buf)
			seq += 1
			if not queries: # Nothing here
				continue
			code = queries[QUERY.CODE][0]
			card = Card(code)
			card.position = POSITION(queries[QUERY.POSITION][0])
			card.sequence = seq
			card.location = location
			card.controller = player
			level = queries[QUERY.LEVEL][0]
			if (level & 0xff) > 0:
				card.level = level & 0xff
			rank = queries[QUERY.RANK][0]
			if (rank & 0xff) > 0:
				card.level = rank & 0xff
			card.attack = queries[QUERY.ATTACK][0]
			card.defense = queries[QUERY.DEFENSE][0]

			card.equip_target = None

			ec, el, es, ep = queries[QUERY.EQUIP_CARD]
			if el > 0:
				card.equip_target = self.get_card(ec, el, es)

			card.xyz_materials = []

			for code in queries[QUERY.OVERLAY_CARD][0]:
				card.xyz_materials.append(Card(code))

			card.counters = []
			for c in queries[QUERY.COUNTERS][0]:
				card.counters.append(c)

			card.lscale = queries[QUERY.LSCALE][0]
			card.rscale = queries[QUERY.RSCALE][0]

			link = queries[QUERY.LINK][0]
			link_marker = queries[QUERY.LINK][1]

			if (link & 0xff) > 0:
				card.level = link & 0xff

			if link_marker > 0:
				card.defense = link_marker

			cards.append(card)
		return cards

	@handle_error
	def get_card(self, player, loc, seq):
		info = ffi.new('OCG_QueryInfo *')
		info.flags = (QUERY.CODE | QUERY.ATTACK | QUERY.DEFENSE | QUERY.POSITION | QUERY.LEVEL | QUERY.RANK | QUERY.LSCALE | QUERY.RSCALE | QUERY.LINK).value
		info.con = player
		info.loc = loc.value
		info.seq = seq
		length = ffi.new('uint32_t *')
		data = lib.OCG_DuelQuery(self.duel, length, info[0])
		if length[0] == 0:
			return
		buf = io.BytesIO(ffi.unpack(ffi.cast('char *', data), length[0]))
		queries = self.read_queries(buf)
		code = queries[QUERY.CODE][0]
		card = Card(code)
		card.position = queries[QUERY.POSITION][0]
		card.location = loc
		card.controller = player
		card.sequence = seq
		level = queries[QUERY.LEVEL][0]
		if (level & 0xff) > 0:
			card.level = level & 0xff
		rank = queries[QUERY.RANK][0]
		if (rank & 0xff) > 0:
			card.level = rank & 0xff
		card.attack = queries[QUERY.ATTACK][0]
		card.defense = queries[QUERY.DEFENSE][0]
		card.lscale = queries[QUERY.LSCALE][0]
		card.rscale = queries[QUERY.RSCALE][0]
		link, link_marker = queries[QUERY.LINK]
		if (link & 0xff) > 0:
			card.level = link & 0xff
		if link_marker > 0:
			card.defense = link_marker
		return card

	@handle_error
	def unpack_location(self, loc):
		controller = loc & 0xff
		location = LOCATION((loc >> 8) & 0xff)
		sequence = (loc >> 16) & 0xff
		position = POSITION((loc >> 24) & 0xff)
		return (controller, location, sequence, position)

	# all modules in ygo.message_handlers package will be imported here
	# if a module contains a MESSAGES dictionary attribute,
	# all of those entries will be considered message handlers
	# if a module contains a CALLBACKS dictionary attribute,
	# all of those entries will be considered callbacks for message handlers
	# all methods mentioned in those dictionaries will be linked into
	# the Duel object, same goes for all additional methods mentioned
	# in an additional METHODS dictionary attribute

	@handle_error
	def bind_message_handlers(self):

		all_handlers = {}

		all_callbacks = {}

		all_methods = {}

		for importer, modname, ispkg in pkgutil.iter_modules(message_handlers.__path__):
			if not ispkg:
				try:
					m = importer.find_module(modname).load_module(modname)
					# check if we got message handlers registered in there
					handlers = m.__dict__.get('MESSAGES')
					if type(handlers) is dict:
						all_handlers.update(handlers)

					# process callbacks defined in there
					callbacks = m.__dict__.get('CALLBACKS')
					if type(callbacks) is dict:
						all_callbacks.update(callbacks)

					# additional methods we shell link?
					meths = m.__dict__.get('METHODS')
					if type(meths) is dict:
						all_methods.update(meths)

				except Exception as e:
					print("Error loading message handler", modname)
					print(e)

		# link all those methods into this object
		for h in all_handlers.keys():
			m = all_handlers[h].__get__(self)
			setattr(self, all_handlers[h].__name__, m)
			self.message_map[h] = m
		for c in all_callbacks.keys():
			m = all_callbacks[c].__get__(self)
			setattr(self, all_callbacks[c].__name__, m)
			self.cm.register_callback(c, m)
		for n in all_methods.keys():
			setattr(self, n, all_methods[n].__get__(self))

	def show_usable(self, pl):
		summonable = natsort.natsorted([card.get_spec(pl) for card in self.summonable])
		spsummon = natsort.natsorted([card.get_spec(pl) for card in self.spsummon])
		repos = natsort.natsorted([card.get_spec(pl) for card in self.repos])
		mset = natsort.natsorted([card.get_spec(pl) for card in self.idle_mset])
		idle_set = natsort.natsorted([card.get_spec(pl) for card in self.idle_set])
		idle_activate = natsort.natsorted([card.get_spec(pl) for card in self.idle_activate])
		if summonable:
			pl.notify(pl._("Summonable in attack position: %s") % ", ".join(summonable))
		if mset:
			pl.notify(pl._("Summonable in defense position: %s") % ", ".join(mset))
		if spsummon:
			pl.notify(pl._("Special summonable: %s") % ", ".join(spsummon))
		if idle_activate:
			pl.notify(pl._("Activatable: %s") % ", ".join(idle_activate))
		if repos:
			pl.notify(pl._("Repositionable: %s") % ", ".join(repos))
		if idle_set:
			pl.notify(pl._("Settable: %s") % ", ".join(idle_set))

	def cardspec_to_ls(self, text):
		if text.startswith('o'):
			text = text[1:]
		r = re.search(r'^([a-z]+)(\d+)', text)
		if not r:
			return (None, None)
		if r.group(1) == 'h':
			l = LOCATION.HAND
		elif r.group(1) == 'm':
			l = LOCATION.MZONE
		elif r.group(1) == 's':
			l = LOCATION.SZONE
		elif r.group(1) == 'g':
			l = LOCATION.GRAVE
		elif r.group(1) == 'x':
			l = LOCATION.EXTRA
		elif r.group(1) == 'r':
			l = LOCATION.REMOVED
		else:
			return None, None
		return l, int(r.group(2)) - 1

	def flag_to_usable_cardspecs(self, flag, reverse=False):
		pm = flag & 0xff
		ps = (flag >> 8) & 0xff
		om = (flag >> 16) & 0xff
		os = (flag >> 24) & 0xff
		zone_names = ('m', 's', 'om', 'os')
		specs = []
		for zn, val in zip(zone_names, (pm, ps, om, os)):
			for i in range(8):
				if reverse:
					avail = val & (1 << i) != 0
				else:
					avail = val & (1 << i) == 0
				if avail:
					specs.append(zn + str(i + 1))
		return specs

	def cardlist_info_for_player(self, card, pl):
		spec = card.get_spec(pl)
		if card.location == LOCATION.DECK:
			spec = pl._("deck")
		cls = (card.controller, card.location, card.sequence)
		if card.controller != pl.duel_player and card.position & POSITION.FACEDOWN and cls not in self.revealed:
			position = card.get_position(pl)
			return (pl._("{position} card ({spec})")
				.format(position=position, spec=spec))
		name = card.get_name(pl)
		return "{name} ({spec})".format(name=name, spec=spec)

	def show_table(self, pl, player, hide_facedown=False):
		mz = self.get_cards_in_location(player, LOCATION.MZONE)
		sz = self.get_cards_in_location(player, LOCATION.SZONE)
		if len(mz+sz) == 0:
			pl.notify(pl._("Table is empty."))
			return
		for card in mz:
			s = "m%d: " % (card.sequence + 1)
			if hide_facedown and card.position & POSITION.FACEDOWN:
				s += card.get_position(pl)
			else:
				s += card.get_name(pl) + " "
				if card.type & TYPE.LINK:
					s += (pl._("({attack}) link rating {level}")
						.format(attack=card.attack, level=card.level))
				elif card.type & TYPE.XYZ:
					s += (pl._("({attack}/{defense}) rank {level}")
						.format(attack=card.attack, defense=card.defense, level=card.level))
				else:
					s += (pl._("({attack}/{defense}) level {level}")
						.format(attack=card.attack, defense=card.defense, level=card.level))
				s += " " + card.get_position(pl)

				if len(card.xyz_materials):
					s += " ("+pl._("xyz materials: %d")%(len(card.xyz_materials))+")"
				counters = []
				for c in card.counters:
					counter_type = c & 0xffff
					counter_val = (c >> 16) & 0xffff
					counter_type = pl.strings['counter'].get(counter_type) or ('Counter %d' % counter_type)
					counter_str = "%s: %d" % (counter_type, counter_val)
					counters.append(counter_str)
				if counters:
					s += " (" + ", ".join(counters) + ")"
			pl.notify(s)
		for card in sz:
			s = "s%d: " % (card.sequence + 1)
			if hide_facedown and card.position & POSITION.FACEDOWN:
				s += card.get_position(pl)
			else:
				s += card.get_name(pl) + " "
				s += card.get_position(pl)

				if card.type & TYPE.PENDULUM:
					s += " (" + pl._("Pendulum scale: %d/%d") % (card.lscale, card.rscale) + ")"

				if card.equip_target:
					s += ' ' + pl._('(equipped to %s)')%(card.equip_target.get_spec(pl))

				counters = []
				for c in card.counters:
					counter_type = c & 0xffff
					counter_val = (c >> 16) & 0xffff
					counter_type = pl.strings['counter'].get(counter_type) or ('Counter %d' % counter_type)
					counter_str = "%s: %d" % (counter_type, counter_val)
					counters.append(counter_str)
				if counters:
					s += " (" + ", ".join(counters) + ")"

			pl.notify(s)

		for card in mz:
			if card.type & TYPE.LINK:
				zone = self.get_linked_zone(card)
				if zone == '':
					continue
				pl.notify(pl._("Zone linked by %s (%s): %s")%(card.get_name(pl), card.get_spec(pl), zone))

	def show_cards_in_location(self, pl, player, location, hide_facedown=False):
		cards = self.get_cards_in_location(player, location)
		if not cards:
			pl.notify(pl._("No cards."))
			return
		for card in cards:
			s = card.get_spec(pl) + " "
			if hide_facedown and card.position & POSITION.FACEDOWN:
				s += card.get_position(pl)
			else:
				s += card.get_name(pl)
				if location != LOCATION.HAND:
					s += " " + card.get_position(pl)
				if card.type & TYPE.MONSTER:
					if card.type & TYPE.LINK:
						s += " " + pl._("link rating %d") % card.level
					elif card.type & TYPE.XYZ:
						s += " " + pl._("rank %d") % card.level
					else:
						s += " " + pl._("level %d") % card.level
			pl.notify(s)

	def show_score(self, pl):
		player = pl.duel_player
		deck = lib.OCG_DuelQueryCount(self.duel, player, LOCATION.DECK.value)
		odeck = lib.OCG_DuelQueryCount(self.duel, 1 - player, LOCATION.DECK.value)
		grave = lib.OCG_DuelQueryCount(self.duel, player, LOCATION.GRAVE.value)
		ograve = lib.OCG_DuelQueryCount(self.duel, 1 - player, LOCATION.GRAVE.value)
		hand = lib.OCG_DuelQueryCount(self.duel, player, LOCATION.HAND.value)
		ohand = lib.OCG_DuelQueryCount(self.duel, 1 - player, LOCATION.HAND.value)
		removed = lib.OCG_DuelQueryCount(self.duel, player, LOCATION.REMOVED.value)
		oremoved = lib.OCG_DuelQueryCount(self.duel, 1 - player, LOCATION.REMOVED.value)
		if pl.watching:
			if self.tag is True:
				nick0 = pl._("team %s")%(self.players[player].nickname+", "+self.tag_players[player].nickname)
				nick1 = pl._("team %s")%(self.players[1 - player].nickname+", "+self.tag_players[1 - player].nickname)
			else:
				nick0 = self.players[player].nickname
				nick1 = self.players[1 - player].nickname
			pl.notify(pl._("LP: %s: %d %s: %d") % (nick0, self.lp[player], nick1, self.lp[1 - player]))
			pl.notify(pl._("Hand: %s: %d %s: %d") % (nick0, hand, nick1, ohand))
			pl.notify(pl._("Deck: %s: %d %s: %d") % (nick0, deck, nick1, odeck))
			pl.notify(pl._("Grave: %s: %d %s: %d") % (nick0, grave, nick1, ograve))
			pl.notify(pl._("Removed: %s: %d %s: %d") % (nick0, removed, nick1, oremoved))
		else:
			pl.notify(pl._("Your LP: %d Opponent LP: %d") % (self.lp[player], self.lp[1 - player]))
			pl.notify(pl._("Hand: You: %d Opponent: %d") % (hand, ohand))
			pl.notify(pl._("Deck: You: %d Opponent: %d") % (deck, odeck))
			pl.notify(pl._("Grave: You: %d Opponent: %d") % (grave, ograve))
			pl.notify(pl._("Removed: You: %d Opponent: %d") % (removed, oremoved))
		if self.paused:
			pl.notify(pl._("This duel is currently paused."))
		else:
			if not pl.watching and pl.duel_player == self.tp and pl in self.players:
				pl.notify(pl._("It's your turn."))
			else:
				pl.notify(pl._("It's %s's turn.")%(self.players[self.tp].nickname))

	def show_info(self, card, pl):
		pln = pl.duel_player
		cs = card.get_spec(pl)
		opponent = 1 - pln
		should_reveal = False
		if pl.watching:
			if cs.startswith('o') and self.revealing[opponent]:
				should_reveal = True
			elif not cs.startswith('o') and self.revealing[pln]:
				should_reveal = True
		if card.position & POSITION.FACEDOWN and ((pl.watching and not should_reveal) or (not pl.watching and card.controller == opponent)):
			pl.notify(pl._("%s: %s card.") % (cs, card.get_position(pl)))
			return
		pl.notify(card.get_info(pl))

	def show_info_cmd(self, pl, spec):
		cards = []
		for i in (0, 1):
			for j in (LOCATION.MZONE, LOCATION.SZONE, LOCATION.GRAVE, LOCATION.REMOVED, LOCATION.HAND, LOCATION.EXTRA):
				cards.extend(card for card in self.get_cards_in_location(i, j))
		specs = {}
		for card in cards:
			specs[card.get_spec(pl)] = card
		for i, card in enumerate(pl.card_list):
			specs[str(i + 1)] = card
		if spec not in specs:
			pl.notify(pl._("Invalid card."))
			return
		self.show_info(specs[spec], pl)

	def start_debug(self, options):
		self.debug_mode = True
		lt = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
		if self.tag is True:
			pl0 = self.players[0].nickname+","+self.tag_players[0].nickname
			pl1 = self.players[1].nickname+","+self.tag_players[1].nickname
		else:
			pl0 = self.players[0].nickname
			pl1 = self.players[1].nickname
		fn = lt+"_"+pl0+"_"+pl1
		self.debug_fp = open(os.path.join('duels', fn), 'w')
		if self.tag is True:
			players = [self.players[0].nickname, self.tag_players[0].nickname, self.players[1].nickname, self.tag_players[1].nickname]
			decks = [self.cards[0], self.tag_cards[0], self.cards[1], self.tag_cards[1]]
		else:
			players = [self.players[0].nickname, self.players[1].nickname]
			decks = [self.cards[0], self.cards[1]]
		self.debug(event_type='start', players=players, decks=decks, seed=self.seed, options = options, lp = self.lp)

	def player_disconnected(self, player):
		if not self.paused:
			self.pause()

	def player_reconnected(self, pl):
		pl.set_parser('DuelParser')
		if not self.paused:
			self.unpause()
			if self.pause_timer:
				self.pause_timer.cancel()
				self.pause_timer = None

	def pause(self):
		for pl in self.players + self.watchers:
			pl.notify(pl._("Duel paused until all duelists reconnect."))
		for pl in self.players+self.tag_players:
			if pl.connection is not None:
				pl.paused_parser = pl.connection.parser
				pl.set_parser('DuelParser')
		if not self.pause_timer:
			self.pause_timer = reactor.callLater(600, self.end, True)

	def unpause(self):
		for pl in self.players+self.tag_players:
			pl.connection.parser = pl.paused_parser
			pl.paused_parser = None
		for pl in self.players+self.watchers:
			pl.notify(pl._("Duel continues."))

	def remove_watcher(self, pl):
		try:
			self.watchers.remove(pl)
			if pl in self.room.teams[0]:
				self.room.teams[0].remove(pl)
			self.watch.remove_recipient(pl)
			self.watch.send_message(pl, __("{player} is no longer watching this duel."))
			pl.duel = None
			pl.watching = False
			self.say.remove_recipient(pl)
			pl.notify(pl._("Watching stopped."))
			pl.set_parser('LobbyParser')
		except ValueError:
			pass

	def add_watcher(self, pl, player = 0):
		pl.duel = self
		pl.duel_player = player
		pl.watching = True
		self.say.add_recipient(pl)
		if self.tag is True:
			pl0 = pl._("team %s")%(self.players[player].nickname+", "+self.tag_players[player].nickname)
			pl1 = pl._("team %s")%(self.players[1 - player].nickname+", "+self.tag_players[1 - player].nickname)
		else:
			pl0 = self.players[player].nickname
			pl1 = self.players[1 - player].nickname
		pl.notify(pl._("Watching duel between %s and %s.")%(pl0, pl1))
		if not pl in self.room.teams[0]:
			self.room.teams[0].append(pl)
		self.watchers.append(pl)
		self.watch.send_message(pl, __("{player} is now watching this duel."))
		self.watch.add_recipient(pl)
		pl.set_parser('DuelParser')
		if self.paused:
			pl.notify(pl._("The duel is currently paused due to not all players being connected."))

	@handle_error
	def inform(self, ref_player, *inf):
		"""
		informs specific players in a duel
		players can be configured with constants from INFORM enum in constants
		each message consists of a callable which takes the player and returns the properly formatted text
		if no callable is received, the message is skipped
		a player cannot be informed twice through this method.
		
		example:
		duel.inform(pl, (INFORM.ALL_PLAYERS, lambda p: p._("you were informed")))
		"""

		if not ref_player or ref_player not in self.players:
			raise ValueError("reference player must be duelling in this duel")
			
		players = self.players[:]
		tag_players = self.tag_players[:]
		watchers = list(filter(lambda p: p not in tag_players, self.watchers))
		all = players + tag_players + watchers

		informed = {}

		for t in inf:
			key = t[0]
			value = t[1]
			if not isinstance(key, INFORM):
				raise TypeError("inform key must be of type INFORM")

			if not callable(value):
				continue
			
			to_be_informed = list(filter(lambda p: \
				p not in informed and (\
					(key & INFORM.PLAYER and p is ref_player) or \
					(key & INFORM.OPPONENT and p is not ref_player and p in players) or \
					(key & INFORM.TAG_PLAYER and p.duel_player == ref_player.duel_player and p in tag_players) or \
					(key & INFORM.TAG_OPPONENT and p.duel_player != ref_player.duel_player and p in tag_players) or \
					(key & INFORM.WATCHERS_PLAYER and p.duel_player == ref_player.duel_player and p in watchers) or \
					(key & INFORM.WATCHERS_OPPONENT and p.duel_player != ref_player.duel_player and p in watchers)\
				), all))

			for p in to_be_informed:
				informed[p] = value

		for pl, cl in informed.items():
			pl.notify(cl(pl))

	def get_linked_zone(self, card):

		lst = []

		zone = lib.query_linked_zone(self.duel, card.controller, card.location.value, card.sequence)

		i = 0

		for i in range(8):
			if zone & (1<<i):
				lst.append('m'+str(i+1))

		for i in range(16, 24, 1):
			if zone & (1<<i):
				lst.append('om'+str(i-15))

		return ', '.join(lst)

	@property
	def paused(self):
		return len(self.players) != len([p for p in self.players if p.connection is not None])

	@property
	def tag(self):
		return len(self.tag_players) > 0
