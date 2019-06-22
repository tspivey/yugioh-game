from gsb.intercept import Menu

from .decision import Decision

class RPS(Menu):
	def __init__(self, pl, op):

		def select(caller, selection):

			pl = caller.connection.player
			room = pl.room

			pl.rps_selection = selection

			pl.notify(pl._("You choose {0}.").format([pl._("Rock"), pl._("Paper"), pl._("Scissors")][selection-1]))

			if self.op.rps_selection == 0:
				pl.notify(pl._("You now need to wait for {0} to choose.").format(self.op.nickname))
			else:
				for p in room.get_all_players():
					p.notify(p._("Here are the results:"))
					p.notify(p._("{0} has chosen {1}.").format(pl.nickname, [p._("Rock"), p._("Paper"), p._("Scissors")][pl.rps_selection-1]))
					p.notify(p._("{0} has chosen {1}.").format(self.op.nickname, [p._("Rock"), p._("Paper"), p._("Scissors")][self.op.rps_selection-1]))

				if pl.rps_selection == self.op.rps_selection:
					for p in room.get_all_players():
						p.notify(p._("Noone will be the victor this round."))
						if p is pl:
							p.notify(RPS(pl, self.op))
						elif p is self.op:
							p.notify(RPS(self.op, pl))
				else:
					pp = sorted([pl, self.op], key = lambda p: p.rps_selection)

					if pp[0].rps_selection == 1 and pp[1].rps_selection == 3:
						for p in room.get_all_players():
							if p is pp[0]:
								p.notify(p._("Since you've won, you may now choose who will go first."))
							elif p is pp[1]:
								p.notify(p._("You've lost, so you must wait for your opponent to choose if they want to go first."))
							else:
								p.notify(p._("{0} wins and may now choose who will go first.").format(pp[0].nickname))
								
						pp[0].notify(Decision(pp[0]))

					else:

						for p in room.get_all_players():
							if p is pp[1]:
								p.notify(p._("Since you've won, you may now choose who will go first."))
							elif p is pp[0]:
								p.notify(p._("You've lost, so you must wait for your opponent to choose if they want to go first."))
							else:
								p.notify(p._("{0} wins and may now choose who will go first.").format(pp[1].nickname))

						pp[1].notify(Decision(pp[1]))

					del pl.rps_selection
					del self.op.rps_selection

		Menu.__init__(self, pl._("What do you want to choose?"), no_abort = "Invalid option.", persistent=True, restore_parser = pl.connection.parser)

		pl.rps_selection = 0

		self.op = op
		self.item(pl._("Rock"))(lambda c: select(c, 1))
		self.item(pl._("Paper"))(lambda c: select(c, 2))
		self.item(pl._("Scissors"))(lambda c: select(c, 3))

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
