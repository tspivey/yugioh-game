import collections
import natsort
import os.path
import sys
import traceback

from .banlist import Banlist
from . import globals

try:
	from _duel import ffi, lib
	DUEL_AVAILABLE = True
except ImportError:
	DUEL_AVAILABLE = False

PROCESSOR_FLAG = 0xf0000000
PROCESSOR_END = 0x20000000

def parse_lflist(filename):

	lst = {}

	with open(filename, 'r', encoding='utf-8') as fp:
		for line in fp:
			line = line.rstrip('\n')
			if not line or line.startswith('#'):
				continue
			elif line.startswith('!'):
				section = line[1:].lower()
				lst[section] = Banlist(section)
			else:
				code, num_allowed, *extra = line.split(' ', 2)
				code = int(code)
				num_allowed = int(num_allowed)
				lst[section].add(code, num_allowed)

	return collections.OrderedDict(natsort.natsorted(lst.items(), reverse=True))

def process_duel(d):
	while d.started:
		res = d.process()
		if res == 0:
			break
		elif res == 1:
			if d.keep_processing:
				d.keep_processing = False
				continue
			break

def process_duel_replay(duel):
	res = lib.process(duel.duel)
	l = lib.get_message(duel.duel, ffi.cast('byte *', duel.buf))
	data = ffi.unpack(duel.buf, l)
	cb = duel.cm.callbacks
	duel.cm.callbacks = collections.defaultdict(list)
	def tp(t):
		duel.tp = t
	duel.cm.register_callback('new_turn', tp)
	def recover(player, amount):
		duel.lp[player] += amount
	def damage(player, amount):
		duel.lp[player] -= amount
	def tag_swap(player):
		c = duel.players[player]
		n = duel.tag_players[player]
		duel.players[player] = n
		duel.watchers[player] = c
		duel.tag_players[player] = c
	duel.cm.register_callback('recover', recover)
	duel.cm.register_callback('damage', damage)
	duel.cm.register_callback('tag_swap', tag_swap)
	duel.process_messages(data)
	duel.cm.callbacks = cb
	return data

def check_sum(cards, acc):
	if acc < 0:
		return False
	if not cards:
		return acc == 0
	l1 = cards[0].param[0]
	l2 = cards[0].param[1]
	nc = cards[1:]
	res1 = check_sum(nc, acc - l1)
	if l2 > 0:
		res2 = check_sum(nc, acc - l2)
	else:
		res2 = False
	return res1 or res2

def parse_ints(text):
	ints = []
	try:
		for i in text.split():
			ints.append(int(i))
	except ValueError:
		pass
	return ints

def get_root_directory():
	return os.path.dirname(os.path.abspath(sys.argv[0]))

def forward_error():
	
	players = globals.server.get_all_players()
	
	players = [p for p in players if p.is_admin]

	exc = traceback.format_exc()

	for pl in players:
	
		pl.notify(pl._("A critical error was encountered."))
		pl.notify(exc)

def handle_error(f):
	def catch(*args, **kwargs):
		try:
			return f(*args, **kwargs)
		except Exception as e:
			forward_error()
			raise e
	return catch