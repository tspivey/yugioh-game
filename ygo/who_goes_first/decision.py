from gsb.intercept import Menu

class Decision(Menu):
	def __init__(self, pl):

		def decision(caller, first):

			pl = caller.connection.player
			room = pl.room

			team = 1
			
			if pl in room.teams[2]:
				team = 2

			if not first:
				team = 3 - team
			
			for p in room.get_all_players():
				if p is pl:
					if first:
						p.notify(p._("You decide to go first."))
					else:
						p.notify(p._("You decide to go second."))
				else:
					if first:
						p.notify(p._("{0} decides to go first.").format(pl.nickname))
					else:
						p.notify(p._("{0} decides to go second.").format(pl.nickname))

			room.start_duel(team)

		Menu.__init__(self, pl._("Do you want to go first?"), no_abort = "Invalid option.", persistent=True, restore_parser = pl.connection.parser)

		self.item(pl._("Yes"))(lambda c: decision(c, True))
		self.item(pl._("No"))(lambda c: decision(c, False))

	def handle_line(self, con, line):
		for s, c in self.restore_parser.command_substitutions.items():
			if line.startswith(s):
				line = c+" "+line[1:]
				break
		cmd, args = self.split(line)
		if cmd in self.restore_parser.commands:
			self.restore_parser.handle_line(con, line)
			con.notify(self)
		else:
			super().handle_line(con, line)
