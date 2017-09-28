import gsb

from ..constants import *

DuelParser = gsb.Parser(command_substitutions = COMMAND_SUBSTITUTIONS)

@DuelParser.command(names=['h', 'hand'])
def hand(caller):
  pl = con.connection.player
  if pl.watching:
    return
  pl.duel.show_hand(pl, pl.duel_player)

@DuelParser.command(names=['tab'])
def tab(caller):
  duel = caller.connection.player.duel
  if caller.connection.player.watching:
    caller.connection.notify(caller.connection._("%s's table:") % duel.players[0].nickname)
    duel.show_table(caller.connection.player, caller.connection.duel_player, True)
  else:
    caller.connection.notify(caller.connection._("Your table:"))
    duel.show_table(caller.connection.player, caller.connection.player.duel_player)

@DuelParser.command(names=['tab2'])
def tab2(caller):
  duel = caller.connection.player.duel
  if caller.connection.player.watching:
    caller.connection.notify(caller.connection._("%s's table:") % duel.players[1].nickname)
  else:
    caller.connection.notify(caller.connection._("Opponent's table:"))
  duel.show_table(caller.connection.player, 1 - caller.connection.player.duel_player, True)

@DuelParser.command(names=['grave'])
def grave(caller):
  caller.connection.player.duel.show_cards_in_location(caller.connection.player, caller.connection.player.duel_player, LOCATION_GRAVE)

@DuelParser.command(names=['grave2'])
def grave2(caller):
  caller.connection.player.duel.show_cards_in_location(caller.connection.player, 1 - caller.connection.player.duel_player, LOCATION_GRAVE, True)

@DuelParser.command
def removed(caller):
  caller.connection.player.duel.show_cards_in_location(caller.connection.player, caller.connection.player.duel_player, LOCATION_REMOVED)

@DuelParser.command
def removed2(caller):
  caller.connection.player.duel.show_cards_in_location(caller.connection.player, 1 - caller.connection.player.duel_player, LOCATION_REMOVED, True)

@DuelParser.command(names=['extra'])
def extra(caller):
  caller.connection.player.duel.show_cards_in_location(caller.connection.player, caller.connection.player.duel_player, LOCATION_EXTRA, caller.connection.player.watching)

@DuelParser.command(names=['extra2'])
def extra2(caller):
  caller.connection.player.duel.show_cards_in_location(caller.connection.player, 1 - caller.connection.player.duel_player, LOCATION_EXTRA, True)
