from .card import Card

class Banlist:
	def __init__(self, name):
		self.__cards = {}
		self.__name = name.lower()

	def add(self, card, amount):
		self.__cards[card] = amount

	def check(self, cards):

		codes = set(cards)

		errors = []
	 
		for card in (Card(c) for c in codes):
			limit = self.limit(card)
			count = cards.count(card.code)

			if limit is None or count <= limit:
				continue

			errors += [(card, limit, count)]

		return errors

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
