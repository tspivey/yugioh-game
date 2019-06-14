from .card import Card
from . import globals

import natsort

class Banlist:
	def __init__(self, name):
		self.__cards = {}
		self.__name = name.lower()

	def add(self, card, amount):
		self.__cards[card] = amount

	def check(self, cards):

		db = globals.language_handler.primary_database

		codes = set(cards)

		# this will filter all unknown cards
		res = db.execute('SELECT id, alias FROM datas WHERE id IN ({0})'.format(', '.join([str(c) for c in codes]))).fetchall()

		codes = [] # a list of lists, each list containing all cards with the same name, but aliases referencing each other
		indices = {} # knows the list indices to each card id
		i = 0

		# pre-processing

		for c in res:
			codes.append([c[0]])
			indices[c[0]] = i
			i += 1
			
		# anti-aliasing
		while True:
		
			# we only want cards with aliases
			aliased = [r for r in res if r[1] != 0]

			# no aliases remaining: we were successful
			if len(aliased) == 0:
				break

			# adding indices for later
			for r in aliased:
				indices[r[1]] = indices[r[0]]

			# select all aliased cards
			res = db.execute('SELECT id, alias FROM datas WHERE id IN ({0})'.format(', '.join([str(r[1]) for r in aliased]))).fetchall()

			# append all aliased cards to the codes lists
			for r in res:
				codes[indices[r[0]]].append(r[0])

		# compressing list
		i = 0

		while i < len(codes):

			j = i + 1

			while j < len(codes):
				if codes[j][0] in codes[i]:
					del codes[j]
					continue
				elif codes[i][0] in codes[j]:
					del codes[i]
					continue

				j += 1
			
			i += 1

		errors = []
		for i in range(len(codes)):

			l = codes[i]

			for j in range(len(l) - 1, -1, -1):

				limit = self.__cards.get(l[j], None)
					
				if limit is not None:
					break

			if limit is None:
				continue # card not in banlist

			# takes care that all different versions of a single card count for the total
			# not just the version on the banlist
			count = sum([cards.count(fc) for fc in l])

			if count <= limit:
				continue # banlist-compatible

			errors += [(l[j], limit, count)]

		return errors

	def check_and_resolve(self, cards):
		return [(Card(e[0]), e[1], e[2], ) for e in self.check(cards)]

	def __list_cards(self, cards, pl):

		# getting all data
		data = pl.cdb.execute('SELECT id, name FROM texts WHERE id IN ({0})'.format(', '.join([str(c) for c in cards]))).fetchall()

		if len(data) < len(cards):
			# not all cards are available in the player's language
			# fill up with english ones
			already_present = set([d[0] for d in data])

			remaining = cards - already_present

			data_r = globals.language_handler.primary_database.execute('SELECT id, name FROM texts WHERE id IN ({0})'.format(', '.join([str(c) for c in remaining]))).fetchall()

			data = data + data_r

		for d in natsort.natsorted(data, key = lambda d: d[1]):

			pl.notify("\t" + d[1])

	def show(self, pl):

		all = set(self.__cards.keys())
		
		forbidden = set([c for c  in self.__cards.keys() if self.__cards[c] == 0])

		limited = set([c for c in self.__cards.keys() if self.__cards[c] == 1])

		semi_limited = all - forbidden - limited

		pl.notify(pl._("Forbidden cards (not allowed at all):"))
		
		self.__list_cards(forbidden, pl)
		
		pl.notify(pl._("Limited cards (only allowed once):"))
		
		self.__list_cards(limited, pl)
		
		pl.notify(pl._("Semi-limited cards (only allowed twice):"))
		
		self.__list_cards(semi_limited, pl)

	@property
	def name(self):
		return self.__name
