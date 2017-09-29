def move(self, code, location, newloc, reason):
  card = dm.Card.from_code(code)
  card.set_location(location)
  pl = self.players[card.controller]
  op = self.players[1 - card.controller]
  plspec = self.card_to_spec(pl.duel_player, card)
  ploc = (location >> 8) & 0xff
  pnewloc = (newloc >> 8) & 0xff
  if reason & 0x01 and ploc != pnewloc:
    pl.notify(pl._("Card %s (%s) destroyed.") % (plspec, card.get_name(pl)))
    for w in self.watchers+[op]:
      s = self.card_to_spec(w.duel_player, card)
      w.notify(w._("Card %s (%s) destroyed.") % (s, card.get_name(w)))
  elif ploc == pnewloc and ploc in (dm.LOCATION_MZONE, dm.LOCATION_SZONE):
    cnew = dm.Card.from_code(code)
    cnew.set_location(newloc)

    if (location & 0xff) != (newloc & 0xff):
      # controller changed too (e.g. change of heart)
      pl.notify(pl._("your card {spec} ({name}) changed controller to {op} and is now located at {targetspec}.").format(spec=plspec, name = card.get_name(pl), op = op.nickname, targetspec = self.card_to_spec(pl.duel_player, cnew)))
      op.notify(op._("you now control {plname}s card {spec} ({name}) and its located at {targetspec}.").format(plname=pl.nickname, spec=self.card_to_spec(op.duel_player, card), name = card.get_name(op), targetspec = self.card_to_spec(op.duel_player, cnew)))
      for w in self.watchers:
        s = self.card_to_spec(w.duel_player, card)
        ts = self.card_to_spec(w.duel_player, cnew)
        w.notify(w._("{plname}s card {spec} ({name}) changed controller to {op} and is now located at {targetspec}.").format(plname=pl.nickname, op=op.nickname, spec=s, targetspec=ts, name=card.get_name(w)))
    else:
      # only place changed (alien decks e.g.)
      pl.notify(pl._("your card {spec} ({name}) switched its zone to {targetspec}.").format(spec=plspec, name=card.get_name(pl), targetspec=self.card_to_spec(pl.duel_player, cnew)))
      for w in self.watchers+[op]:
        s = self.card_to_spec(w.duel_player, card)
        ts = self.card_to_spec(w.duel_player, cnew)
        w.notify(w._("{plname}s card {spec} ({name}) changed its zone to {targetspec}.").format(plname=pl.nickname, spec=s, targetspec=ts, name=card.get_name(w)))
  elif reason & 0x4000 and ploc != pnewloc:
    pl.notify(pl._("you discarded {spec} ({name}).").format(spec = plspec, name = card.get_name(pl)))
    for w in self.watchers+[op]:
      s = self.card_to_spec(w.duel_player, card)
      w.notify(w._("{plname} discarded {spec} ({name}).").format(plname=pl.nickname, spec=s, name=card.get_name(w)))
  elif ploc == dm.LOCATION_REMOVED and pnewloc in (dm.LOCATION_SZONE, dm.LOCATION_MZONE):
    cnew = dm.Card.from_code(code)
    cnew.set_location(newloc)
    pl.notify(pl._("your banished card {spec} ({name}) returns to the field at {targetspec}.").format(spec=plspec, name=card.get_name(pl), targetspec=self.card_to_spec(pl.duel_player, cnew)))
    for w in self.watchers+[op]:
      s=self.card_to_spec(w.duel_player, card)
      ts = self.card_to_spec(w.duel_player, cnew)
      w.notify(w._("{plname}'s banished card {spec} ({name}) returned to their field at {targetspec}.").format(plname=pl.nickname, spec=s, targetspec=ts, name=card.get_name(w)))
  elif ploc == dm.LOCATION_GRAVE and pnewloc in (dm.LOCATION_SZONE, dm.LOCATION_MZONE):
    cnew = dm.Card.from_code(code)
    cnew.set_location(newloc)
    pl.notify(pl._("your card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(spec=plspec, name=card.get_name(pl), targetspec=self.card_to_spec(pl.duel_player, cnew)))
    for w in self.watchers+[op]:
      s = self.card_to_spec(w.duel_player, card)
      ts = self.card_to_spec(w.duel_player, cnew)
      w.notify(w._("{plname}s card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(plname = pl.nickname, spec=s, targetspec=ts, name = card.get_name(w)))
  elif pnewloc == dm.LOCATION_HAND and ploc != pnewloc:
    pl.notify(pl._("Card {spec} ({name}) returned to hand.")
      .format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      if card.position in (dm.POS_FACEDOWN_DEFENSE, dm.POS_FACEDOWN):
        name = w._("Face-down card")
      else:
        name = card.get_name(w)
      s = self.card_to_spec(w.duel_player, card)
      w.notify(w._("{plname}'s card {spec} ({name}) returned to their hand.")
        .format(plname=pl.nickname, spec=s, name=name))
  elif reason & 0x12 and ploc != pnewloc:
    pl.notify(pl._("You tribute {spec} ({name}).")
      .format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = self.card_to_spec(w.duel_player, card)
      if card.position in (dm.POS_FACEDOWN_DEFENSE, dm.POS_FACEDOWN):
        name = w._("%s card") % card.get_position(w)
      else:
        name = card.get_name(w)
      w.notify(w._("{plname} tributes {spec} ({name}).")
        .format(plname=pl.nickname, spec=s, name=name))
  elif ploc == dm.LOCATION_OVERLAY+dm.LOCATION_MZONE and pnewloc in (dm.LOCATION_GRAVE, dm.LOCATION_REMOVED):
    pl.notify(pl._("you detached %s.")%(card.get_name(pl)))
    for w in self.watchers+[op]:
      w.notify(w._("%s detached %s")%(pl.nickname, card.get_name(w)))
  elif ploc != pnewloc and pnewloc == dm.LOCATION_GRAVE:
    pl.notify(pl._("your card {spec} ({name}) was sent to the graveyard.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = self.card_to_spec(w.duel_player, card)
      w.notify(w._("{plname}'s card {spec} ({name}) was sent to the graveyard.").format(plname=pl.nickname, spec=s, name=card.get_name(w)))
  elif ploc != pnewloc and pnewloc == dm.LOCATION_REMOVED:
    pl.notify(pl._("your card {spec} ({name}) was banished.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      if card.position in (dm.POS_FACEDOWN_DEFENSE, dm.POS_FACEDOWN):
        name = w._("Face-down defense")
      else:
        name = card.get_name(w)
      s = self.card_to_spec(w.duel_player, card)
      w.notify(w._("{plname}'s card {spec} ({name}) was banished.").format(plname=pl.nickname, spec=s, name=name))
  elif ploc != pnewloc and pnewloc == dm.LOCATION_DECK:
    pl.notify(pl._("your card {spec} ({name}) returned to your deck.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = self.card_to_spec(w.duel_player, card)
      w.notify(w._("{plname}'s card {spec} ({name}) returned to their deck.").format(plname=pl.nickname, spec=s, name=card.get_name(w)))
  elif ploc != pnewloc and pnewloc == dm.LOCATION_EXTRA:
    pl.notify(pl._("your card {spec} ({name}) returned to your extra deck.").format(spec=plspec, name=card.get_name(pl)))
    for w in self.watchers+[op]:
      s = self.card_to_spec(w.duel_player, card)
      w.notify(w._("{plname}'s card {spec} ({name}) returned to their extra deck.").format(plname=pl.nickname, spec=s, name=card.get_name(w)))
