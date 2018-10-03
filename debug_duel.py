import sys
import json
import sqlite3
from ygo import duel as dm
from ygo import globals as glb
from ygo import server
from ygo.language_handler import LanguageHandler

class FakePlayer:
	def __init__(self, i, deck):
		self.deck = {'cards': deck}
		self.duel_player = i
		self.cdb = glb.server.db
		self.language = 'english'
		self.watching = False
		self.seen_waiting = False
		self.soundpack = False
		

	def notify(self, text, *args, **kwargs):
		print(self.duel_player, text)

	_ = lambda self, t: t

	@property
	def strings(self):
		return glb.language_handler.get_strings(self.language)

def main():
	global lr
	lr=0
	glb.language_handler = LanguageHandler()
	glb.language_handler.add('english', 'en')
	glb.language_handler.set_primary_language('english')
	fp = open(sys.argv[1])
	glb.server = server.Server()
	glb.server.db = sqlite3.connect('locale/en/cards.cdb')
	glb.server.db.row_factory = sqlite3.Row
	for i, line in enumerate(fp):
		print("line %d" % (i+1))
		if i + 1 == 227:
			import code;code.interact(local=dict(globals(), **locals()))
		j = json.loads(line)
		if 'data' in j:
			j['data'] = j['data'].encode('latin1')
		if j['event_type'] == 'start':
			duel = dm.Duel(j.get('seed', 0))
			players = [FakePlayer(i, deck) for i, deck in enumerate(j['decks'])]
			for i, name in enumerate(j['players']):
				players[i].nickname = name
				duel.load_deck(players[i], shuffle=False)
			duel.players = players
			duel.cm.register_callback('*', debug)
			duel.start(0x40000)
		elif j['event_type'] == 'set_responsei':
			duel.set_responsei(j['response'])
			print("Responded %d" % j['response'])
		elif j['event_type'] == 'set_responseb':
			duel.set_responseb(j['response'].encode('latin1'))
			print('Responded %r' % j['response'].encode('latin1'))
		elif j['event_type'] == 'process':
			np = get_next_packet(duel)
			if np != j['data']:
				print("np data mismatch.")
				return

def get_next_packet(duel):
	res = dm.lib.process(duel.duel)
	l = dm.lib.get_message(duel.duel, dm.ffi.cast('byte *', duel.buf))
	data = dm.ffi.unpack(duel.buf, l)
	duel.process_messages(data)
	return data

def debug(type, *args, **kwargs):
#	if type == 'idle':
#		import code;code.interact(local=dict(globals(), **locals()))
	if type == 'debug':
		if kwargs['event_type'] == 'process':
			print('%x %r' % (kwargs['result'], kwargs['data'].encode('latin1')))
		return
	if type == 'draw':
		args = list(args)
		args[1] = [c.name for c in args[1]]
	print(type, args, kwargs)

if __name__ == '__main__':
	main()
