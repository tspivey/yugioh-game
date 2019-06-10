from .constants import __
from . import globals
from .channels.say import Say

class Room:
	def __init__(self, creator):
		creator_account = creator.get_account()
		self.open = False
		self.private = False
		self.teams = ([], [], [])
		self.creator = creator
		self.options = 0
		self.rules = creator_account.duel_rules
		self.invitations = []
		self.banlist = creator_account.banlist
		self.say = Say()
		self.lp = [8000, 8000]

	def get_all_players(self):
		return self.teams[0]+self.teams[1]+self.teams[2]

	def join(self, player):
		player.set_parser('RoomParser')
		player.room = self
		player.deck = {'cards': []}
		self.teams[0].append(player)
		self.say.add_recipient(player)
		if player.nickname in self.invitations:
			self.invitations.remove(player.nickname)
		for pl in self.get_all_players():
			if pl is player:
				pl.notify(pl._("You joined %s's room. Use the teams and move command to move yourself into a team, or stay outside of any team to watch the duel.")%(self.creator.nickname))
				self.show(pl)
			else:
				pl.notify(pl._("%s joined this room.")%(player.nickname))

	def leave(self, player):

		if player in self.teams[0]:
			self.teams[0].remove(player)
		elif player in self.teams[1]:
			self.teams[1].remove(player)
		elif player in self.teams[2]:
			self.teams[2].remove(player)
		else:
			return

		player.set_parser('LobbyParser')
		player.room = None
		player.deck = {'cards': []}
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

	def set_banlist(self, list):

		if list.lower() != 'tcg' and list.lower() != 'ocg' and list.lower() != 'none' and not list.lower() in globals.lflist or self.open:
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

	def add_invitation(self, pl):

		if pl.nickname in self.invitations:
			return False
		else:
			self.invitations.append(pl.nickname)
			return True

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
