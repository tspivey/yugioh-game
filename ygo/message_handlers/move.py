import io

from ygo.card import Card
from ygo.constants import *

def msg_move(self, data):
  data = io.BytesIO(data[1:])
  code = self.read_u32(data)
  location = self.read_u32(data)
  newloc = self.read_u32(data)
  reason = self.read_u32(data)
  self.cm.call_callbacks('move', code, location, newloc, reason)
  return data.read()

def move(self, code, location, newloc, reason):
  card = Card(code)
  card.set_location(location)
  pl = self.players[card.controller]
  op = self.players[1 - card.controller]
  plspec = card.get_spec(pl.duel_player)
  ploc = (location >> 8) & 0xff
  pnewloc = (newloc >> 8) & 0xff
  if reason & 0x01 and ploc != pnewloc:
    pl.notify(pl._("Card %s (%s) destroyed.") % (plspec, card.get_name(pl)))
    for w in self.watchers+[op]:
      s = card.get_spec(w.duel_player)
      w.notify(w._("Card %s (%s) destroyed.") % (s, card.get_name(w)))
  elif ploc == pnewloc and ploc in (LOCATION_MZONE, LOCATION_SZONE):
    cnew = Card(code)
    cnew.set_location(newloc)

    if (location & 0xff) != (newloc & 0xff):
      # controller changed too (e.g. change of heart)
      pl.notify(pl._("your card {spec} ({name}) changed controller to {op} and is now located at {targetspec}.").format(spec=plspec, name = card.get_name(pl), op = op.nickname, targetspec = cnew.get_spec(pl.duel_player)))
      op.notify(op._("you now control {plname}s card {spec} ({name}) and its located at {targetspec}.").format(plname=pl.nickname, spec=self.card_to_spec(op.duel_player, card), name = card.get_name(op), targetspec = cnew.get_spec(op.duel_player)))
      for w in self.watchers:
        s = card.get_spec(w.duel_player)
        ts = cnew.get_spec(w.duel_player)
        w.notify(w._("{plname}s card {spec} ({name}) changed controller to {op} and is now located at {targetspec}.").format(plname=pl.nickname, op=op.nickname, spec=s, targetspec=ts, name=card.get_name(w)))
    else:
      # only place changed (alien decks e.g.)
      pl.notify(pl._("your card {spec} ({name}) switched its zone to {targetspec}.").format(spec=plspec, name=card.get_name(pl), targetspec=cnew.get_spec(pl.duel_player)))
      for w in self.watchers+[op]:
        s = card.get_spec(w.duel_player)
        ts = cnew.get_spec(w.duel_player)
        w.notify(w._("{plname}s card {spec} ({name}) changed its zone to {targetspec}.").format(plname=pl.nickname, spec=s, targetspec=ts, name=card.get_name(w)))
  elif reason & 0x4000 and ploc != pnewloc:
    pl.notify(pl._("you discarded {spec} ({name}).").format(spec = plspec, name = card.get_name(pl)))
    for w in self.watchers+[op]:
      s = card.get_spec(w.duel_player)
      w.notify(w._("{plname} discarded {spec} ({name}).").format(plname=pl.nickname, spec=s, name=card.get_name(w)))
  elif ploc == LOCATION_REMOVED and pnewloc in (LOCATION_SZONE, LOCATION_MZONE):
    cnew = Card(code)
    cnew.set_location(newloc)
    pl.notify(pl._("your banished card {spec} ({name}) returns to the field at {targetspec}.").format(spec=plspec, name=card.get_name(pl), targetspec=cnew.get_spec(pl.duel_player)))
    for w in self.watchers+[op]:
      s=card.get_spec(w.duel_player)
      ts = cnew.get_spec(w.duel_player)
      w.notify(w._("{plname}'s banished card {spec} ({name}) returned to their field at {targetspec}.").format(plname=pl.nickname, spec=s, targetspec=ts, name=card.get_name(w)))
  elif ploc == LOCATION_GRAVE and pnewloc in (LOCATION_SZONE, LOCATION_MZONE):
    cnew = Card(code)
    cnew.set_location(newloc)
    pl.notify(pl._("your card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(spec=plspec, name=card.get_name(pl), targetspec=cnew.get_spec(pl.duel_player)))
    for w in self.watchers+[op]:
      s = card.get_spec(w.duel_player)
      ts = cnew.get_spec(w.duel_player)
      w.notify(w._("{plname}s card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(plname = pl.nickname, spec=s, targetspec=ts, name = card.get_name(w)))
  elif pnewloc == LOCATION_HAND and ploc != pnewloc:
    pl.notify(pl._("Card {spec} ({name}) returned to hand.")
      .format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      if card.position in (POS_FACEDOWN_DEFENSE, POS_FACEDOWN):
        name = w._("Face-down card")
      else:
        name = card.get_name(w)
      s = card.get_spec(w.duel_player)
      w.notify(w._("{plname}'s card {spec} ({name}) returned to their hand.")
        .format(plname=pl.nickname, spec=s, name=name))
  elif reason & 0x12 and ploc != pnewloc:
    pl.notify(pl._("You tribute {spec} ({name}).")
      .format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = card.get_spec(w.duel_player)
      if card.position in (POS_FACEDOWN_DEFENSE, POS_FACEDOWN):
        name = w._("%s card") % card.get_position(w)
      else:
        name = card.get_name(w)
      w.notify(w._("{plname} tributes {spec} ({name}).")
        .format(plname=pl.nickname, spec=s, name=name))
  elif ploc == LOCATION_OVERLAY+LOCATION_MZONE and pnewloc in (LOCATION_GRAVE, LOCATION_REMOVED):
    pl.notify(pl._("you detached %s.")%(card.get_name(pl)))
    for w in self.watchers+[op]:
      w.notify(w._("%s detached %s")%(pl.nickname, card.get_name(w)))
  elif ploc != pnewloc and pnewloc == LOCATION_GRAVE:
    pl.notify(pl._("your card {spec} ({name}) was sent to the graveyard.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = card.get_spec(w.duel_player)
      w.notify(w._("{plname}'s card {spec} ({name}) was sent to the graveyard.").format(plname=pl.nickname, spec=s, name=card.get_name(w)))
  elif ploc != pnewloc and pnewloc == LOCATION_REMOVED:
    pl.notify(pl._("your card {spec} ({name}) was banished.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      if card.position in (POS_FACEDOWN_DEFENSE, POS_FACEDOWN):
        name = w._("Face-down defense")
      else:
        name = card.get_name(w)
      s = card.get_spec(w.duel_player)
      w.notify(w._("{plname}'s card {spec} ({name}) was banished.").format(plname=pl.nickname, spec=s, name=name))
  elif ploc != pnewloc and pnewloc == LOCATION_DECK:
    pl.notify(pl._("your card {spec} ({name}) returned to your deck.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = card.get_spec(w.duel_player)
      w.notify(w._("{plname}'s card {spec} ({name}) returned to their deck.").format(plname=pl.nickname, spec=s, name=card.get_name(w)))
  elif ploc != pnewloc and pnewloc == LOCATION_EXTRA:
    pl.notify(pl._("your card {spec} ({name}) returned to your extra deck.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = card.get_spec(w.duel_player)
      w.notify(w._("{plname}'s card {spec} ({name}) returned to their extra deck.").format(plname=pl.nickname, spec=s, name=card.get_name(w)))

MESSAGES = {50: msg_move}

CALLBACKS = {'move': move}
