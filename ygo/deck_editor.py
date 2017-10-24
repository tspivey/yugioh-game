from collections import OrderedDict
import json

from .card import Card
from . import globals
from . import models
from .constants import *
from .parsers.deck_editor_parser import DeckEditorParser

class DeckEditor:
	def __init__(self, player):
		self.deck_edit_pos = 0
		self.deck_name = ''
		self.last_search = ""
		self.player = player

	def list(self):
		decks = self.player.connection.account.decks
		if not decks:
			self.player.notify(self.player._("No decks."))
			self.player.connection.session.commit()
			return
		self.player.notify(self.player._("You own %d decks:")%(len(decks)))
		for deck in decks:
			self.player.notify(deck.name)
		self.player.connection.session.commit()

	def clear(self, name):
		account = self.player.connection.account
		session = self.player.connection.session
		deck = models.Deck.find(session, account, name)
		if not deck:
			self.player.notify(self.player._("Deck not found."))
			session.commit()
			return
		deck.content = json.dumps({'cards': []})
		session.commit()
		self.player.notify(self.player._("Deck cleared."))

	def delete(self, name):
		account = self.player.connection.account
		session = self.player.connection.session
		deck = models.Deck.find(session, account, name)
		if not deck:
			self.player.notify(self.player._("Deck not found."))
			session.commit()
			return
		session.delete(deck)
		session.commit()
		self.player.notify(self.player._("Deck deleted."))

	def rename(self, args):
		if '=' not in args:
			self.player.notify(self.player._("Usage: deck rename <old>=<new>"))
			return
		args = args.strip().split('=', 1)
		name = args[0].strip()
		dest = args[1].strip()
		if not name or not dest:
			self.player.notify(self.player._("Usage: deck rename <old>=<new>"))
			return
		if '=' in dest:
			self.player.notify(self.player._("Deck names may not contain =."))
			return
		account = self.player.connection.account
		session = self.player.connection.session
		deck = models.Deck.find(session, account, name)
		if not deck:
			self.player.notify(self.player._("Deck not found."))
			session.commit()
			return
		dest_deck = models.Deck.find(session, account, dest)
		if dest_deck:
			self.player.notify(self.player._("Destination deck already exists"))
			session.commit()
			return
		deck.name = dest
		session.commit()
		self.player.notify(self.player._("Deck renamed."))

	def edit(self, deck_name):
		con = self.player.connection
		con.player.paused_parser = con.parser
		con.parser = DeckEditorParser
		account = con.account
		deck = con.session.query(models.Deck).filter_by(account_id=con.account.id, name=deck_name).first()
		if deck:
			con.notify(con._("Deck exists, loading."))
			con.player.deck = json.loads(deck.content)
			invalid_cards = con.player.get_invalid_cards_in_deck()
			con.player.deck['cards'] = [c for c in con.player.deck['cards'] if c not in invalid_cards]
			if len(invalid_cards):
				con.notify(con._("Invalid cards were removed from this deck. This usually occurs after the server loading a new database which doesn't know those cards anymore."))
		else:
			con.notify(con._("Creating new deck %s.") % deck_name)
		self.deck_name = deck_name
		con.parser.prompt(con)
	
	@staticmethod
	def group_cards(cardlist):
		"""
		Groups all cards in the supplied list.

		This provides output like foo, bar(x3) etc.
		"""
		cnt = OrderedDict()
		for code in cardlist:
			if not code in cnt:
				cnt[code] = 1
			else:
				cnt[code] += 1
		return cnt

	def group_sort_cards(self, cardlist):
		"""
		Use the above function to group all cards, then sort them into groups.
		"""
		extras = [c for c in cardlist if (Card(c).type & (TYPE_XYZ | TYPE_SYNCHRO | TYPE_FUSION | TYPE_LINK))]
		for c in extras: cardlist.remove(c)
		traps = [c for c in cardlist if (Card(c).type & 4)]
		for c in traps: cardlist.remove(c)
		monsters = [c for c in cardlist if (Card(c).type&1)]
		for c in monsters: cardlist.remove(c)
		spells = [c for c in cardlist if (Card(c).type & 2)]
		for c in spells: cardlist.remove(c)
		other=cardlist
		extras_group = self.group_cards(extras)
		traps_group = self.group_cards(traps)
		spells_group = self.group_cards(spells)
		monsters_group = self.group_cards(monsters)
		other_group = self.group_cards(other)
		groups=(monsters_group, spells_group, traps_group, extras_group, other_group)
		return groups

	def group_cards_combined(self, cardlist):
		"""
		Groups and sorts cards, then combines them in the correct order for proper indexing.
		"""
		groups = self.group_sort_cards(cardlist)
		monsters, spells, traps, extras, other = groups
		full = OrderedDict()
		for x,y in monsters.items(): full[x] = y
		for x,y in spells.items(): full[x] = y
		for x,y in traps.items(): full[x] = y
		for x,y in extras.items(): full[x] = y
		for x, y in other.items(): full[x] = y
		return full

	def find_next(self, text, start, limit=None, wrapped=False):
		sql = 'SELECT id FROM texts WHERE UPPER(name) LIKE ? and id in (%s) ORDER BY id ASC LIMIT 1'
		if limit:
			cards = globals.server.all_cards[start:start+limit]
		else:
			cards = globals.server.all_cards[start:]
		row = self.player.cdb.execute(sql % (', '.join([str(c) for c in cards])), ('%'+text.upper()+'%', )).fetchone()
		if row is not None:
			return globals.server.all_cards.index(row[0])
		if wrapped:
			return
		return self.find_next(text, 0, start, wrapped=True)

	def find_prev(self, text, start, end=None, wrapped=False):
		sql = 'SELECT id FROM texts WHERE UPPER(name) LIKE ? AND id IN (%s) ORDER BY id DESC LIMIT 1'
		pos = start
		if end is None:
			end = 0
		cards = globals.server.all_cards[end:start]
		row = self.player.cdb.execute(sql % (', '.join([str(c) for c in cards])), ('%'+text.upper()+'%', )).fetchone()
		if row is not None:
			return globals.server.all_cards.index(row[0])
		if wrapped:
			return
		return self.find_prev(text, len(globals.server.all_cards) - 1, start, wrapped=True)

	def save(self, deck, session, account, name):
		deck = json.dumps(deck)
		existing_deck = session.query(models.Deck).filter_by(account_id=account.id, name=name).first()
		if existing_deck:
			new_deck = existing_deck
		else:
			new_deck = models.Deck(account_id=account.id, name=name)
			session.add(new_deck)
		new_deck.content = deck

	def new(self, name):
		account = self.player.connection.account
		session = self.player.connection.session
		deck = models.Deck.find(session, account, name)
		if deck:
			self.player.notify(self.player._("That deck already exists."))
			session.commit()
			return
		deck = models.Deck(account_id=account.id, name=name)
		session.add(deck)
		deck.content = json.dumps({'cards': []})
		session.commit()
		self.player.notify(self.player._("Deck created."))

	def check(self, deck, banlist = None):
		con = self.player.connection
		if not banlist:
			for k in globals.lflist.keys():
				self.player.notify(k)
			return
		if banlist not in globals.lflist:
			self.player.notify(self.player._("Invalid entry."))
			return
		codes = set(deck)
		errors = 0
		for code in codes:
			count = deck.count(code)
			if code not in globals.lflist[banlist] or count <= globals.lflist[banlist][code]:
				continue
			card = Card(code)
			self.player.notify(self.player._("%s: limit %d, found %d.") % (card.get_name(self.player), globals.lflist[banlist][code], count))
			errors += 1
		self.player.notify(self.player._("Check completed with %d errors.") % errors)
