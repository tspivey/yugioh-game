import os
import re
import random
from functools import partial
import json
import datetime
import collections
import struct
import argparse
import gsb
from gsb.intercept import Menu, Reader, YesOrNo
from twisted.internet import reactor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import duel as dm
import strings
from parsers import parser, duel_parser, LoginParser
import models
import game

all_cards = [int(row[0]) for row in dm.db.execute("select id from datas")]

engine = create_engine('sqlite:///game.db')
models.Base.metadata.bind = engine
Session = sessionmaker(bind=engine)
models.Base.metadata.create_all()

class MyServer(gsb.Server):
	def on_connect(self, caller):
		caller.connection.deck = {'cards': []}
		caller.connection.deck_edit_pos = 0
		caller.connection.duel = None
		caller.connection.requested_opponent = None
		caller.connection.nickname = None
		caller.connection.seen_waiting = False
		caller.connection.chat = True
		caller.connection.session = Session()

	def on_disconnect(self, caller):
		con = caller.connection
		if not con.nickname:
			return
		del game.players[con.nickname.lower()]
		for pl in game.players.values():
			pl.notify("%s logged out." % con.nickname)
		if con.duel:
			con.duel.notify_all("Your opponent disconnected, the duel is over.")
			con.duel.end()
		con.nickname = None

server = MyServer(port=4000, default_parser=LoginParser())
game.server = server

@parser.command(names=['duel'], args_regexp=r'(.*)')
def duel(caller):
	con = caller.connection
	nick = caller.args[0]
	player = get_player(nick)
	if con.duel:
		con.notify("You are already in a duel.")
		return
	elif not player:
		con.notify("That player is not online.")
		return
	elif player.duel:
		con.notify("That player is already in a duel.")
		return
	elif player is con:
		con.notify("You can't duel yourself.")
		return
	elif not con.deck['cards']:
		con.notify("You can't duel without a deck. Try deck load starter.")
		return
	if player.requested_opponent == con.nickname:
		player.notify("Duel request accepted, dueling with %s." % con.nickname)
		start_duel(con, player)
		player.requested_opponent = None
	else:
		player.notify("%s wants to duel. Type duel %s to accept." % (con.nickname, con.nickname))
		con.requested_opponent = player.nickname
		con.notify("Duel request sent to %s." % player.nickname)

def start_duel(*players):
	players = list(players)
	random.shuffle(players)
	duel = MyDuel()
	duel.load_deck(0, players[0].deck['cards'])
	duel.load_deck(1, players[1].deck['cards'])
	for i, pl in enumerate(players):
		pl.notify("Duel created. You are player %d." % i)
		pl.duel = duel
		pl.duel_player = i
		pl.parser = duel_parser
	duel.players = players
	if os.environ.get('DEBUG', 0):
		duel.start_debug()
	duel.start()
	reactor.callLater(0, procduel, duel)

def procduel(d):
	while d.started:
		res = d.process()
		if res & 0x20000:
			break
		elif res & 0x10000 and res != 0x10000:
			if d.keep_processing:
				d.keep_processing = False
				continue
			break

class MyDuel(dm.Duel):
	def __init__(self):
		super(MyDuel, self).__init__()
		self.keep_processing = False
		self.to_ep = False
		self.to_m2 = False
		self.current_phase = 0
		self.cm.register_callback('draw', self.draw)
		self.cm.register_callback('phase', self.phase)
		self.cm.register_callback('new_turn', self.new_turn)
		self.cm.register_callback('idle', self.idle)
		self.cm.register_callback('select_place', self.select_place)
		self.cm.register_callback('select_chain', self.select_chain)
		self.cm.register_callback('summoning', self.summoning)
		self.cm.register_callback("select_battlecmd", self.select_battlecmd)
		self.cm.register_callback('attack', self.attack)
		self.cm.register_callback('begin_damage', self.begin_damage)
		self.cm.register_callback('end_damage', self.end_damage)
		self.cm.register_callback('battle', self.battle)
		self.cm.register_callback('damage', self.damage)
		self.cm.register_callback('hint', self.hint)
		self.cm.register_callback('select_card', self.select_card)
		self.cm.register_callback('move', self.move)
		self.cm.register_callback('select_option', self.select_option)
		self.cm.register_callback('recover', self.recover)
		self.cm.register_callback('select_tribute', partial(self.select_card, is_tribute=True))
		self.cm.register_callback('pos_change', self.pos_change)
		self.cm.register_callback('set', self.set)
		self.cm.register_callback("chaining", self.chaining)
		self.cm.register_callback('select_position', self.select_position)
		self.cm.register_callback('yesno', self.yesno)
		self.cm.register_callback('select_effectyn', self.select_effectyn)
		self.cm.register_callback('win', self.win)
		self.cm.register_callback('pay_lpcost', self.pay_lpcost)
		self.cm.register_callback('sort_chain', self.sort_chain)
		self.cm.register_callback('announce_attrib', self.announce_attrib)
		self.cm.register_callback('select_sum', self.select_sum)
		self.cm.register_callback('select_counter', self.select_counter)
		self.cm.register_callback('announce_race', self.announce_race)
		self.cm.register_callback('become_target', self.become_target)
		self.cm.register_callback('debug', self.debug)
		self.debug_mode = False
		self.players = [None, None]
		self.lp = [8000, 8000]
		self.started = False

	def draw(self, player, cards):
		pl = self.players[player]
		pl.notify("Drew %d cards:" % len(cards))
		for i, c in enumerate(cards):
			pl.notify("%d: %s" % (i+1, c.name))
		self.players[1 - player].notify("Opponent drew %d cards." % len(cards))

	def phase(self, phase):
		phases = {
			1: 'draw',
			2: 'standby',
			4: 'main1',
			8: 'battle start',
			0x10: 'battle step',
			0x20: 'damage',
			0x40: 'damage calculation',
			0x80: 'battle',
			0x100: 'main2',
			0x200: 'end',
		}
		phase_str = phases.get(phase, str(phase))
		for pl in self.players:
			pl.notify('entering %s phase.' % phase_str)
		self.current_phase = phase

	def new_turn(self, tp):
		self.tp = tp
		self.players[tp].notify("Your turn.")
		self.players[1 - tp].notify("%s's turn." % self.players[tp].nickname)

	def idle(self, summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs):
		self.state = "idle"
		pl = self.players[self.tp]
		self.summonable = summonable
		self.spsummon = spsummon
		self.repos = repos
		self.idle_mset = idle_mset
		self.idle_set = idle_set
		self.idle_activate = idle_activate
		self.to_bp = bool(to_bp)
		self.to_ep = bool(to_ep)
		self.idle_action(pl)

	def idle_action(self, pl):
		def prompt():
			pl.notify("Select a card on which to perform an action.")
			pl.notify("h shows your hand, tab and tab2 shows your or the opponent's table.")
			if self.to_bp:
				pl.notify("b: Enter the battle phase.")
			if self.to_ep:
				pl.notify("e: End phase.")
			pl.notify(DuelReader, r, no_abort="Invalid specifier. Retry.", restore_parser=duel_parser)
		cards = []
		for i in (0, 1):
			for j in (dm.LOCATION_HAND, dm.LOCATION_MZONE, dm.LOCATION_SZONE, dm.LOCATION_GRAVE, dm.LOCATION_EXTRA):
				cards.extend(self.get_cards_in_location(i, j))
		specs = set(self.card_to_spec(self.tp, card) for card in cards)
		def r(caller):
			if caller.text == 'b' and self.to_bp:
				self.set_responsei(6)
				reactor.callLater(0, procduel, self)
				return
			elif caller.text == 'e' and self.to_ep:
				self.set_responsei(7)
				reactor.callLater(0, procduel, self)
				return
			if caller.text not in specs:
				pl.notify("Invalid specifier. Retry.")
				prompt()
				return
			loc, seq = self.cardspec_to_ls(caller.text)
			if caller.text.startswith('o'):
				plr = 1 - self.tp
			else:
				plr = self.tp
			card = self.get_card(plr, loc, seq)
			if not card:
				pl.notify("There is no card in that position.")
				pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
				return
			if plr == 1 - self.tp:
				if card.position in (0x8, 0xa):
					pl.notify("Face-down card.")
					return prompt()
				pl.notify(card.info())
				return prompt()
			self.act_on_card(caller, card)
		prompt()

	def act_on_card(self, caller, card):
		pl = self.players[self.tp]
		pl.notify(card.name)
		if card in self.summonable:
			pl.notify("s: Summon this card in face-up attack position.")
		if card in self.idle_set:
			pl.notify("t: Set this card.")
		if card in self.idle_mset:
			pl.notify("m: Summon this card in face-down defense position.")
		if card in self.repos:
			pl.notify("r: reposition this card.")
		if card in self.spsummon:
			pl.notify("c: Special summon this card.")
		if card in self.idle_activate:
			pl.notify("v: Idle activate this card.")
		pl.notify("i: Show card info.")
		pl.notify("z: back.")
		def action(caller):
			if caller.text == 's' and card in self.summonable:
				self.set_responsei(self.summonable.index(card) << 16)
			elif caller.text == 't' and card in self.idle_set:
				self.set_responsei((self.idle_set.index(card) << 16) + 4)
			elif caller.text == 'm' and card in self.idle_mset:
				self.set_responsei((self.idle_mset.index(card) << 16) + 3)
			elif caller.text == 'r' and card in self.repos:
				self.set_responsei((self.repos.index(card) << 16) + 2)
			elif caller.text == 'c' and card in self.spsummon:
				self.set_responsei((self.spsummon.index(card) << 16) + 1)
			elif caller.text == 'v' and card in self.idle_activate:
				self.set_responsei((self.idle_activate.index(card) << 16) + 5)
			elif caller.text == 'i':
				self.show_info(card, pl)
				pl.notify(DuelReader, action, no_abort="Invalid command", restore_parser=duel_parser)
				return
			elif caller.text == 'z':
				reactor.callLater(0, self.idle_action, pl)
				return
			else:
				pl.notify("Invalid action.")
				pl.notify(DuelReader, action, no_abort="Invalid command", restore_parser=duel_parser)
				return
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, action, no_abort="Invalid command", restore_parser=duel_parser)

	def cardspec_to_ls(self, text):
		if text.startswith('o'):
			text = text[1:]
		r = re.search(r'^([a-z]+)(\d+)', text)
		if not r:
			return (None, None)
		if r.group(1) == 'h':
			l = dm.LOCATION_HAND
		elif r.group(1) == 'm':
			l = dm.LOCATION_MZONE
		elif r.group(1) == 's':
			l = dm.LOCATION_SZONE
		elif r.group(1) == 'g':
			l = dm.LOCATION_GRAVE
		elif r.group(1) == 'x':
			l = dm.LOCATION_EXTRA
		else:
			return None, None
		return l, int(r.group(2)) - 1

	def pcl(self, name, cards):
		self.players[self.tp].notify(name+":")
		for card in cards:
			self.players[self.tp].notify(card.name)

	def select_place(self, player, count, flag):
		pl = self.players[player]
		specs = self.flag_to_usable_cardspecs(flag)
		pl.notify("Select place for card, one of %s." % ", ".join(specs))
		def r(caller):
			if caller.text not in specs:
				pl.notify("Invalid cardspec. Try again.")
				pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
				return
			l, s = self.cardspec_to_ls(caller.text)
			if caller.text.startswith('o'):
				plr = 1 - player
			else:
				plr = player
			resp = bytes([plr, l, s])
			self.set_responseb(resp)
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)

	def flag_to_usable_cardspecs(self, flag):
		pm = flag & 0xff
		ps = (flag >> 8) & 0xff
		om = (flag >> 16) & 0xff
		os = (flag >> 24) & 0xff
		zone_names = ('m', 's', 'om', 'os')
		specs = []
		for zn, val in zip(zone_names, (pm, ps, om, os)):
			for i in range(8):
				avail = val & (1 << i) == 0
				if avail:
					specs.append(zn + str(i + 1))
		return specs

	def select_chain(self, player, size, spe_count, forced, chains):
		if size == 0 and spe_count == 0:
			self.keep_processing = True
			self.set_responsei(-1)
			return
		pl = self.players[player]
		if forced:
			s = ""
		else:
			s = " (c to cancel)"
		pl.notify("Select chain%s:" % s)
		specs = {}
		chain_cards = [c[1] for c in chains]
		for et, card, desc in chains:
			cs = self.card_to_spec(player, card)
			specs[cs] = card
			pl.notify("%s: %s" % (cs, card.name))
			op = self.players[1 - player]
			if not op.seen_waiting:
				op.notify("Waiting for opponent.")
				op.seen_waiting = True
		def r(caller):
			if caller.text == 'c' and not forced:
				self.set_responsei(-1)
				reactor.callLater(0, procduel, self)
				return
			if caller.text.startswith('i'):
				info = True
				caller.text = caller.text[1:]
			else:
				info = False
			if caller.text not in specs:
				pl.notify("Invalid spec.")
				pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
				return
			card = specs[caller.text]
			idx = chain_cards.index(card)
			if info:
				self.show_info(card, pl)
				pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
				return
			self.set_responsei(idx)
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)

	def select_option(self, player, options):
		def select(caller, idx):
			self.set_responsei(idx)
			reactor.callLater(0, procduel, self)
		opts = []
		for opt in options:
			if opt > 10000:
				code = opt >> 4
				string = dm.Card.from_code(code).strings[opt & 0xf]
			else:
				string = "Unknown option %d" % opt
			opts.append(string)
		m = Menu("Select option:", no_abort="Invalid option.", persistent=True, restore_parser=duel_parser)
		for idx, opt in enumerate(opts):
			m.item(opt)(lambda caller, idx=idx: select(caller, idx))
		self.players[player].notify(m)

	def summoning(self, card, special=False):
		if special:
			action = "Special summoning"
		else:
			action = "Summoning"
		pos = card.position_name()
		nick = self.players[card.controller].nickname
		for pl in self.players:
			pl.notify("%s %s %s (%d/%d) in %s position." % (nick, action, card.name, card.attack, card.defense, pos))

	def select_battlecmd(self, player, activatable, attackable, to_m2, to_ep):
		self.state = "battle"
		self.activatable = activatable
		self.attackable = attackable
		self.to_m2 = bool(to_m2)
		self.to_ep = bool(to_ep)
		pl = self.players[player]
		self.display_battle_menu(pl)

	def display_battle_menu(self, pl):
		pl.notify("Battle menu:")
		if self.attackable:
			pl.notify("a: Attack.")
		if self.activatable:
			pl.notify("c: activate.")
		if self.to_m2:
			pl.notify("m: Main phase 2.")
		if self.to_ep:
			pl.notify("e: End phase.")
		def r(caller):
			if caller.text == 'a' and self.attackable:
				self.battle_attack(caller.connection)
			elif caller.text == 'c' and self.activatable:
				self.battle_activate(caller.connection)
			elif caller.text == 'e' and self.to_ep:
				self.set_responsei(3)
				reactor.callLater(0, procduel, self)
			elif caller.text == 'm' and self.to_m2:
				self.set_responsei(2)
				reactor.callLater(0, procduel, self)
			else:
				pl.notify("Invalid option.")
				pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
		pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)

	def battle_attack(self, con):
		pl = self.players[con.duel_player]
		pln = con.duel_player
		pl.notify("Select card to attack with:")
		specs = {}
		for c in self.attackable:
			spec = self.card_to_spec(pln, c)
			pl.notify("%s: %s (%d/%d)" % (spec, c.name, c.attack, c.defense))
			specs[spec] = c
		pl.notify("z: back.")
		def r(caller):
			if caller.text == 'z':
				self.display_battle_menu(pl)
				return
			if caller.text not in specs:
				pl.notify("Invalid cardspec. Retry.")
				pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
				return
			card = specs[caller.text]
			seq = self.attackable.index(card)
			self.set_responsei((seq << 16) + 1)
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)

	def battle_activate(self, con):
		pl = self.players[con.duel_player]
		pln = con.duel_player
		pl.notify("Select card to activate:")
		specs = {}
		for c in self.activatable:
			spec = self.card_to_spec(pln, c)
			pl.notify("%s: %s (%d/%d)" % (spec, c.name, c.attack, c.defense))
			specs[spec] = c
		pl.notify("z: back.")
		def r(caller):
			if caller.text == 'z':
				self.display_battle_menu(pl)
				return
			if caller.text not in specs:
				pl.notify("Invalid cardspec. Retry.")
				pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
				return
			card = specs[caller.text]
			seq = self.activatable.index(card)
			self.set_responsei((seq << 16))
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)

	def card_to_spec(self, player, card):
		s = ""
		if card.controller != player:
			s += "o"
		if card.location == dm.LOCATION_HAND:
			s += "h"
		elif card.location == dm.LOCATION_MZONE:
			s += "m"
		elif card.location == dm.LOCATION_SZONE:
			s += "s"
		elif card.location == dm.LOCATION_GRAVE:
			s += "g"
		elif card.location == dm.LOCATION_EXTRA:
			s += "x"
		s += str(card.sequence + 1)
		return s

	def attack(self, ac, al, aseq, apos, tc, tl, tseq, tpos):
		acard = self.get_card(ac, al, aseq)
		if not acard:
			return
		name = self.players[ac].nickname
		if tc == 0 and tl == 0 and tseq == 0 and tpos == 0:
			for pl in self.players:
				aspec = self.card_to_spec(pl.duel_player, acard)
				pl.notify("%s prepares to attack with %s (%s)" % (name, aspec, acard.name))
			return
		tcard = self.get_card(tc, tl, tseq)
		if not tcard:
			return
		for pl in self.players:
			aspec = self.card_to_spec(pl.duel_player, acard)
			tspec = self.card_to_spec(pl.duel_player, tcard)
			tcname = tcard.name
			if tcard.controller != pl.duel_player and tcard.position in (0x8, 0xa):
				tcname = tcard.position_name() + " card"
			pl.notify("%s prepares to attack %s (%s) with %s (%s)" % (name, tspec, tcname, aspec, acard.name))

	def begin_damage(self):
		self.notify_all("begin damage")

	def end_damage(self):
		self.notify_all("end damage")

	def battle(self, attacker, aa, ad, bd0, tloc, da, dd, bd1):
		loc = (attacker >> 8) & 0xff
		seq = (attacker >> 16) & 0xff
		c2 = attacker & 0xff
		card = self.get_card(c2, loc, seq)
		tc = tloc & 0xff
		tl = (tloc >> 8) & 0xff
		tseq = (tloc >> 16) & 0xff
		if tloc:
			target = self.get_card(tc, tl, tseq)
		else:
			target = None
		s = "%s (%d/%d) attacks" % (card.name, aa, ad)
		if target:
			s += " %s (%d/%d)" % (target.name, da, dd)
		self.notify_all(s)

	def damage(self, player, amount):
		new_lp = self.lp[player]-amount
		self.players[player].notify("Your lp decreased by %d, now %d" % (amount, new_lp))
		self.players[1 - player].notify("%s's lp decreased by %d, now %d" % (self.players[player].nickname, amount, new_lp))
		self.lp[player] -= amount

	def recover(self, player, amount):
		new_lp = self.lp[player] + amount
		self.players[player].notify("Your lp increased by %d, now %d" % (amount, new_lp))
		self.players[1 - player].notify("%s's lp increased by %d, now %d" % (self.players[player].nickname, amount, new_lp))
		self.lp[player] += amount

	def notify_all(self, s):
		for pl in self.players:
			pl.notify(s)

	def hint(self, msg, player, data):
		if msg == 3 and data in strings.SYSTEM_STRINGS:
			self.players[player].notify(strings.SYSTEM_STRINGS[data])
		elif msg == 6 or msg == 7:
			reactor.callLater(0, procduel, self)

	def select_card(self, player, cancelable, min_cards, max_cards, cards, is_tribute=False):
		con = self.players[player]
		if is_tribute:
			s = " to tribute"
		else:
			s = ""
		con.notify("Select %d to %d cards%s separated by spaces:" % (min_cards, max_cards, s))
		for i, c in enumerate(cards):
			name = c.name
			if c.controller != player and c.position in (0x8, 0xa):
				name = c.position_name() + " card"
			con.notify("%d: %s" % (i+1, name))
		def error(text):
			con.notify(text)
			con.notify(DuelReader, f, no_abort="Invalid command", restore_parser=duel_parser)
		def f(caller):
			cds = caller.text.split()
			try:
				cds = [int(i) - 1 for i in cds]
			except ValueError:
				return error("Invalid value.")
			if len(cds) != len(set(cds)):
				return error("Duplicate values not allowed.")
			if (not is_tribute and len(cds) < min_cards) or len(cds) > max_cards:
				return error("Please enter between %d and %d cards." % (min_cards, max_cards))
			if min(cds) < 0 or max(cds) > len(cards) - 1:
				return error("Invalid value.")
			buf = bytes([len(cds)])
			tribute_value = 0
			for i in cds:
				tribute_value += (cards[i].release_param if is_tribute else 0)
				buf += bytes([i])
			if is_tribute and tribute_value < min_cards:
				return error("Not enough tributes.")
			self.set_responseb(buf)
			reactor.callLater(0, procduel, self)
		con.notify(DuelReader, f, no_abort="Invalid command", restore_parser=duel_parser)

	def show_table(self, con, player, hide_facedown=False):
		mz = self.get_cards_in_location(player, dm.LOCATION_MZONE)
		sz = self.get_cards_in_location(player, dm.LOCATION_SZONE)
		if len(mz+sz) == 0:
			con.notify("Table is empty.")
			return
		for card in mz:
			s = "m%d: " % (card.sequence + 1)
			if hide_facedown and card.position in (0x8, 0xa):
				s += card.position_name()
			else:
				s += card.name + " "
				s += "(%d/%d) " % (card.attack, card.defense)
				s += card.position_name()
			con.notify(s)
		for card in sz:
			s = "s%d: " % (card.sequence + 1)
			if hide_facedown and card.position in (0x8, 0xa):
				s += card.position_name()
			else:
				s += card.name + " "
				s += card.position_name()
			con.notify(s)

	def show_cards_in_location(self, con, player, location, hide_facedown=False):
		cards = self.get_cards_in_location(player, location)
		if not cards:
			con.notify("Table is empty.")
			return
		for card in cards:
			s = self.card_to_spec(player, card)
			if hide_facedown and card.position in (0x8, 0xa):
				s += card.position_name()
			else:
				s += card.name + " "
				s += card.position_name()
			con.notify(s)

	def show_hand(self, con, player):
		h = self.get_cards_in_location(player, dm.LOCATION_HAND)
		if not h:
			con.notify("Your hand is empty.")
			return
		for c in h:
			con.notify("h%d: %s" % (c.sequence + 1, c.name))

	def show_score(self, con):
		player = con.duel_player
		duel = con.duel
		con.notify("Your LP: %d Opponent LP: %d" % (duel.lp[player], duel.lp[1 - player]))
		deck = duel.get_cards_in_location(player, dm.LOCATION_DECK)
		odeck = duel.get_cards_in_location(1 - player, dm.LOCATION_DECK)
		grave = duel.get_cards_in_location(player, dm.LOCATION_GRAVE)
		ograve = duel.get_cards_in_location(1 - player, dm.LOCATION_GRAVE)
		hand = duel.get_cards_in_location(player, dm.LOCATION_HAND)
		ohand = duel.get_cards_in_location(1 - player, dm.LOCATION_HAND)
		removed = duel.get_cards_in_location(player, dm.LOCATION_REMOVED)
		oremoved = duel.get_cards_in_location(1 - player, dm.LOCATION_REMOVED)
		con.notify("Hand: You: %d Opponent: %d" % (len(hand), len(ohand)))
		con.notify("Deck: You: %d Opponent: %d" % (len(deck), len(odeck)))
		con.notify("Grave: You: %d Opponent: %d" % (len(grave), len(ograve)))
		con.notify("Removed: You: %d Opponent: %d" % (len(removed), len(oremoved)))

	def move(self, code, location, newloc, reason):
		card = dm.Card.from_code(code)
		card.set_location(location)
		pl = self.players[card.controller]
		op = self.players[1 - card.controller]
		plspec = self.card_to_spec(pl.duel_player, card)
		opspec = self.card_to_spec(op.duel_player, card)
		if reason & 0x01:
			pl.notify("Card %s (%s) destroyed." % (plspec, card.name))
			op.notify("Card %s (%s) destroyed." % (opspec, card.name))

	def show_info(self, card, pl):
		pln = pl.duel_player
		cs = self.card_to_spec(pln, card)
		if card.position in (0x8, 0xa) and card in self.get_cards_in_location(1 - pln, dm.LOCATION_MZONE) + self.get_cards_in_location(1 - pln, dm.LOCATION_SZONE):
			pos = card.position_name()
			pl.notify("%s: %s card." % (cs, pos))
			return
		pl.notify(card.info())

	def show_info_cmd(self, con, spec):
		cards = []
		for i in (0, 1):
			for j in (dm.LOCATION_MZONE, dm.LOCATION_SZONE, dm.LOCATION_GRAVE):
				cards.extend(card for card in self.get_cards_in_location(i, j) if card.controller == con.duel_player or card.position not in (0x8, 0xa))
		specs = {}
		for card in cards:
			specs[self.card_to_spec(con.duel_player, card)] = card
		if spec not in specs:
			con.notify("Invalid card.")
			return
		self.show_info(specs[spec], con)

	def pos_change(self, card, prevpos):
		cs = self.card_to_spec(card.controller, card)
		cso = self.card_to_spec(1 - card.controller, card)
		newpos = card.position_name()
		self.players[card.controller].notify("The position of card %s (%s) was changed to %s." % (cs, card.name, newpos))
		self.players[1 - card.controller].notify("The position of card %s (%s) was changed to %s." % (cso, card.name, newpos))

	def set(self, card):
		c = card.controller
		self.players[c].notify("You set %s (%s) in %s position." %
		(self.card_to_spec(c, card), card.name, card.position_name()))
		op = 1 - c
		on = self.players[c].nickname
		self.players[op].notify("%s sets %s in %s position." %
		(on, self.card_to_spec(op, card), card.position_name()))

	def chaining(self, card, tc, tl, ts, desc, cs):
		c = card.controller
		o = 1 - c
		n = self.players[c].nickname
		self.players[c].notify("Activating %s" % card.name)
		self.players[o].notify("%s activating %s" % (n, card.name))

	def select_position(self, player, card, positions):
		pl = self.players[player]
		m = Menu("Select position for %s:" % (card.name,), no_abort="Invalid option.", persistent=True, restore_parser=duel_parser)
		def set(caller, pos=None):
			self.set_responsei(pos)
			reactor.callLater(0, procduel, self)
		if positions & 1:
			m.item("Face-up attack")(lambda caller: set(caller, 1))
		if positions & 2:
			m.item("Face-down attack")(lambda caller: set(caller, 2))
		if positions & 4:
			m.item("Face-up defense")(lambda caller: set(caller, 4))
		if positions & 8:
			m.item("Face-down defense")(lambda caller: set(caller, 8))
		pl.notify(m)

	def yesno(self, player, desc):
		pl = self.players[player]
		def yes(caller):
			self.set_responsei(1)
			reactor.callLater(0, procduel, self)
		def no(caller):
			self.set_responsei(0)
			reactor.callLater(0, procduel, self)
		if desc > 10000:
			code = desc >> 4
			opt = dm.Card.from_code(code).strings[desc & 0xf]
		else:
			opt = "String %d" % desc
			opt = strings.SYSTEM_STRINGS.get(desc, opt)
		pl.notify(YesOrNo, opt, yes, no=no)

	def select_effectyn(self, player, card):
		pl = self.players[player]
		def yes(caller):
			self.set_responsei(1)
			reactor.callLater(0, procduel, self)
		def no(caller):
			self.set_responsei(0)
			reactor.callLater(0, procduel, self)
		question = "Do you want to use the effect from %s in %s?" % (card.name, self.card_to_spec(player, card))
		pl.notify(YesOrNo, question, yes, no=no)

	def win(self, player, reason):
		if player == 2:
			self.notify_all("The duel was a draw.")
			self.end()
			return
		winner = self.players[player]
		loser = self.players[1 - player]
		winner.notify("You won.")
		loser.notify("You lost.")
		self.end()

	def pay_lpcost(self, player, cost):
		self.lp[player] -= cost
		self.players[player].notify("You pay %d LP. Your LP is now %d." % (cost, self.lp[player]))
		self.players[1 - player].notify("%s pays %d LP. Their LP is now %d." % (self.players[player].nickname, cost, self.lp[player]))

	def sort_chain(self, player, cards):
		self.set_responsei(-1)
		reactor.callLater(0, procduel, self)

	def announce_attrib(self, player, count, avail):
		attributes = ('Earth', 'Water', 'Fire', 'Wind', 'Light', 'Dark', 'Divine')
		attrmap = {k: (1<<i) for i, k in enumerate(attributes)}
		avail_attributes = {k: v for k, v in attrmap.items() if avail & v}
		avail_attributes_keys = avail_attributes.keys()
		avail_attributes_values = list(avail_attributes.values())
		pl = self.players[player]
		def prompt():
			pl.notify("Type %d attributes separated by spaces." % count)
			for i, attrib in enumerate(avail_attributes_keys):
				pl.notify("%d. %s" % (i + 1, attrib))
			pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
		def r(caller):
			items = caller.text.split()
			ints = []
			try:
				ints = [int(i) for i in items]
			except ValueError:
				pass
			ints = [i for i in ints if i > 0 <= len(avail_attributes_keys)]
			ints = set(ints)
			if len(ints) != count:
				pl.notify("Invalid attributes.")
				return prompt()
			value = sum(avail_attributes_values[i - 1] for i in ints)
			self.set_responsei(value)
			reactor.callLater(0, procduel, self)
		return prompt()

	def select_sum(self, mode, player, val, select_min, select_max, must_select, select_some):
		pl = self.players[player]
		must_select_value = sum(c.param for c in must_select)
		def prompt():
			pl.notify("Select cards with a total value of at least %d, seperated by spaces." % (val - must_select_value))
			for c in must_select:
				pl.notify("%s must be selected, automatically selected." % c.name)
			for i, card in enumerate(select_some):
				pl.notify("%d: %s (%d)" % (i+1, card.name, card.param))
			return pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=duel_parser)
		def error(t):
			pl.notify(t)
			return prompt()
		def r(caller):
			text = caller.text.split()
			ints = []
			try:
				for i in text:
					ints.append(int(i) - 1)
			except ValueError:
				return error("Invalid entry.")
			if len(ints) != len(set(ints)):
				return error("Duplicate values not allowed.")
			if any(i for i in ints if i < 1 or i > len(select_some) - 1):
				return error("Value out of range.")
			s = sum(select_some[i].param for i in ints)
			if s < val - must_select_value:
				return error("%d is less than %d." % (s, val - must_select_value))
			lst = [len(ints) + len(must_select)]
			lst.extend([0] * len(must_select))
			lst.extend(ints)
			b = bytes(lst)
			self.set_responseb(b)
			reactor.callLater(0, procduel, self)
		prompt()

	def select_counter(self, player, countertype, count, cards):
		pl = self.players[player]
		def prompt():
			pl.notify("Adjust counters for %d cards, separated by spaces." % len(cards))
			for c in cards:
				pl.notify("%s (%d)" % (c.name, c.counter))
			pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=duel_parser)
		def error(text):
			pl.notify(text)
			return prompt()
		def r(caller):
			ints = self.parse_ints(caller.text)
			ints = [i & 0xffff for i in ints]
			if len(ints) != len(cards):
				return error("Please specify %d values." % len(cards))
			if any(cards[i].counter < val for i, val in enumerate(ints)):
				return error("Values cannot be greater than counter.")
			if sum(ints) != count:
				return error("Please specify %d values with a sum of %d." % (len(cards), count))
			bytes = struct.pack('h' * count, *ints)
			self.set_responseb(bytes)
			reactor.callLater(0, procduel, self)
		prompt()

	def parse_ints(self, text):
		ints = []
		try:
			for i in text.split():
				ints.append(int(i))
		except ValueError:
			pass
		return ints

	def become_target(self, tc, tl, tseq):
		card = self.get_card(tc, tl, tseq)
		if not card:
			return
		name = self.players[self.tp].nickname
		for pl in self.players:
			spec = self.card_to_spec(pl.duel_player, card)
			tcname = card.name
			if card.controller != pl.duel_player and card.position in (0x8, 0xa):
				tcname = card.position_name() + " card"
			pl.notify("%s targets %s (%s)" % (name, spec, tcname))

	def announce_race(self, player, count, avail):
		races = (
			"Warrior", "Spellcaster", "Fairy", "Fiend", "Zombie",
			"Machine", "Aqua", "Pyro", "Rock", "Wind Beast",
			"Plant", "Insect", "Thunder", "Dragon", "Beast",
			"Beast Warrior", "Dinosaur", "Fish", "Sea Serpent", "Reptile",
			"psycho", "Divine", "Creator god", "Wyrm", "Cybers",
		)
		racemap = {k: (1<<i) for i, k in enumerate(races)}
		avail_races = {k: v for k, v in racemap.items() if avail & v}
		pl = self.players[player]
		def prompt():
			pl.notify("Type %d races separated by spaces." % count)
			for i, s in enumerate(avail_races.keys()):
				pl.notify("%d: %s" % (i+1, s))
			pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=duel_parser)
		def error(text):
			pl.notify(text)
			pl.notify(DuelReader, r, no_abort="Invalid entry.", restore_parser=duel_parser)
		def r(caller):
			ints = []
			try:
				for i in caller.text.split():
					ints.append(int(i) - 1)
			except ValueError:
				return error("Invalid value.")
			if len(ints) != count:
				return error("%d items required." % count)
			if len(ints) != len(set(ints)):
				return error("Duplicate values not allowed.")
			if any(i > len(avail_races) - 1 or i < 0 for i in ints):
				return error("Invalid value.")
			result = 0
			for i in ints:
				result |= list(avail_races.values())[i]
			self.set_responsei(result)
			reactor.callLater(0, procduel, self)
		prompt()

	def end(self):
		super(MyDuel, self).end()
		for pl in self.players:
			pl.duel = None
			pl.intercept = None
			pl.parser = parser

	def start_debug(self):
		self.debug_mode = True
		lt = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
		fn = lt+"_"+self.players[0].nickname+"_"+self.players[1].nickname
		self.debug_fp = open(os.path.join('duels', fn), 'w')
		self.debug(event_type='start', player0=self.players[0].nickname, player1=self.players[1].nickname,
		deck0=self.cards[0], deck1=self.cards[1])

	def debug(self, **kwargs):
		if not self.debug_mode:
			return
		s = json.dumps(kwargs)
		self.debug_fp.write(s+'\n')
		self.debug_fp.flush()

class DuelReader(Reader):
	def handle_line(self, con, line):
		con.seen_waiting = False
		for s, c in duel_parser.command_substitutions.items():
			if line.startswith(s):
				line = c+" "+line[1:]
				break
		cmd, args = self.split(line)
		if cmd in duel_parser.commands:
			duel_parser.handle_line(con, line)
			con.notify(self, self.done)
		else:
			super().handle_line(con, line)

@duel_parser.command(names=['h', 'hand'])
def hand(caller):
	con = caller.connection
	if not con.duel:
		con.notify("Not in a duel.")
		return
	con.duel.show_hand(con, con.duel_player)

@duel_parser.command(names=['tab'])
def tab(caller):
	duel = caller.connection.duel
	if not duel:
		caller.connection.notify("Not in a duel.")
		return
	caller.connection.notify("Your table:")
	duel.show_table(caller.connection, caller.connection.duel_player)

@duel_parser.command(names=['tab2'])
def tab2(caller):
	duel = caller.connection.duel
	if not duel:
		caller.connection.notify("Not in a duel.")
		return
	caller.connection.notify("Opponent's table:")
	duel.show_table(caller.connection, 1 - caller.connection.duel_player, True)

@duel_parser.command(names=['grave'])
def grave(caller):
	if not caller.connection.duel:
		caller.connection.notify("Not in a duel.")
		return
	caller.connection.duel.show_cards_in_location(caller.connection, caller.connection.duel_player, dm.LOCATION_GRAVE)

@duel_parser.command(names=['grave2'])
def grave2(caller):
	if not caller.connection.duel:
		caller.connection.notify("Not in a duel.")
		return
	caller.connection.duel.show_cards_in_location(caller.connection, 1 - caller.connection.duel_player, dm.LOCATION_GRAVE, True)

@duel_parser.command(names=['extra'])
def extra(caller):
	if not caller.connection.duel:
		caller.connection.notify("Not in a duel.")
		return
	caller.connection.duel.show_cards_in_location(caller.connection, caller.connection.duel_player, dm.LOCATION_EXTRA)

@duel_parser.command(names=['extra2'])
def extra2(caller):
	if not caller.connection.duel:
		caller.connection.notify("Not in a duel.")
		return
	caller.connection.duel.show_cards_in_location(caller.connection, 1 - caller.connection.duel_player, dm.LOCATION_EXTRA, True)

@parser.command(names='deck', args_regexp=r'(.*)')
def deck(caller):
	lst = caller.args[0].split(None, 1)
	cmd = lst[0]
	caller.args = lst[1:]
	if cmd == 'load':
		deck_load(caller)
	elif cmd == 'edit':
		deck_edit(caller)
	elif cmd == 'list':
		deck_list(caller)
	elif cmd == 'clear':
		deck_clear(caller)
	elif cmd == 'delete':
		deck_delete(caller)
	elif cmd == 'import':
		deck_import(caller)
	elif cmd == 'new':
		deck_new(caller)
	else:
		caller.connection.notify("Invalid deck command.")

def deck_list(caller):
	decks = caller.connection.account.decks
	if not decks:
		caller.connection.notify("No decks.")
		caller.connection.session.commit()
		return
	for deck in decks:
		caller.connection.notify(deck.name)
	caller.connection.session.commit()

def deck_load(caller):
	session = caller.connection.session
	name = caller.args[0]
	account = caller.connection.account
	if name.startswith('public/'):
		account = session.query(models.Account).filter_by(name='Public').first()
		name = name[7:]
	deck = session.query(models.Deck).filter_by(account_id=account.id, name=name).first()
	if not deck:
		caller.connection.notify("Deck doesn't exist.")
		session.commit()
		return
	content = json.loads(deck.content)
	caller.connection.deck = content
	session.commit()
	caller.connection.notify("Deck loaded with %d cards." % len(content['cards']))

def deck_clear(caller):
	if not caller.args:
		caller.connection.notify("Clear which deck?")
		return
	name = caller.args[0]
	account = caller.connection.account
	session = caller.connection.session
	deck = models.Deck.find(session, account, name)
	if not deck:
		caller.connection.notify("Deck not found.")
		session.commit()
		return
	deck.content = json.dumps({'cards': []})
	session.commit()
	caller.connection.notify("Deck cleared.")

def deck_delete(caller):
	if not caller.args:
		caller.connection.notify("Delete which deck?")
		return
	name = caller.args[0]
	account = caller.connection.account
	session = caller.connection.session
	deck = models.Deck.find(session, account, name)
	if not deck:
		caller.connection.notify("Deck not found.")
		session.commit()
		return
	session.delete(deck)
	session.commit()
	caller.connection.notify("Deck deleted.")

def deck_edit(caller):
	con = caller.connection
	account = caller.connection.account
	deck_name = caller.args[0]
	deck = con.session.query(models.Deck).filter_by(account_id=con.account.id, name=deck_name).first()
	if deck:
		con.notify("Deck exists, loading.")
		con.deck = json.loads(deck.content)
	cards = con.deck['cards']
	def info():
		show_deck_info(con)
		con.notify("u: up d: down /: search t: top")
		con.notify("s: send to deck r: remove from deck l: list deck q: quit")
	def read():
		info()
		con.notify(Reader, r, prompt="Command (%d cards in deck):" % len(cards), no_abort="Invalid command", restore_parser=parser)
	def r(caller):
		code = all_cards[con.deck_edit_pos]
		if caller.text == 'd':
			con.deck_edit_pos+= 1
			if con.deck_edit_pos > len(all_cards) - 1:
				con.deck_edit_pos = len(all_cards) - 1
				con.notify("bottom of list.")
			read()
		elif caller.text == 'u':
			if con.deck_edit_pos == 0:
				con.notify("Top of list.")
				read()
				return
			con.deck_edit_pos -= 1
			read()
		elif caller.text == 't':
			con.notify("Top.")
			con.deck_edit_pos = 0
			read()
		elif caller.text == 's':
			if cards.count(code) == 3:
				con.notify("You already have 3 of this card in your deck.")
				read()
				return
			cards.append(code)
			save_deck(con.deck, con.session, con.account, deck_name)
			con.session.commit()
			read()
		elif caller.text.startswith('r'):
			rm = re.search(r'^r(\d+)', caller.text)
			if rm:
				n = int(rm.group(1)) - 1
				if n < 0 or n > len(cards) - 1:
					con.notify("Invalid card.")
					read()
					return
				code = cards[n]
			if cards.count(code) == 0:
				con.notify("This card isn't in your deck.")
				read()
				return
			cards.remove(code)
			save_deck(con.deck, con.session, con.account, deck_name)
			con.session.commit()
			read()
		elif caller.text.startswith('/'):
			pos = find_next(caller.text[1:], con.deck_edit_pos + 1)
			if not pos:
				con.notify("Not found.")
			else:
				con.deck_edit_pos = pos
			read()
		elif caller.text == 'l':
			for i, code in enumerate(cards):
				card = dm.Card.from_code(code)
				con.notify("%d: %s" % (i+1, card.name))
			read()
		elif caller.text == 'q':
			con.notify("Quit.")
		else:
			con.notify("Invalid command.")
			read()
	read()

def show_deck_info(con):
	cards = con.deck['cards']
	pos = con.deck_edit_pos
	code = all_cards[pos]
	in_deck = cards.count(code)
	if in_deck > 0:
		con.notify("%d in deck." % in_deck)
	card = dm.Card.from_code(code)
	con.notify(card.info())

def find_next(text, start):
	for i, code in enumerate(all_cards[start:]):
		card = dm.Card.from_code(code)
		if text.lower() in card.name.lower():
			return start+i

def save_deck(deck, session, account, name):
	deck = json.dumps(deck)
	existing_deck = session.query(models.Deck).filter_by(account_id=account.id, name=name).first()
	if existing_deck:
		new_deck = existing_deck
	else:
		new_deck = models.Deck(account_id=account.id, name=name)
		session.add(new_deck)
	new_deck.content = deck

def deck_import(caller):
	if not caller.args:
		caller.connection.notify("Import which deck?")
		return 
	deck_fn = os.path.join('decks', caller.args[0].replace('/', '_'))
	if not os.path.exists(deck_fn):
		caller.connection.notify("Deck not found.")
		return
	with open(deck_fn) as fp:
		deck = json.load(fp)
	save_deck(deck, caller.connection.session, caller.connection.account, caller.args[0].replace('/', '_'))
	caller.connection.session.commit()
	caller.connection.notify("Deck imported.")
	os.remove(deck_fn)

def deck_new(caller):
	if not caller.args:
		caller.connection.notify("Create which deck?")
		return
	name = caller.args[0]
	account = caller.connection.account
	session = caller.connection.session
	deck = models.Deck.find(session, account, name)
	if deck:
		caller.connection.notify("That deck already exists.")
		session.commit()
		return
	deck = models.Deck(account_id=account.id, name=name)
	session.add(deck)
	deck.content = json.dumps({'cards': []})
	session.commit()
	caller.connection.notify("Deck created.")

def get_player(name):
	return game.players.get(name.lower())

@parser.command(names=["chat"], args_regexp=r'(.*)')
def chat(caller):
	text = caller.args[0]
	if not text:
		caller.connection.chat = not caller.connection.chat
		if caller.connection.chat:
			caller.connection.notify("Chat on.")
		else:
			caller.connection.notify("Chat off.")
		return
	if not caller.connection.chat:
		caller.connection.chat = True
		caller.connection.notify("Chat on.")
	for pl in game.players.values():
		if pl.chat:
			pl.notify("%s chats: %s" % (caller.connection.nickname, caller.args[0]))

@parser.command(names=["say"], args_regexp=r'(.*)')
def say(caller):
	text = caller.args[0]
	if not text:
		caller.connection.notify("Say what?")
		return
	if not caller.connection.duel:
		caller.connection.notify("Not in a duel.")
		return
	for pl in caller.connection.duel.players:
		pl.notify("%s says: %s" % (caller.connection.nickname, caller.args[0]))

@parser.command(names=['who'])
def who(caller):
	caller.connection.notify("Online players:")
	for pl in game.players.values():
		s = pl.nickname
		if pl.duel:
			s += ' (dueling)'
		caller.connection.notify(s)

@duel_parser.command(names=['sc', 'score'])
def score(caller):
	if not caller.connection.duel:
		caller.connection.notify("Not in a duel.")
		return
	caller.connection.duel.show_score(caller.connection)

@parser.command(names=['replay'], args_regexp=r'(.*)=(\d+)')
def replay(caller):
	with open(os.path.join('duels', caller.args[0])) as fp:
		lines = [json.loads(line) for line in fp]
	limit = int(caller.args[1])
	for line in lines[:limit]:
		if line['event_type'] == 'start':
			player0 = get_player(line['player0'])
			player1 = get_player(line['player1'])
			if not player0 or not player1:
				con.notify("One of the players is not logged in.")
				return
			if player0.duel or player1.duel:
				con.notify("One of the players is in a duel.")
				return
			duel = MyDuel()
			duel.load_deck(0, line['deck0'], shuffle=False)
			duel.load_deck(1, line['deck1'], shuffle=False)
			duel.players = [player0, player1]
			player0.duel = duel
			player1.duel = duel
			player0.duel_player = 0
			player1.duel_player = 1
			duel.start()
		elif line['event_type'] == 'process':
			procduel_replay(duel)
		elif line['event_type'] == 'set_responsei':
			duel.set_responsei(line['response'])
		elif line['event_type'] == 'set_responseb':
			duel.set_responseb(line['response'].encode('latin1'))
	reactor.callLater(0, procduel, duel)

def procduel_replay(duel):
	res = dm.lib.process(duel.duel)
	cb = duel.cm.callbacks
	duel.cm.callbacks = collections.defaultdict(list)
	def tp(t):
		duel.tp = t
	duel.cm.register_callback('new_turn', tp)
	def recover(player, amount):
		duel.lp[player] += amount
	def damage(player, amount):
		duel.lp[player] -= amount
	duel.cm.register_callback('recover', recover)
	duel.cm.register_callback('damage', damage)
	data = duel.process_messages()
	duel.cm.callbacks = cb
	return data

@duel_parser.command(names=['info'], args_regexp=r'(.*)')
def info(caller):
	caller.connection.duel.show_info_cmd(caller.connection, caller.args[0])

@parser.command(names=['help'], args_regexp=r'(.*)')
def help(caller):
	topic = caller.args[0]
	if not topic:
		topic = "start"
	topic = topic.replace('/', '_').strip()
	fn = os.path.join('help', topic)
	if not os.path.isfile(fn):
		caller.connection.notify("No help topic.")
		return
	with open(fn, encoding='utf-8') as fp:
		caller.connection.notify(fp.read().rstrip('\n'))

@parser.command(names=['quit'])
def quit(caller):
	caller.connection.notify("Goodbye.")
	server.disconnect(caller.connection)

@parser.command(names=['lookup'], args_regexp=r'(.*)')
def lookup(caller):
	name = caller.args[0]
	r = re.compile(r'^(\d+)\.(.+)$')
	r = r.search(name)
	if r:
		n, name = int(r.group(1)), r.group(2)
	else:
		n = 1
	if n == 0:
		n = 1
	name = '%'+name+'%'
	rows = dm.db.execute('select id from texts where name like ? limit ?', (name, n)).fetchall()
	if not rows:
		caller.connection.notify("No results found.")
		return
	nr = rows[min(n - 1, len(rows) - 1)]
	card = dm.Card.from_code(nr[0])
	caller.connection.notify(card.info())

@parser.command(names=['echo'], args_regexp=r'(.*)')
def echo(caller):
	caller.connection.notify(caller.args[0])

@parser.command(names='passwd')
def passwd(caller):
	session = caller.connection.session
	account = caller.connection.account
	new_password = ""
	old_parser = caller.connection.parser
	def r(caller):
		if not account.check_password(caller.text):
			caller.connection.notify("Incorrect password.")
			session.commit()
			return
		caller.connection.notify(Reader, r2, prompt="New password:", no_abort="Invalid command.", restore_parser=old_parser)
	def r2(caller):
		nonlocal new_password
		new_password = caller.text
		if len(new_password) < 6:
			caller.connection.notify("Passwords must be at least 6 characters.")
			caller.connection.notify(Reader, r2, prompt="New password:", no_abort="Invalid command.", restore_parser=old_parser)
			return
		caller.connection.notify(Reader, r3, prompt="Confirm password:", no_abort="Invalid command.", restore_parser=old_parser)
	def r3(caller):
		if new_password != caller.text:
			caller.connection.notify("Passwords don't match.")
			session.commit()
			return
		account.set_password(caller.text)
		session.commit()
		caller.connection.notify("Password changed.")
	caller.connection.notify(Reader, r, prompt="Current password:", no_abort="Invalid command.", restore_parser=old_parser)

for key in parser.commands.keys():
	duel_parser.commands[key] = parser.commands[key]

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port', type=int, default=4000, help="Port to bind to")
	args = parser.parse_args()
	server.port = args.port
	server.run()

if __name__ == '__main__':
	main()
