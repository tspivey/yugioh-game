import random

from .constants import __
from .duel import Duel, DUEL_AVAILABLE
from .duel_reader import DuelReader
from . import globals
from .channels.say import Say
from .invite.joinable import Joinable

class Room(Joinable):
	def __init__(self, creator):
		Joinable.__init__(self)
		creator_account = creator.get_account()
		self.open = False
		self.private = False
		self.teams = ([], [], [])
		self.creator = creator
		self.options = 0
		self.rules = creator_account.duel_rules
		self.banlist = creator_account.banlist
		self.say = Say()
		self.started = False
		self.match = False
		self.lp = [8000, 8000]
		self.points = [0, 0]
		self.duel_count = 0
		self.decider = 0

	def get_all_players(self):
		return self.teams[0]+self.teams[1]+self.teams[2]

	def join(self, player):

		success = Joinable.join(self, player)

		if not self.creator is player and self.private and not success:
			return

		player.set_parser('RoomParser')
		player.locked = False
		player.room = self
		player.deck = {'cards': [], 'side': []}
		self.teams[0].append(player)
		self.say.add_recipient(player)
		for pl in self.get_all_players():
			if pl is player:
				if self.duel_count > 0:
					pl.notify(pl._("You joined %s's room. The match however started already, thus you can only watch the following duels.")%(self.creator.nickname))
				else:
					pl.notify(pl._("You joined %s's room. Use the teams and move command to move yourself into a team, or stay outside of any team to watch the duel.")%(self.creator.nickname))
				self.show(pl)
			else:
				pl.notify(pl._("%s joined this room.")%(player.nickname))

	def leave(self, player):

		abort = True

		if player in self.teams[0]:
			self.teams[0].remove(player)
			abort = False
		elif player in self.teams[1]:
			self.teams[1].remove(player)
		elif player in self.teams[2]:
			self.teams[2].remove(player)
		else:
			return

		if player.connection:
			player.set_parser('LobbyParser')
		player.locked = False
		player.room = None
		player.deck = {'cards': [], 'side': []}
		self.say.remove_recipient(player)

		player.notify(player._("You left the room."))

		for pl in self.get_all_players():
			pl.notify(pl._("%s left this room.") % player.nickname)

		if player is self.creator:
			# closing room entirely
			for pl in self.get_all_players():
				pl.set_parser('LobbyParser')
				pl.locked = False
				pl.room = None
				pl.deck = {'cards': [], 'side': []}
				self.say.remove_recipient(pl)

				pl.notify(pl._("The room creator disbanded the room."))

			player.notify(player._("The room was disbanded."))

			if self.open and not self.private:
				globals.server.challenge.send_message(None, __("{player} disbanded their duel room."), player = player.nickname)

			return
			
		if (self.started or self.duel_count > 0) and abort:
			self.duel_count = 0
			self.points = [0, 0]
			self.started = False
			for pl in self.get_all_players():
				pl.notify(pl._("Duel aborted."))
				pl.locked = False
				pl.deck = {'cards': [], 'side': []}
				pl.set_parser('RoomParser')

			globals.server.check_reboot()
				
	def set_banlist(self, list):

		if list.lower() != 'tcg' and list.lower() != 'ocg' and list.lower() != 'none' and not list.lower() in globals.banlists or self.open:
			return False
		else:
			self.banlist = list.lower()
			return True

	def get_banlist(self):
		if self.banlist == 'tcg':
			# always the newest tcg list
			lst = [l for l in globals.banlists if l.endswith('tcg')]
			return lst[0]
		elif self.banlist == 'ocg':
			# always the newest ocg list
			lst = [l for l in globals.banlists.keys() if not l.endswith('tcg')]
			return lst[0]
		else:
			return self.banlist

	def move(self, player, team):

		if player in self.teams[0]:
			self.teams[0].remove(player)
		elif player in self.teams[1]:
			self.teams[1].remove(player)
		elif player in self.teams[2]:
			self.teams[2].remove(player)
		else:
			return

		self.teams[team].append(player)

		if team == 0:
			player.locked = False

	def show(self, pl):
		pl.notify(pl._("The following settings are defined for this room:"))

		pl.notify(pl._("Banlist: %s")%(self.get_banlist()))

		s = pl._("Duel Rules:")+" "

		if self.rules == 4:
			s += pl._("Link")
		elif self.rules == 1:
			s += pl._("Traditional")
		elif self.rules == 0:
			s += pl._("Default")
		elif self.rules == 5:
			s += pl._("MR 5")

		pl.notify(s)

		pl.notify(pl._("Lifepoints - %s: %d, %s: %d")%(pl._("team %d")%(1), self.lp[0], pl._("team %d")%(2), self.lp[1]))

		pl.notify(pl._("Privacy: %s")%(pl._("private") if self.private is True else pl._("public")))

		if self.match:
			pl.notify(pl._("Match mode enabled."))

			pl.notify(pl._("Team 1 score: {0}").format(self.points[0]))
			pl.notify(pl._("Team 2 score: {0}").format(self.points[1]))
		else:
			pl.notify(pl._("Match mode disabled."))

	def start_duel(self, start_team):

		if DUEL_AVAILABLE:
			random.shuffle(self.teams[1])
			random.shuffle(self.teams[2])
			duel = Duel()
			duel.add_players(self.teams[start_team]+self.teams[3-start_team], shuffle_players=False)
			duel.set_player_info(0, self.lp[0])
			duel.set_player_info(1, self.lp[1])
			duel.room = self

			if not self.private:
				if duel.tag is True:
					pl0 = "team "+duel.players[0].nickname+", "+duel.tag_players[0].nickname
					pl1 = "team "+duel.players[1].nickname+", "+duel.tag_players[1].nickname
				else:
					pl0 = duel.players[0].nickname
					pl1 = duel.players[1].nickname
				globals.server.challenge.send_message(None, __("The duel between {player1} and {player2} has begun!"), player1 = pl0, player2 = pl1)

			duel.start(((self.rules&0xff)<<16)+(self.options&0xffff))

			duel.private = self.private

			# move all 	players without a team into the duel as watchers
			for p in self.teams[0]:
				duel.add_watcher(p)

			# remove the room from all players
			for p in self.get_all_players():
				self.say.remove_recipient(p)
				p.room = None

		else:
			self.started = False
			for p in self.get_all_players():
				p.notify(p._("Duels aren't available right now."))

	# restore this room to a specific player
	# called by every duel after the duel finished
	def restore(self, pl, already_in_room = False):
		if pl.connection is None:
			for opl in globals.server.get_all_players():
				opl.notify(opl._("%s logged out.")%(pl.nickname))
			self.leave(pl)
			globals.server.remove_player(pl.nickname)
		else:
			if isinstance(pl.connection.parser, DuelReader):
				pl.connection.parser.done = lambda caller: None
		if self.disbandable:
			if pl.connection:
				pl.room = None
				pl.set_parser('LobbyParser')
		else:
			if not already_in_room and pl.connection:
				pl.set_parser('RoomParser')
				pl.room = self
				self.say.add_recipient(pl)

				if not pl in self.teams[0]:
					pl.locked = True

	# called by every duel after all players were restored
	def process(self):
		if self.disbandable:
			for pl in self.teams[1] + self.teams[2]:
				pl.deck = {'cards': [], 'side': []}
			globals.server.check_reboot()
		else:
			self.started = False
			self.duel_count += 1

			for pl in self.get_all_players():
				if pl in self.teams[0]:
					pl.notify(pl._("You're now waiting for all players to get ready for their next duel."))
				else:
					pl.notify(pl._("You are now preparing for your next duel."))
				pl.connection.parser.prompt(pl.connection)

	def announce_draw(self):
		self.points[0] += 1
		self.points[1] += 1
		self.decider = 0

		if self.disbandable:
			self.inform()
	
	def announce_victory(self, pl, announce = True):
		if pl in self.teams[1]:
			self.points[0] += 1
			self.decider = 2
		else:
			self.points[1] += 1
			self.decider = 1
			
		if self.disbandable:
			self.inform(announce)

	def announce_giveup(self, pl):

		if self.private:
			return

		duel = pl.duel

		if self.tag is True:
			op = "team "+duel.players[1 - pl.duel_player].nickname+", "+duel.tag_players[1 - pl.duel_player].nickname
		else:
			op = duel.players[1 - pl.duel_player].nickname
		globals.server.challenge.send_message(None, __("{player1} has cowardly submitted to {player2}."), player1 = pl.nickname, player2 = op)

		for p1 in self.teams[1]:
			for p2 in self.teams[2]:
				p1.giveup_against(p2)
				p2.giveup_against(p1)

	# informs players globally and handles statistics
	def inform(self, announce = True):
		if self.points[0] == self.points[1]:
			if self.tag is True:
				pl0 = "team "+self.teams[1][0].nickname+", "+self.teams[1][1].nickname
				pl1 = "team "+self.teams[2][0].nickname+", "+self.teams[2][1].nickname
			else:
				pl0 = self.teams[1][0].nickname
				pl1 = self.teams[2][0].nickname
			if not self.private:
				if announce:
					globals.server.challenge.send_message(None, __("{player1} and {player2} ended up in a draw."), player1 = pl0, player2 = pl1)
				self.teams[1][0].draw_against(self.teams[2][0])
				self.teams[2][0].draw_against(self.teams[1][0])
				if self.tag is True:
					self.teams[1][0].draw_against(self.teams[2][1])
					self.teams[1][1].draw_against(self.teams[2][0])
					self.teams[1][1].draw_against(self.teams[2][1])
					self.teams[2][0].draw_against(self.teams[1][1])
					self.teams[2][1].draw_against(self.teams[1][0])
					self.teams[2][1].draw_against(self.teams[1][1])

			return

		if self.points[0] > self.points[1]:
			winners = self.teams[1][:]
			losers = self.teams[2][:]
		else:
			winners = self.teams[2][:]
			losers = self.teams[1][:]

		if not self.private:
			for w in winners:
				for l in losers:
					w.win_against(l)
			for l in losers:
				for w in winners:
					l.lose_against(w)

		if not self.private and announce:
			if self.tag is True:
				w = "team "+winners[0].nickname+", "+winners[1].nickname
				l = "team "+losers[0].nickname+", "+losers[1].nickname
			else:
				w = winners[0].nickname
				l = losers[0].nickname
			if self.match:
				globals.server.challenge.send_message(None, __("{winner} won the match between {player1} and {player2}."), winner = w, player1 = w, player2 = l)
			else:
				globals.server.challenge.send_message(None, __("{winner} won the duel between {player1} and {player2}."), winner = w, player1 = w, player2 = l)

	# returns True if the room can be disbanded
	# either because its only ment for one duel
	# or because the match ended
	@property
	def disbandable(self):
		if not self.match:
			return True
		if self.duel_count == 2:
			return True
		if self.duel_count >= 1 and abs(self.points[0] - self.points[1]) > 0:
			return True
		return False

	@property
	def tag(self):
		if len(self.teams[1]) == 2 and len(self.teams[2]) == 2:
			return True
		return False
