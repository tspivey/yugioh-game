from gsb.intercept import Menu

from .parsers.duel_parser import DuelParser

class DuelMenu(Menu):
	def handle_line(self, con, line):
		con.player.seen_waiting = False
		for s, c in DuelParser.command_substitutions.items():
			if line.startswith(s):
				line = c+" "+line[1:]
				break
		cmd, args = self.split(line)
		if cmd in DuelParser.commands:
			DuelParser.handle_line(con, line)
		else:
			super().handle_line(con, line)
