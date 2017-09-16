import sys
import json
import duel as dm

def main():
	global lr
	lr=0
	fp = open(sys.argv[1])
	for i, line in enumerate(fp):
		print("line %d" % (i+1))
		j = json.loads(line)
		if 'data' in j:
			j['data'] = j['data'].encode('latin1')
		if j['event_type'] == 'start':
			duel = dm.Duel(j.get('seed', 0))
			duel.load_deck(0, j['deck0'], shuffle=False)
			duel.load_deck(1, j['deck1'], shuffle=False)
			duel.cm.register_callback('*', debug)
			duel.start()
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
	print("here")
	c = duel.get_cards_in_location(0, 4)[0]
	import code;code.interact(local=dict(globals(), **locals()))

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
