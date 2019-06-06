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
	 
		for card in codes:
			count = cards.count(card)

			if card not in self.__cards or count <= self.__cards[card]:
				continue

			errors += [(card, self.__cards[card], count)]

		return errors

	def check_and_resolve(self, cards):

		orig = self.check(cards)
		
		return [(Card(t[0]), t[1], t[2]) for t in orig]

	@property
	def name(self):
		return self.__name
