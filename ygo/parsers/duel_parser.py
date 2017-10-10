import gsb

from ..constants import *

DuelParser = gsb.Parser(command_substitutions = COMMAND_SUBSTITUTIONS)

@DuelParser.command(names=['h', 'hand'])
def hand(caller):
	pl = caller.connection.player
	if pl.watching:
		return
	pl.duel.show_hand(pl, pl.duel_player)

@DuelParser.command(names=['tab'])
def tab(caller):
	duel = caller.connection.player.duel
	if caller.connection.player.watching:
		caller.connection.notify(caller.connection._("%s's table:") % duel.players[0].nickname)
		duel.show_table(caller.connection.player, caller.connection.player.duel_player, True)
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

@DuelParser.command(names=['watchers'])
def show_watchers(caller):
	if caller.connection.player.duel.watchers==[]:
		caller.connection.notify(caller.connection._("No one is watching this duel."))
	else:
		caller.connection.notify(caller.connection._("People watching this duel:"))
		for pl in sorted(caller.connection.player.duel.watchers, key=lambda x: x.nickname):
			caller.connection.notify(pl.nickname)

@DuelParser.command(names=['info'], args_regexp=r'(.*)')
def info(caller):
	caller.connection.player.duel.show_info_cmd(caller.connection.player, caller.args[0])

@DuelParser.command(names=['giveup'])
def giveup(caller):

	duel = caller.connection.player.duel

	for pl in duel.players+duel.watchers:
		pl.notify(pl._("%s has ended the duel.")%(caller.connection.player.nickname))

	duel.end()

	if not duel.private:
		for pl in globals.server.get_all_players():
			globals.server.announce_challenge(pl, pl._("%s has cowardly submitted to %s.")%(caller.connection.player.nickname, duel.players[1 - caller.connection.player.duel_player].nickname))
