from .card import Card
from . import globals

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

	@property
	def name(self):
		return self.__name

	def limit(self, card):
		if card.code in self.__cards:
			return self.__cards[card.code]
		if card.alias == 0:
			return None
		while card.alias != 0:
			if card.alias in self.__cards:
				return self.__cards[card.alias]
			card = Card(card.alias)
		return None
