import io

from ygo.card import Card
from ygo.constants import *
from ygo.utils import handle_error

def msg_move(self, data):
	data = io.BytesIO(data[1:])
	code = self.read_u32(data)
	location = self.read_u32(data)
	newloc = self.read_u32(data)
	reason = self.read_u32(data)
	self.cm.call_callbacks('move', code, location, newloc, reason)
	return data.read()

@handle_error
def move(self, code, location, newloc, reason):
	card = Card(code)
	card.set_location(location)
	cnew = Card(code)
	cnew.set_location(newloc)
	pl = self.players[card.controller]
	op = self.players[1 - card.controller]
	plspec = card.get_spec(pl)
	opspec = card.get_spec(op)
	plnewspec = cnew.get_spec(pl)
	opnewspec = cnew.get_spec(op)

	getspec = lambda p: plspec if p.duel_player == pl.duel_player else opspec
	getnewspec = lambda p: plnewspec if p.duel_player == pl.duel_player else opnewspec

	card_visible = True
	
	if card.position == cnew.position and card.position in (POS_FACEDOWN, POS_FACEDOWN_DEFENSE):
		card_visible = False

	getvisiblename = lambda p: card.get_name(p) if card_visible else p._("Face-down card")

	if reason & 0x01 and card.location != cnew.location:
		self.inform(
			pl,
			(INFORM.ALLIES, lambda p: p._("Card %s (%s) destroyed.") % (plspec, card.get_name(p))),
			(INFORM.OPPONENTS, lambda p: p._("Card %s (%s) destroyed.") % (opspec, card.get_name(p)))
		)
	elif card.location == cnew.location and card.location in (LOCATION_MZONE, LOCATION_SZONE):
		if card.controller != cnew.controller:
			# controller changed too (e.g. change of heart)
			self.inform(
				pl,
				(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) changed controller to {op} and is now located at {targetspec}.").format(spec=plspec, name = card.get_name(p), op = op.nickname, targetspec = plnewspec)),
				(INFORM.OPPONENT, lambda p: p._("you now control {plname}s card {spec} ({name}) and its located at {targetspec}.").format(plname=pl.nickname, spec=opspec, name = card.get_name(p), targetspec = opnewspec)),
				(INFORM.WATCHERS | INFORM.TAG_PLAYERS, lambda p: w._("{plname}s card {spec} ({name}) changed controller to {op} and is now located at {targetspec}.").format(plname=pl.nickname, op=op.nickname, spec=getspec(p), targetspec=getnewspec(p), name=card.get_name(p))),
			)
		else:
			# only column changed (alien decks e.g.)
			self.inform(
				pl,
				(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) switched its zone to {targetspec}.").format(spec=plspec, name=card.get_name(p), targetspec=plnewspec)),
				(INFORM.OTHER, lambda p: p._("{plname}s card {spec} ({name}) changed its zone to {targetspec}.").format(plname=pl.nickname, spec=getspec(p), targetspec=getnewspec(p), name=card.get_name(p))),
			)
	elif reason & 0x4000 and card.location != cnew.location:
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("you discarded {spec} ({name}).").format(spec = plspec, name = card.get_name(p))),
			(INFORM.OTHER, lambda p: p._("{plname} discarded {spec} ({name}).").format(plname=pl.nickname, spec=getspec(p), name=card.get_name(p))),
		)
	elif card.location == LOCATION_REMOVED and cnew.location in (LOCATION_SZONE, LOCATION_MZONE):
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your banished card {spec} ({name}) returns to the field at {targetspec}.").format(spec=plspec, name=card.get_name(p), targetspec=plnewspec)),
			(INFORM.OTHER, lambda p: p._("{plname}'s banished card {spec} ({name}) returned to their field at {targetspec}.").format(plname=pl.nickname, spec=getspec(p), targetspec=getnewspec(p), name=card.get_name(p))),
		)
	elif card.location == LOCATION_GRAVE and cnew.location in (LOCATION_SZONE, LOCATION_MZONE):
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(spec=plspec, name=card.get_name(p), targetspec=plnewspec)),
			(INFORM.OTHER, lambda p: p._("{plname}s card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(plname = pl.nickname, spec=getspec(p), targetspec=getnewspec(p), name = card.get_name(p))),
		)
	elif cnew.location == LOCATION_HAND and card.location != cnew.location:
		self.inform(
			pl,
			(INFORM.PLAYER | INFORM.TAG_PLAYER, lambda p: p._("Card {spec} ({name}) returned to hand.").format(spec=plspec, name=card.get_name(p))),
			(INFORM.WATCHERS | INFORM.OPPONENTS, lambda p: p._("{plname}'s card {spec} ({name}) returned to their hand.").format(plname=pl.nickname, spec=getspec(p), name=getvisiblename(p))),
		)
	elif reason & 0x12 and card.location != cnew.location:
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("You tribute {spec} ({name}).").format(spec=plspec, name=card.get_name(p))),
			(INFORM.OTHER, lambda p: p._("{plname} tributes {spec} ({name}).").format(plname=pl.nickname, spec=getspec(p), name=getvisiblename(p))),
		)
	elif card.location == LOCATION_OVERLAY+LOCATION_MZONE and cnew.location in (LOCATION_GRAVE, LOCATION_REMOVED):
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("you detached %s.")%(card.get_name(p))),
			(INFORM.OTHER, lambda p: p._("%s detached %s")%(pl.nickname, card.get_name(p))),
		)
	elif card.location != cnew.location and cnew.location == LOCATION_GRAVE:
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) was sent to the graveyard.").format(spec=plspec, name=card.get_name(p))),
			(INFORM.OTHER, lambda p: p._("{plname}'s card {spec} ({name}) was sent to the graveyard.").format(plname=pl.nickname, spec=getspec(p), name=card.get_name(p))),
		)
	elif card.location != cnew.location and cnew.location == LOCATION_REMOVED:
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) was banished.").format(spec=plspec, name=card.get_name(p))),
			(INFORM.OTHER, lambda p: p._("{plname}'s card {spec} ({name}) was banished.").format(plname=pl.nickname, spec=getspec(p), name=getvisiblename(p))),
		)
	elif card.location != cnew.location and cnew.location == LOCATION_DECK:
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) returned to your deck.").format(spec=plspec, name=card.get_name(p))),
			(INFORM.OTHER, lambda p: p._("{plname}'s card {spec} ({name}) returned to their deck.").format(plname=pl.nickname, spec=getspec(p), name=getvisiblename(p))),
		)
	elif card.location != cnew.location and cnew.location == LOCATION_EXTRA:
		self.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) returned to your extra deck.").format(spec=plspec, name=card.get_name(pl))),
			(INFORM.OTHER, lambda p: p._("{plname}'s card {spec} ({name}) returned to their extra deck.").format(plname=pl.nickname, spec=getspec(p), name=card.get_name(p))),
		)

MESSAGES = {50: msg_move}

CALLBACKS = {'move': move}
