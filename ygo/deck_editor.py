from collections import OrderedDict
from gsb.intercept import Reader
import json
import re

from .card import Card
from . import globals
from . import models

class DeckEditor:
	def __init__(self, player):
		self.deck_edit_pos = 0
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
		parser = con.parser
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
		cards = con.player.deck['cards']
		def group_cards(cards):
			cnt = OrderedDict()
			for i, code in enumerate(cards):
				if not code in cnt:
					cnt[code] = 1
				else:
					cnt[code] += 1
			return cnt
		def info():
			self.show_deck_info()
			con.notify(con._("u: up d: down /: search forward ?: search backward t: top"))
			con.notify(con._("s: send to deck r: remove from deck l: list deck g: go to card in deck q: quit"))
			con.notify(con._("c: check deck against banlist"))
		def read():
			info()
			main, extra = self.player.count_deck_cards(cards)
			con.notify(Reader, r, prompt=con._("Command (%d cards in main deck, %d cards in extra deck):") % (main, extra), no_abort="Invalid command", restore_parser=parser)
		def r(caller):
			code = globals.server.all_cards[self.deck_edit_pos]
			if caller.text == 'd':
				self.deck_edit_pos+= 1
				if self.deck_edit_pos > len(globals.server.all_cards) - 1:
					self.deck_edit_pos = len(globals.server.all_cards) - 1
					con.notify(con._("bottom of list."))
				read()
			elif caller.text == 'u':
				if self.deck_edit_pos == 0:
					con.notify(con._("Top of list."))
					read()
					return
				self.deck_edit_pos -= 1
				read()
			elif caller.text == 't':
				con.notify(con._("Top."))
				self.deck_edit_pos = 0
				read()
			elif caller.text == 's':
				if cards.count(code) == 3:
					con.notify(con._("You already have 3 of this card in your deck."))
					read()
					return
				cards.append(code)
				self.save(con.player.deck, con.session, con.account, deck_name)
				con.session.commit()
				read()
			elif caller.text.startswith('r'):
				cnt = group_cards(cards)
				rm = re.search(r'^r(\d+)', caller.text)
				if rm:
					n = int(rm.group(1)) - 1
					if n < 0 or n > len(cnt) - 1:
						con.notify(con._("Invalid card."))
						read()
						return
					code = list(cnt.keys())[n]
				if cards.count(code) == 0:
					con.notify(con._("This card isn't in your deck."))
					read()
					return
				cards.remove(code)
				self.save(con.player.deck, con.session, con.account, deck_name)
				con.session.commit()
				read()
			elif caller.text.startswith('/'):
				text = caller.text[1:] or self.last_search
				self.last_search = text
				search_pos = self.deck_edit_pos + 1
				if search_pos >= len(globals.server.all_cards):
					search_pos = 0
				pos = self.find_next(text, search_pos)
				if not pos:
					con.notify(con._("Not found."))
				else:
					self.deck_edit_pos = pos
				read()
			elif caller.text.startswith('?'):
				text = caller.text[1:] or self.last_search
				self.last_search = text
				search_start = self.deck_edit_pos - 1
				if search_start < 0:
					search_start = len(globals.server.all_cards) - 1
				pos = self.find_prev(text, search_start)
				if not pos:
					con.notify(con._("Not found."))
				else:
					self.deck_edit_pos = pos
				read()
			elif caller.text == 'l':
				i=0
				cnt = group_cards(cards)
				for code, count in cnt.items():
					i+=1
					card = Card(code)
					if count == 1:
						con.notify("%d: %s" % (i, card.get_name(con.player)))
					else:
						con.notify("%d: %s (x %d)" % (i, card.get_name(con.player), count))
				read()
			elif caller.text.startswith('g'):
				cnt = group_cards(cards)
				gm = re.search(r'^g(\d+)', caller.text)
				if gm:
					n = int(gm.group(1)) - 1
					if n < 0 or n > len(cnt) - 1:
						con.notify(con._("Invalid card."))
						read()
						return
					code = list(cnt.keys())[n]
					self.deck_edit_pos=globals.server.all_cards.index(code)
					read()
			elif caller.text == 'q':
				con.notify(con._("Quit."))
			elif caller.text.startswith('c'):
				cm = re.search(r'c ?([a-zA-Z0-9\.\- ]+)', caller.text)
				if cm:
					self.check(cards, cm.group(1).lower())
				else:
					self.check(None)
				read()
			else:
				con.notify(con._("Invalid command."))
				read()
		read()

	def show_deck_info(self):
		cards = self.player.deck['cards']
		pos = self.deck_edit_pos
		code = globals.server.all_cards[pos]
		in_deck = cards.count(code)
		if in_deck > 0:
			self.player.notify(self.player._("%d in deck.") % in_deck)
		card = Card(code)
		self.player.notify(card.get_info(self.player))

	def find_next(self, text, start, limit=None, wrapped=False):
		if limit:
			cards = globals.server.all_cards[start:start+limit]
		else:
			cards = globals.server.all_cards[start:]
		for i, code in enumerate(cards):
			card = Card(code)
			if text.lower() in card.get_name(self.player).lower():
				return start + i
		if wrapped:
			return
		return self.find_next(text, 0, start, wrapped=True)

	def find_prev(self, text, start, end=None, wrapped=False):
		text = text.lower()
		pos = start
		if end is None:
			end = 0
		while pos >= end:
			card = Card(globals.server.all_cards[pos])
			name = card.get_name(self.player).lower()
			if text in name:
				return pos
			pos -= 1
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
