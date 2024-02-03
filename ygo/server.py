import re
import socket
import urllib.request

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
		self.soundpack_version = ""
		self.update_soundpack_version()

		self.challenge = Challenge()
		self.chat = Chat()
		self.players = {}
		self.session_factory = models.setup()
		self.max_online = 0

	def update_soundpack_version(self):
		# download our soundpack version file from the server
		response = urllib.request.urlopen("https://raw.githubusercontent.com/JessicaTegner/yugioh-soundpack/master/ygo.ver")
		latest_soundpack_version = response.read()
		if isinstance(latest_soundpack_version, bytes):
			latest_soundpack_version = latest_soundpack_version.decode("utf-8")
		# strip newlines
		latest_soundpack_version = latest_soundpack_version.strip()
		self.soundpack_version = latest_soundpack_version

	def on_connect(self, caller):
		### for backwards compatibility ###
		caller.connection._ = lambda s: caller.connection.player._(s)
		caller.connection.player = None
		caller.connection.session = self.session_factory()
		caller.connection.web = False
		caller.connection.dont_process = False
		caller.connection.transport.setTcpKeepAlive(True)
		if hasattr(socket, "TCP_KEEPIDLE"):
			caller.connection.transport.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 120)

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
			con.session.close()
			for pl in self.get_all_players():
				pl.notify(pl._("%s logged out.") % con.player.nickname)

	def is_banned(self, host):
		session = self.session_factory()
		
		banned = session.query(models.Account).filter_by(ip_address = host, banned = True).all()

		session.close()

		if len(banned) > 0:
			return True
		
		return False

	def get_player(self, name):
		return self.players.get(name.lower())

	def get_all_players(self):
		return self.players.values()

	def add_player(self, player):
		self.players[player.nickname.lower()] = player
		self.challenge.add_recipient(player)
		self.chat.add_recipient(player)
		for l in globals.language_handler.get_available_languages():
			globals.language_handler.get_language(l)['channel'].add_recipient(player)
		if len(self.players) > self.max_online:
			self.max_online = len(self.players)

	def remove_player(self, nick):
		try:
			self.challenge.remove_recipient(self.players[nick.lower()])
			self.chat.remove_recipient(self.players[nick.lower()])
			for l in globals.language_handler.get_available_languages():
				globals.language_handler.get_language(l)['channel'].remove_recipient(self.players[nick.lower()])
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

		if len(duels):
			return

		rooms = [p.room for p in self.get_all_players() if p.room and p.room.match and p.room.duel_count > 0]

		if len(rooms):
			return

		if globals.rebooting:
			self.reboot()

	def reboot(self):
		for pl in self.get_all_players():
			pl.notify(pl._("Rebooting."))
		reactor.callLater(0.2, reactor.stop)

	def handle_localhost_commands(self, caller):
		# shutdown
		if caller.text == 'shutdown':
			globals.rebooting = not globals.rebooting
			if globals.rebooting:
				for pl in self.get_all_players():
					if pl.is_admin:
						pl.notify("Reboot started.")
				caller.connection.notify("Reboot started.")
				self.check_reboot()
			else:
				for pl in self.get_all_players():
					if pl.is_admin:
						pl.notify("Reboot canceled.")
				caller.connection.notify("Reboot canceled.")
			return True

	@property
	def all_cards(self):
		return globals.language_handler.all_primary_cards
