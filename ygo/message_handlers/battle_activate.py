from twisted.internet import reactor

from ygo.duel_reader import DuelReader
from ygo.utils import process_duel
from ygo.parsers.duel_parser import DuelParser

def battle_activate(self, pl):
	pln = pl.duel_player
	pl.notify(pl._("Select card to activate:"))
	specs = {}
	for c in self.activatable:
		spec = c.get_spec(pl)
		pl.notify("%s: %s (%d/%d)" % (spec, c.get_name(pl), c.attack, c.defense))
		specs[spec] = c
	pl.notify(pl._("z: back."))
	def r(caller):
		if caller.text == 'z':
			self.display_battle_menu(pl)
			return
		if caller.text not in specs:
			pl.notify(pl._("Invalid cardspec. Retry."))
			pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=DuelParser)
			return
		card = specs[caller.text]
		seq = self.activatable.index(card)
		self.set_responsei((seq << 16))
		reactor.callLater(0, process_duel, self)
	pl.notify(DuelReader, r, no_abort="Invalid command", restore_parser=DuelParser)

METHODS = {'battle_activate': battle_activate}
