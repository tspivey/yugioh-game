from . import globals

class Room:
	def __init__(self, creator):
		self.open = False
		self.private = False
		self.teams = ([], [], [])
		self.creator = creator
		self.options = 0
		self.rules = 0
		self.banlist = 'tcg'

	def get_all_players(self):
		return self.teams[0]+self.teams[1]+self.teams[2]

	def join(self, player):
		player.set_parser('RoomParser')
		player.room = self
		self.teams[0].append(player)
		for pl in self.get_all_players():
			if pl is player:
				if player is self.creator:
					player.notify(player._("You joined your new room. You need to finish the setup to make it available to the other players."))
				else:
					pl.notify(pl._("You joined %s's room. Use the teams and move command to move yourself into a team, or stay outside of any team to watch the duel."))
			else:
				pl.notify(pl._("%s joined this room."))

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

		player.notify(player._("You left the room."))

		for pl in self.get_all_players():
			pl.notify(pl._("%s left this room."))

		if player is self.creator:
			# closing room entirely
			for pl in self.get_all_players():
				pl.set_parser('LobbyParser')
				pl.room = None
				pl.notify(pl._("The room creator disbanded the room."))

			player.notify(player._("The room was disbanded."))

	def set_banlist(self, list):

		if list.lower() != 'tcg' and list.lower() != 'ocg' and not list.lower() in globals.lflist or self.open:
			return False
		else:
			self.banlist = list.lower()
			return True

	def get_banlist(self):
		if self.banlist == 'tcg':
			# always the newest tcg list
			lst = [l for l in globals.lflist if l.endswith('tcg')]
			return lst[0]
		elif list == 'ocg':
			# always the newest ocg list
			lst = [l for l in globals.lflist.keys() if not l.endswith('tcg')]
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
