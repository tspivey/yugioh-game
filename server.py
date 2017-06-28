import os
import re
import random
from functools import partial
import json
import datetime
import gsb
from gsb.intercept import Menu, Reader, YesOrNo
from twisted.internet import reactor
import duel as dm


all_cards = [int(row[0]) for row in dm.db.execute("select id from datas")]

players = {}
class MyServer(gsb.Server):
	nickname_re = re.compile(r'^[a-zA-Z0-9]+$')
	def on_connect(self, caller):
		caller.connection.deck = {'cards': []}
		caller.connection.deck_edit_pos = 0
		caller.connection.duel = None
		caller.connection.requested_opponent = None
		caller.connection.nickname = None
		self.notify(caller.connection, "Connected!")
		def prompt():
			caller.connection.notify(Reader, r, prompt="Nickname:")
		def r(caller):
			m = self.nickname_re.match(caller.text)
			if not m:
				caller.connection.notify("Invalid nickname, try again.")
				prompt()
				return
			elif get_player(caller.text):
				caller.connection.notify("That player is already logged in.")
				prompt()
				return
			for pl in players.values():
				pl.notify("%s logged in." % caller.text)
			players[caller.text.lower()] = caller.connection
			caller.connection.nickname = caller.text
			caller.connection.notify("Logged in.")
			if os.path.exists("motd.txt"):
				with open('motd.txt', 'r') as fp:
					caller.connection.notify(fp.read())
		prompt()

	def on_disconnect(self, caller):
		con = caller.connection
		if not con.nickname:
			return
		del players[con.nickname.lower()]
		for pl in players.values():
			pl.notify("%s logged out." % con.nickname)
		if con.duel:
			con.duel.notify_all("Your opponent disconnected, the duel is over.")
			con.duel.end()

server = MyServer(port=4000)

@server.command(r'^duel (.+)+$')
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
		pl.notify("Select a card on which to perform an action.")
		pl.notify("h shows your hand, tab and tab2 shows your or the opponent's table.")
		if self.to_bp:
			pl.notify("b: Enter the battle phase.")
		if self.to_ep:
			pl.notify("e: End phase.")
		def r(caller):
			if caller.text == 'h':
				self.show_hand(caller.connection, self.tp)
				pl.notify(DuelReader, r, no_abort=True)
				return
			if caller.text == 'b' and self.to_bp:
				self.set_responsei(6)
				reactor.callLater(0, procduel, self)
				return
			elif caller.text == 'e' and self.to_ep:
				self.set_responsei(7)
				reactor.callLater(0, procduel, self)
				return
			loc, seq = self.cardspec_to_ls(caller.text)
			if loc is None:
				pl.notify("Invalid specifier. Retry.")
				pl.notify(DuelReader, r, no_abort=True)
				return
			card = self.get_card(self.tp, loc, seq)
			if not card:
				pl.notify("There is no card in that position.")
				pl.notify(DuelReader, r, no_abort=True)
				return
			self.act_on_card(caller, card)
		pl.notify(DuelReader, r, no_abort=True)

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
				pl.notify(DuelReader, action, no_abort=True)
				return
			elif caller.text == 'z':
				reactor.callLater(0, self.idle_action, pl)
				return
			else:
				pl.notify("Invalid action.")
				pl.notify(DuelReader, action, no_abort=True)
				return
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, action, no_abort=True)

	def cardspec_to_ls(self, text):
		r = re.search(r'^([a-z]+)(\d+)', text)
		if not r:
			return (None, None)
		if r.group(1) == 'h':
			l = dm.LOCATION_HAND
		elif r.group(1) == 'm':
			l = dm.LOCATION_MZONE
		elif r.group(1) == 's':
			l = dm.LOCATION_SZONE
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
				pl.notify(DuelReader, r, no_abort=True)
				return
			l, s = self.cardspec_to_ls(caller.text)
			if caller.text.startswith('o'):
				plr = 1 - player
			else:
				plr = player
			resp = bytes([plr, l, s])
			self.set_responseb(resp)
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort=True)

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
				pl.notify(DuelReader, r, no_abort=True)
				return
			card = specs[caller.text]
			idx = chain_cards.index(card)
			if info:
				self.show_info(card, pl)
				pl.notify(DuelReader, r, no_abort=True)
				return
			self.set_responsei(idx)
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort=True)

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
		m = Menu("Select option:")
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
				pl.notify(DuelReader, r, no_abort=True)
		pl.notify(DuelReader, r, no_abort=True)

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
				pl.notify(DuelReader, r, no_abort=True)
				return
			card = specs[caller.text]
			seq = self.attackable.index(card)
			self.set_responsei((seq << 16) + 1)
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort=True)

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
				pl.notify(DuelReader, r, no_abort=True)
				return
			card = specs[caller.text]
			seq = self.activatable.index(card)
			self.set_responsei((seq << 16))
			reactor.callLater(0, procduel, self)
		pl.notify(DuelReader, r, no_abort=True)

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
		s += str(card.sequence + 1)
		return s

	def attack(self, attacker, target):
		pass

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
		self.notify_all("%s's lp decreased by %d, now %d" % (self.players[player].nickname, amount, self.lp[player]-amount))
		self.lp[player] -= amount

	def recover(self, player, amount):
		self.notify_all("%s's lp increased by %d, now %d" % (self.players[player].nickname, amount, self.lp[player] + amount))
		self.lp[player] += amount

	def notify_all(self, s):
		for pl in self.players:
			pl.notify(s)

	def hint(self, msg, player, data):
		if msg == 3 and data == 501:
			self.players[player].notify("Select a card to discard:")

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
			con.notify(DuelReader, f, no_abort=True)
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
		con.notify(DuelReader, f, no_abort=True)

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

	def show_hand(self, con, player):
		h = self.get_cards_in_location(player, dm.LOCATION_HAND)
		if not h:
			con.notify("Your hand is empty.")
			return
		for c in h:
			con.notify("h%d: %s" % (c.sequence + 1, c.name))

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
		m = Menu("Select position for %s:" % (card.name,), no_abort=True)
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

	def end(self):
		super(MyDuel, self).end()
		for pl in self.players:
			pl.duel = None
			pl.intercept = None

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

class DuelReader(Reader):
	def feed(self, caller):
		con = caller.connection
		text = caller.text
		if text == 'h':
			con.duel.show_hand(con, con.duel_player)
		elif text == 'tab':
			con.duel.show_table(con, con.duel_player)
		elif text == 'tab2':
			con.duel.show_table(con, 1 - con.duel_player, True)
		elif text.startswith("'"):
			for pl in players.values():
				pl.notify("%s: %s" % (con.nickname, text[1:]))
		if text in ('h', 'tab', 'tab2') or text.startswith("'"):
			caller.connection.notify(self, self.done)
			return
		super(DuelReader, self).feed(caller)

@server.command('^h(and)?$')
def hand(caller):
	con = caller.connection
	if not con.duel:
		con.notify("Not in a duel.")
		return
	con.duel.show_hand(con, con.duel_player)

@server.command('^tab$')
def tab(caller):
	duel = caller.connection.duel
	if not duel:
		caller.connection.notify("Not in a duel.")
		return
	duel.show_table(caller.connection, caller.connection.duel_player)

@server.command('^tab2$')
def tab2(caller):
	duel = caller.connection.duel
	if not duel:
		caller.connection.notify("Not in a duel.")
		return
	duel.show_table(caller.connection, 1 - caller.connection.duel_player, True)

@server.command(r'^deck load ([a-zA-Z0-9]+)')
def deck_load(caller):
	fn = caller.args[0].replace('/', '_')
	if not os.path.exists(os.path.join('decks', fn)):
		caller.connection.notify("No deck with that name.")
		return
	caller.connection.deck = load_deck(fn)
	caller.connection.notify("Deck loaded with %d cards." % len(caller.connection.deck['cards']))

@server.command(r'^deck edit ([a-zA-z0-9]+)')
def deck_edit(caller):
	con = caller.connection
	deck_name = caller.args[0].replace('/', '_')
	if os.path.exists(os.path.join('decks', deck_name)):
		con.notify("Deck exists, loading.")
		con.deck = load_deck(deck_name)
	cards = con.deck['cards']
	def info():
		show_deck_info(con)
		con.notify("u: up d: down /: search t: top")
		con.notify("s: send to deck r: remove from deck l: list deck q: quit")
	def read():
		info()
		con.notify(Reader, r, prompt="Command (%d cards in deck):" % len(cards), no_abort=True)
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
			save_deck(con.deck, deck_name)
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
			save_deck(con.deck, deck_name)
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

def load_deck(fn):
	with open(os.path.join('decks', fn)) as fp:
		return json.load(fp)

def save_deck(deck, filename):
	with open(os.path.join('decks', filename), 'w') as fp:
		fp.write(json.dumps(deck))

def get_player(name):
	return players.get(name.lower())

@server.command(r"^(?:'|say ) *(.+)")
def say(caller):
	for pl in players.values():
		pl.notify("%s: %s" % (caller.connection.nickname, caller.args[0]))

@server.command('^who$')
def who(caller):
	caller.connection.notify("Online players:")
	for pl in players.values():
		s = pl.nickname
		if pl.duel:
			s += ' (dueling)'
		caller.connection.notify(s)

if __name__ == '__main__':
	server.run()
