from twisted.internet import reactor

from ygo.duel_reader import DuelReader
from ygo.constants import TYPE_LINK
from ygo.utils import process_duel
from ygo.parsers.duel_parser import DuelParser

def battle_attack(self, pl):
	pln = pl.duel_player
	pl.notify(pl._("Select card to attack with:"))
	specs = {}
	for c in self.attackable:
		spec = c.get_spec(pl)
		if c.type & TYPE_LINK:
			pl.notify(pl._("%s: %s (%d)")%(spec, c.get_name(pl), c.attack))
		else:
			pl.notify("%s: %s (%d/%d)" % (spec, c.get_name(pl), c.attack, c.defense))
		specs[spec] = c
	pl.notify(pl._("z: back."))
	def r(caller):
		if caller.text == 'z':
			self.display_battle_menu(pl)
			return
		if caller.text not in specs:
			pl.notify(pl._("Invalid cardspec. Retry."))
			return self.battle_attack(pl)
		card = specs[caller.text]
		seq = self.attackable.index(card)
		self.set_responsei((seq << 16) + 1)
		reactor.callLater(0, process_duel, self)
	pl.notify(DuelReader, r, no_abort=pl._("Invalid command."), prompt=pl._("Select a card:"), restore_parser=DuelParser)

METHODS = {'battle_attack': battle_attack}
