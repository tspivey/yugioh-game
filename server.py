import re
from functools import partial
import gsb
from gsb.intercept import Menu, Reader
from twisted.internet import reactor
import duel as dm

active_duel = None
duelp0 = None
duelp1 = None

class MyServer(gsb.Server):
	def on_connect(self, caller):
		self.notify(caller.connection, "Connected!")

server = MyServer(port=4000)
# Map of duels to tuple of players
duels = {}
@server.command(r'^duel *$')
def duel(caller):
	global active_duel, duelp0, duelp1
	if active_duel is None:
		active_duel = MyDuel()
		active_duel.load_deck(0, dm.deck)
		caller.connection.notify('Duel created. You are player 0.')
		active_duel.players[0] = caller.connection
		caller.connection.duel_player = 0
		duelp0 = caller.connection
		caller.connection.duel = active_duel
	else:
		caller.connection.notify("Joining duel as player 1 and starting.")
		active_duel.load_deck(1, dm.deck)
		caller.connection.duel_player = 1
		duelp1 = caller.connection
		active_duel.players[1] = caller.connection
		duels[active_duel] = (duelp0, duelp1)
		caller.connection.duel = active_duel
		active_duel.start()
		procduel(active_duel)

def procduel(d):
	while True:
		res = d.process()
		if res & 0x10000:
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

		self.players = [None, None]
		self.lp = [8000, 8000]

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
		for pl in self.players:
			pl.notify("Player %d is tp." % tp)

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

	def select_chain(self, player, size, spe_count, chains):
		if size == 0 and spe_count == 0:
			self.keep_processing = True
			self.set_responsei(-1)
			return
		pl = self.players[player]
		pl.notify("Select chain:")
		specs = {}
		chain_cards = [c[1] for c in chains]
		for et, card, desc in chains:
			cs = self.card_to_spec(player, card)
			specs[cs] = card
			pl.notify("%s: %s" % (cs, card.name))
		def r(caller):
			if caller.text == 'c':
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
			code = opt >> 4
			string = dm.Card.from_code(code).strings[opt & 0xf]
			opts.append(string)
		m = Menu("Select option:")
		for idx, opt in enumerate(opts):
			m.item(opt)(lambda caller, idx=idx: select(caller, idx))
		self.players[player].notify(m)

	def summoning(self, card, location):
		pos = str(hex(location))
		for pl in self.players:
			pl.notify("Player %d summoning %s in %s" % (self.tp, card.name, pos))

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
		def r(caller):
			if caller.text == 'a' and self.attackable:
				self.battle_attack(caller.connection)
			elif caller.text == 'c' and self.activatable:
				self.battle_activate(caller.connection)
			elif caller.text == 'e' and self.to_ep:
				self.set_responsei(3)
				reactor.callLater(0, procduel, self)
			elif caller.text == '2' and self.to_m2:
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
		self.players[self.tp].notify("Attack: attacker=%x target=%x" % (attacker, target))

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
		self.notify_all("Player %d's lp decreased by %d, now %d" % (player, amount, self.lp[player]-amount))
		self.lp[player] -= amount

	def recover(self, player, amount):
		self.notify_all("Player %d's lp increased by %d, now %d" % (player, amount, self.lp[player] + amount))
		self.lp[player] += amount

	def notify_all(self, s):
		for pl in self.players:
			pl.notify(s)

	def hint(self, msg, player, data):
		if msg == 3 and data == 501:
			self.players[player].notify("Select a card to discard:")

	def select_card(self, player, cancelable, min, max, cards, is_tribute=False):
		con = self.players[player]
		if is_tribute:
			s = " to tribute"
		else:
			s = ""
		con.notify("Select %d to %d cards%s separated by spaces:" % (min, max, s))
		for i, c in enumerate(cards):
			con.notify("%d: %s" % (i+1, c.name))
		def f(caller):
			cds = caller.text.split()
			if len(cds) < min or len(cds) > max:
				con.notify("Please enter between %d and %d cards." % (min, max))
				con.notify(DuelReader, f, no_abort=True)
				return
			buf = bytes([len(cds)])
			for i in cds:
				try:
					i = int(i) - 1
					if i < 0 or i > len(cards) - 1:
						raise ValueError
				except ValueError:
					con.notify("Invalid value.")
					con.notify(DuelReader, f, no_abort=True)
					return
				buf += bytes([i])
			self.set_responseb(buf)
			reactor.callLater(0, procduel, self)
		con.notify(DuelReader, f, no_abort=True)

	def show_table(self, con, player, hide_facedown=False):
		mz = self.get_cards_in_location(player, dm.LOCATION_MZONE)
		for card in mz:
			s = "m%d: " % (card.sequence + 1)
			if hide_facedown and card.position in (0x8, 0xa):
				s += self.position_name(card)
			else:
				s += card.name + " "
				s += "(%d/%d) " % (card.attack, card.defense)
				s += self.position_name(card)
			con.notify(s)
		sz = self.get_cards_in_location(player, dm.LOCATION_SZONE)
		for card in sz:
			s = "s%d: " % (card.sequence + 1)
			if hide_facedown and card.position in (0x8, 0xa):
				s += self.position_name(card)
			else:
				s += card.name + " "
				s += self.position_name(card)
			con.notify(s)

	def show_hand(self, con, player):
		h = self.get_cards_in_location(player, dm.LOCATION_HAND)
		if not h:
			con.notify("Your hand is empty.")
			return
		for c in h:
			con.notify("h%d: %s" % (c.sequence + 1, c.name))

	def position_name(self, card):
		if card.position == 0x1:
			return "face-up attack"
		elif card.position == 0x2:
			return "face-down attack"
		elif card.position == 0x4:
			return "face-up defense"
		elif card.position == 0x8:
			return "face-down defense"
		elif card.position == 0xa:
			return "face down"
		return str(card.position)

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
			pos = self.position_name(card)
			pl.notify("%s: %s card." % (cs, pos))
			return
		pl.notify(card.name)
		pl.notify("type: %d attack: %d defense: %d" % (card.type, card.attack, card.defense))
		pl.notify(card.desc)

	def pos_change(self, card, prevpos):
		cs = self.card_to_spec(card.controller, card)
		cso = self.card_to_spec(1 - card.controller, card)
		newpos = self.position_name(card)
		self.players[card.controller].notify("The position of card %s (%s) was changed to %s." % (cs, card.name, newpos))
		self.players[1 - card.controller].notify("The position of card %s (%s) was changed to %s." % (cso, card.name, newpos))

	def set(self, card):
		c = card.controller
		self.players[c].notify("You set %s (%s) in %s position." %
		(self.card_to_spec(c, card), card.name, self.position_name(card)))
		op = 1 - c
		on = "Player %d" % c
		self.players[op].notify("%s sets %s in %s position." %
		(on, self.card_to_spec(op, card), self.position_name(card)))

	def chaining(self, card, tc, tl, ts, desc, cs):
		c = card.controller
		o = 1 - c
		n = "Player %d" % c
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
			m.item("Face-down attack")(lambda caller: set(caller, 1))
		if positions & 4:
			m.item("Face-up defense")(lambda caller: set(caller, 1))
		if positions & 8:
			m.item("Face-down defense")(lambda caller: set(caller, 1))
		pl.notify(m)

class DuelReader(Reader):
	def feed(self, caller):
		con = caller.connection
		text = caller.text
		if text == 'h':
			con.duel.show_hand(con, con.duel_player)
		elif text == 'tab':
			con.duel.show_table(con, con.duel_player)
		elif text == 'tab2':
			con.duel.show_table(con, 1 - con.duel_player)
		if text in ('h', 'tab', 'tab2'):
			caller.connection.notify(self, self.done)
			return
		super(DuelReader, self).feed(caller)

@server.command('^h(and)?$')
def hand(caller):
	con = caller.connection
	con.duel.show_hand(con, con.duel_player)

def check_tp(f):
	def wraps(caller):
		if caller.connection.duel_player != caller.connection.duel.tp:
			caller.connection.notify("It's not your turn.")
			return
		f(caller)
	return wraps

@server.command(r'^summon ([a-z]+)(\d+)$')
@check_tp
def summon(caller):
	idle_action(caller, 'summon', 'summonable', 0)

@server.command(r'^mset ([a-z]+)(\d+)$')
@check_tp
def mset(caller):
	idle_action(caller, 'mset', 'idle_mset', 3)

def idle_action(caller, name, list_name, add):
	loc, n = caller.args
	n = int(n)
	duel = caller.connection.duel
	hand = duel.get_cards_in_location(caller.connection.duel_player, dm.LOCATION_HAND)
	seq = n - 1
	hc = [card for card in hand if card.sequence == seq]
	summonable = getattr(duel, list_name)
	summonable = [t for t in summonable if t[3] == seq]
	if not summonable:
		caller.connection.notify("Cannot %s %s." % (name, hc[0].name))
		return
	card, controller, location, sequence = summonable[0]
	i = (sequence << 16) + add
	duel.set_responsei(i)
	procduel(duel)

@server.command(r'^place ([a-z]+)(\d+)')
@check_tp
def place(caller):
	duel = caller.connection.duel
	place, n = caller.args
	n = int(n) - 1
	if n < 0 or place not in ('m', 's'):
		caller.connection.notify("Invalid place.")
		return
	l = p = 0
	if place == 'm':
		p = 4
	elif place == 's':
		p = 8
	resp = bytes([caller.connection.duel_player, p, n])
	duel.set_responseb(resp)
	procduel(duel)

@server.command(r'^bp$')
@check_tp
def bp(caller):
	duel = caller.connection.duel
	if not duel.to_bp:
		caller.connection.notify("Unable to enter battle phase.")
		return
	duel.set_responsei(6)
	procduel(duel)

@server.command(r'^ep$')
@check_tp
def ep(caller):
	duel = caller.connection.duel
	if not duel.to_ep:
		caller.connection.notify("Unable to enter end phase.")
		return
	if duel.current_phase == 8:
		duel.set_responsei(3)
	else:
		duel.set_responsei(7)
	procduel(duel)

@server.command(r'^m2$')
@check_tp
def m2(caller):
	duel = caller.connection.duel
	if not duel.to_m2 or duel.current_phase != 8:
		caller.connection.notify("Unable to enter main2 phase.")
		return
	duel.set_responsei(2)
	procduel(duel)

@server.command('^tab$')
def tab(caller):
	duel = caller.connection.duel

@server.command(r'^attack (\d+)$')
def attack(caller):
	duel = caller.connection.duel
	n = int(caller.args[0])
	if n < 1 or n > len(duel.attackable):
		caller.connection.notify("Invalid card.")
		return
	c = duel.attackable[n - 1]
	duel.set_responsei((c[3] << 16) + 1)
	procduel(duel)

@server.command("^t$")
def t(caller):
	def r(caller):
		pass
	caller.connection.notify(DuelReader, r, no_abort=True)

if __name__ == '__main__':
	server.run()