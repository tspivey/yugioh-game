import re
import sqlite3
import gsb

from twisted.internet import reactor

from .card import Card
from . import globals
from . import models
from .channels.challenge import Challenge
from .channels.chat import Chat

class Server(gsb.Server):

	def __init__(self, *args, **kwargs):
		gsb.Server.__init__(self, *args, **kwargs)

		self.challenge = Challenge()
		self.chat = Chat()
		self.db = sqlite3.connect('locale/en/cards.cdb')
		self.db.row_factory = sqlite3.Row
		self.players = {}
		self.session_factory = models.setup()
		self.all_cards = [int(row[0]) for row in self.db.execute("select id from datas where id = alias or alias = 0 order by id asc")]

	def on_connect(self, caller):
		### for backwards compatibility ###
		caller.connection._ = lambda s: caller.connection.player._(s)
		caller.connection.player = None
		caller.connection.session = self.session_factory()
		caller.connection.web = False
		caller.connection.dont_process = False

	def on_disconnect(self, caller):
		con = caller.connection
		if not con.player or not con.player.connection or con.dont_process:
			return
		if con.player.duel is not None and con.player.watching is False:
			# player is in a duel, so we won't disconnect entirely
			for pl in self.get_all_players():
				pl.notify(pl._("%s lost connection while in a duel.")%con.player.nickname)
			con.player.duel.player_disconnected(con.player)
			con.player.detach_connection()
		else:
			if con.player.watching:
				con.player.duel.remove_watcher(con.player)
			elif con.player.room is not None:
				con.player.room.leave(con.player)
			self.remove_player(con.player.nickname)
			for pl in self.get_all_players():
				pl.notify(pl._("%s logged out.") % con.player.nickname)

	def get_player(self, name):
		return self.players.get(name.lower())

	def get_all_players(self):
		return self.players.values()

	def add_player(self, player):
		self.players[player.nickname.lower()] = player
		self.challenge.add_recipient(player)
		self.chat.add_recipient(player)

	def remove_player(self, nick):
		try:
			self.challenge.remove_recipient(self.players[nick.lower()])
			self.chat.remove_recipient(self.players[nick.lower()])
			del(self.players[nick.lower()])
		except KeyError:
			pass

	# me being the caller (we don't want to address me)
	def guess_players(self, name, me):

		name = name[0].upper()+name[1:].lower()
		players = [self.get_player(p) for p in self.players.keys() if (p[0].upper()+p[1:].lower()) != me]
		i = 0

		while i < len(players):
			if players[i].nickname == name:
				# exact match means we will only return that player
				return [players[i]]
			elif players[i].nickname.startswith(name):
				i += 1
				continue
			else:
				del players[i]

		players.sort(key=lambda p: p.nickname)

		return players

	def get_card_by_name(self, pl, name):
		r = re.compile(r'^(\d+)\.(.+)$')
		r = r.search(name)
		if r:
			n, name = int(r.group(1)), r.group(2)
		else:
			n = 1
		if n == 0:
			n = 1
		name = '%'+name+'%'
		rows = pl.cdb.execute('select id from texts where name like ? limit ?', (name, n)).fetchall()
		if not rows:
			return
		nr = rows[min(n - 1, len(rows) - 1)]
		card = Card(nr[0])
		return card

	def check_reboot(self):
		duels = [c.duel for c in self.get_all_players() if c.duel is not None]
		if globals.rebooting and len(duels) == 0:
			for pl in self.get_all_players():
				pl.notify(pl._("Rebooting."))
			reactor.callLater(0.2, reactor.stop)
