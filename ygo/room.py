import random

from .constants import __
from .duel import Duel, DUEL_AVAILABLE
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

	def get_all_players(self):
		return self.teams[0]+self.teams[1]+self.teams[2]

	def join(self, player):

		success = Joinable.join(self, player)

		if not self.creator is player and self.private and not success:
			return

		player.set_parser('RoomParser')
		player.room = self
		player.deck = {'cards': [], 'side': []}
		self.teams[0].append(player)
		self.say.add_recipient(player)
		for pl in self.get_all_players():
			if pl is player:
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

		player.set_parser('LobbyParser')
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
				pl.room = None
				pl.deck = {'cards': []}
				self.say.remove_recipient(pl)

				pl.notify(pl._("The room creator disbanded the room."))

			player.notify(player._("The room was disbanded."))

			if self.open and not self.private:
				globals.server.challenge.send_message(None, __("{player} disbanded their duel room."), player = player.nickname)

			return
			
		if self.started and abort:
			self.started = False
			for pl in self.get_all_players():
				pl.notify(pl._("Duel aborted."))
				pl.set_parser('RoomParser')
				
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

		pl.notify(s)

		pl.notify(pl._("Lifepoints - %s: %d, %s: %d")%(pl._("team %d")%(1), self.lp[0], pl._("team %d")%(2), self.lp[1]))

		pl.notify(pl._("Privacy: %s")%(pl._("private") if self.private is True else pl._("public")))

		if self.match:
			pl.notify(pl._("Match mode enabled"))
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
