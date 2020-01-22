import gsb
import json
import random

from ..card import Card
from ..constants import COMMAND_SUBSTITUTIONS, RE_NICKNAME, __
from ..duel import Duel
from .. import globals
from .. import models
from .. import parser
from ..who_goes_first.decision import Decision
from ..who_goes_first.rps import RPS

class room_parser(parser.Parser):

	def prompt(self, connection):
		room = connection.player.room

		if not room.started:
			connection.notify(connection._("Enter ? to show all commands and room preferences"))

			if connection.player.locked:
				connection.notify(connection._("Don't forget to remove the lock when you are ready. Type lock to do so."))

	def huh(self, caller):
		caller.connection.notify(caller.connection._("This command isn't available right now."))

	def handle_line(self, connection, line):
		super(room_parser, self).handle_line(connection, line)
		if connection.parser is self:
			self.prompt(connection)

	def explain(self, command, connection):
		# we don't want the parser to construct absurd help texts for us
		# but the caller we pass in will probably have very less information available
		c = gsb.Caller(connection, args = [])
		command.func(c)

RoomParser = room_parser(command_substitutions = COMMAND_SUBSTITUTIONS)

@RoomParser.command(names=['?'])
def list(caller):
	pl = caller.connection.player
	room = pl.room

	room.show(pl)

	pl.notify(pl._("The following commands are available for you:"))

	if not room.open:
		pl.notify(pl._("banlist - define banlist"))
		pl.notify(pl._("finish - finish room creation and open it to other players"))
		pl.notify(pl._("lifepoints - set lifepoints per team"))
		pl.notify(pl._("match - toggle match mode on or off"))
		pl.notify(pl._("private - toggles privacy"))
		pl.notify(pl._("rules - define duel rules"))
		pl.notify(pl._("save - save settings for all your future rooms"))

	if room.open:
		pl.notify(pl._("teams - show teams and associated players"))
		if room.duel_count == 0 and not room.started:
			pl.notify(pl._("deck - select a deck to duel with"))
			pl.notify(pl._("move - move yourself into a team of your choice"))
		if room.duel_count > 0 and pl not in room.teams[0] and not room.started:
			pl.notify(pl._("exchange [<maindeck> <sidedeck>] - exchange cards between main deck and side deck"))
			pl.notify(pl._("lock - lock/unlock a room so that the duel cannot be started"))
			pl.notify(pl._("scoop - scoop the next duel"))

		if room.creator is pl and not room.started:
			pl.notify(pl._("invite - invite player into this room"))
			pl.notify(pl._("remove - remove player from this room"))
			pl.notify(pl._("start - start duel with current teams"))

	if room.duel_count == 0 or pl in room.teams[0]:
		if room.creator is pl:
			pl.notify(pl._("leave - leave this room and close it"))
		else:
			pl.notify(pl._("leave - leave this room"))

@RoomParser.command(names=['finish'], allowed = lambda c: not c.connection.player.room.open and c.connection.player.room.creator is c.connection.player)
def finish(caller):

	pl = caller.connection.player
	room = pl.room

	room.open = True

	pl.notify(pl._("You finished the room setup."))

	if room.private is True:
		pl.notify(pl._("You can now invite players to join this room."))
	else:
		pl.notify(pl._("Players can now join this room, or you can invite them to join you."))
		globals.server.challenge.send_message(None, __("{player} created a new duel room."), player = pl.nickname)

@RoomParser.command(names=['leave'], allowed = lambda c: c.connection.player in c.connection.player.room.teams[0] or (not c.connection.player.room.started and c.connection.player.room.duel_count == 0))
def leave(caller):

	pl = caller.connection.player
	room = pl.room

	room.leave(pl)

@RoomParser.command(names=['banlist'], args_regexp=r'([a-zA-Z0-9\.\- ]+)', allowed = lambda c: not c.connection.player.room.open and c.connection.player.room.creator is c.connection.player)
def banlist(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0:
		pl.notify(pl._("You can set the banlist to ocg or tcg, which will automatically select the newest tcg/ocg banlist for you."))

		pl.notify(pl._("You can also set the banlist to none or one of the following:"))
		pl.deck_editor.check(None)

	elif len(caller.args) == 1 and caller.args[0] == None:
		pl.notify(pl._("Invalid banlist specified."))
	else:
		success = room.set_banlist(caller.args[0])
		if success is True:
			pl.notify(pl._("The banlist for this room was set to %s.")%(room.get_banlist()))
		else:
			pl.notify(pl._("This game doesn't know this banlist. Check the banlist command to get all possible arguments to this command."))

@RoomParser.command(names=['teams'], allowed = lambda c: c.connection.player.room.open)
def teams(caller):

	pl = caller.connection.player
	room = pl.room

	for i in (1, 2):
		if len(room.teams[i]) == 0:
			pl.notify(pl._("No players in %s.")%(pl._("team %d")%i))
		else:
			pl.notify(pl._("Players in %s: %s")%(pl._("team %d")%i, ', '.join([p.nickname for p in room.teams[i]])))

	if len(room.teams[0]) == 0:
		pl.notify(pl._("No remaining players in this room."))
	else:
		pl.notify(pl._("Players not yet in a team: %s")%(', '.join([p.nickname for p in room.teams[0]])))

@RoomParser.command(names=['move'], args_regexp=r'([0-2])', allowed = lambda c: c.connection.player.room.open and not c.connection.player.room.started and c.connection.player.room.duel_count == 0)
def move(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0 or len(caller.args) == 1 and caller.args[0] == None:
		pl.notify(pl._("You can move yourself into team 0, 1 or 2, where 0 means that you remove yourself from any team."))
	else:
		team = int(caller.args[0])
		room.move(pl, team)
		if team == 0:
			for p in room.get_all_players():
				if p is pl:
					pl.notify(pl._("You were removed from any team."))
				else:
					p.notify(p._("%s was removed from any team.") % pl.nickname)
		else:
			for p in room.get_all_players():
				if p is pl:
					pl.notify(pl._("You were moved into %s.")%(pl._("team %d")%(team)))
				else:
					p.notify(p._("%s was moved into %s.")%(pl.nickname, p._("team %d")%(team)))

@RoomParser.command(names=['private'], allowed = lambda c: not c.connection.player.room.open and c.connection.player.room.creator is c.connection.player)
def private(caller):

	pl = caller.connection.player
	room = pl.room

	room.private = not room.private

	if room.private is True:
		pl.notify(pl._("This room is now private."))
	else:
		pl.notify(pl._("This room is now public."))

@RoomParser.command(names=['rules'], args_regexp=r'([a-zA-Z0-9]+)', allowed = lambda c: c.connection.player.room.creator is c.connection.player and not c.connection.player.room.open)
def rules(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0:
		pl.notify(pl._("Following rules can be defined:"))
		pl.notify(pl._("MR5 - The new update to the rules that applys since April 1st, 2020 (MR 5 is an unofficial name)"))
		pl.notify(pl._("Link - Enable link summons (Master Rule 4)"))
		pl.notify(pl._("Default - The default duelling behaviour before link summons came in (Master Rule 3, we advise you to use MR 5 over this one)"))
		pl.notify(pl._("Traditional - Duel rules from the first days of Yu-Gi-Oh"))
	elif caller.args[0] is None or caller.args[0].lower() not in ('link', 'default', 'traditional', 'mr5'):
		pl.notify(pl._("Invalid duel rules specified. See rules command to get the possible arguments."))
	else:
		rule = caller.args[0].lower()
		if rule == 'link':
			room.rules = 4
		elif rule == 'traditional':
			room.rules = 1
		elif rule == 'mr5':
			room.rules = 5
		else:
			room.rules = 0 # Shouldn't this be 3 now? A bit unsure, looking at ygocore's code. 0 seems to be working though.

		s = pl._("Duel rules were set to %s.")

		if room.rules == 0:
			s2 = pl._("Default")
		elif room.rules == 1:
			s2 = pl._("Traditional")
		elif room.rules == 4:
			s2 = pl._("Link")
		elif room.rules == 5:
			s2 = pl._("MR 5")

		s = s%(s2)

		pl.notify(s)

@RoomParser.command(names=['deck'], args_regexp=r'(.+)', allowed = lambda c: c.connection.player.room.open and not c.connection.player.room.started and c.connection.player.room.duel_count == 0)
def deck(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0:
		pl.deck_editor.list_public_decks()
		pl.deck_editor.list_decks([])
		return

	name = caller.args[0]

	# first the loading algorithm
	# parsing the string, loading from database
	session = caller.connection.session
	account = pl.get_account()

	player_name = ''
	deck_name = name

	if '/' in deck_name:
		player_name = deck_name.split("/")[0].title()
		deck_name = deck_name[(len(player_name) + 1):]

	if player_name != '':

		if player_name.lower() == pl.nickname.lower():
			pl.notify(pl._("You don't need to mention yourself if you want to use your own deck."))
			return

		account = session.query(models.Account).filter_by(name=player_name).first()

		if not account:
			pl.notify(pl._("Player {0} could not be found.").format(player_name))
			return

		deck = models.Deck.find(session, account, deck_name)

	else:

		deck = models.Deck.find(session, account, deck_name)

	if not deck:
		pl.notify(pl._("Deck doesn't exist or isn't publically available."))
		return

	content = json.loads(deck.content)

	# we parsed the deck now we execute several checks

	# we filter all invalid cards first
	found = False

	invalid_cards = pl.get_invalid_cards_in_deck(content.get('cards', []))

	if invalid_cards:
		content['cards'] = [c for c in content['cards'] if c not in invalid_cards]
		found = True

	invalid_cards = pl.get_invalid_cards_in_deck(content.get('side', []))

	if invalid_cards:
		content['side'] = [c for c in content['side'] if c not in invalid_cards]
		found = True

	if found:
		pl.notify(pl._("Invalid cards were removed from this deck. This usually occurs after the server loading a new database which doesn't know those cards anymore."))

	# we check card limits first
	main, extra = pl.count_deck_cards(content['cards'])
	if main < 40 or main > 60:
		pl.notify(pl._("Your main deck must contain between 40 and 60 cards (currently %d).") % main)
		return

	if extra > 15:
		pl.notify(pl._("Your extra deck may not contain more than 15 cards (currently %d).")%extra)
		return

	if len(content.get('side', [])) > 15:
		pl.notify(pl._("Your side deck may not contain more than 15 cards (currently %d).")%len(content.get('side', [])))
		return

	# check against selected banlist
	if room.get_banlist() != 'none':
		errors = globals.banlists[room.get_banlist()].check_and_resolve(content.get('cards', []) + content.get('side', []))

		for err in errors:
			pl.notify(pl._("%s: limit %d, found %d.") % (err[0].get_name(pl), err[1], err[2]))

		if len(errors) > 0:
			pl.notify(pl._("Check completed with %d errors.") % len(errors))
			return

	pl.deck = content
	pl.notify(pl._("Deck loaded with %d cards.") % len(content['cards']))

	for p in room.get_all_players():
		if p is not pl:
			p.notify(p._("%s loaded a deck.")%(pl.nickname))

@RoomParser.command(names=['start'], allowed = lambda c: c.connection.player.room.creator is c.connection.player and c.connection.player.room.open and not c.connection.player.room.started)
def start(caller):

	pl = caller.connection.player
	room = pl.room

	# do we have an equal amount of players in both teams?

	if len(room.teams[1]) != len(room.teams[2]):
		pl.notify(pl._("Both teams must have the same amount of players."))
		return

	if not 0 < len(room.teams[1]) <= 2:
		pl.notify(pl._("Both teams may only have one or two players."))
		return

	# do all players have decks loaded?
	for p in room.teams[1]+room.teams[2]:
		if len(p.deck['cards']) == 0:
			pl.notify(pl._("%s doesn't have a deck loaded yet.")%(p.nickname))
			return

	# is someone locking the room?
	p_l = [p for p in room.teams[1] + room.teams[2] if p.locked]

	if len(p_l):
		pl.notify(pl._("Players currently locking this room: {0}").format(', '.join([(p.nickname if p is not pl else pl._("you")) for p in p_l])))
		return

	if globals.rebooting and room.duel_count == 0:
		pl.notify(pl._("This server is going to reboot soon, you cannot start a duel right now."))
		return

	# is it a tag duel?
	if len(room.teams[1]) > 1:
		room.options = room.options | 0x20
	else:
		if room.options&0x20 == 0x20:
			room.options = room.options ^ 0x20

	for p in room.get_all_players():
		if p is pl:
			p.notify(p._("You start the duel."))
		else:
			p.notify(p._("%s starts the duel.")%(pl.nickname))

	# decide who will go first
	room.started = True

	if room.decider == 0:
		pl0 = room.teams[1][random.randint(0, len(room.teams[1])-1)]
		pl1 = room.teams[2][random.randint(0, len(room.teams[2])-1)]
	else:
		pl0 = room.teams[room.decider][random.randint(0, len(room.teams[room.decider])-1)]
		pl1 = room.teams[3-room.decider][random.randint(0, len(room.teams[3-room.decider])-1)]

	if room.decider == 0:

		for p in room.get_all_players():
			if p is pl0 or p is pl1:
				p.notify(p._("You need to play rock paper scissors to decide upon who will go first."))
			else:
				p.notify(p._("{0} and {1} will now play rock paper scissors to decide upon who will go first.").format(pl0.nickname, pl1.nickname))
	
		pl0.notify(RPS(pl0, pl1))
		pl1.notify(RPS(pl1, pl0))

	else:
		for p in room.get_all_players():
			if p is pl0:
				p.notify(p._("You've lost the last duel of this match, thus you may decide who'll go first."))
			elif p is pl1:
				p.notify(p._("You've won the last duel of this match, thus your opponent may decide who will go first."))
			else:
				p.notify(p._("{0} lost the last duel of this match and thus may decide who will go first.").format(pl0.nickname))

		pl0.notify(Decision(pl0))

@RoomParser.command(names=['invite'], args_regexp=RE_NICKNAME, allowed = lambda c: c.connection.player.room.creator is c.connection.player and c.connection.player.room.open)
def invite(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0:
		pl.notify(pl._("You can invite any player to join this room. Simply type invite <player> to do so."))
		return

	if caller.args[0] is None:
		pl.notify(pl._("No player with this name found."))
		return

	players = globals.server.guess_players(caller.args[0], pl.nickname)

	if len(players) == 0:
		pl.notify(pl._("No player with this name found."))
		return
	elif len(players)>1:
		pl.notify(pl._("Multiple players match this name: %s")%(', '.join([p.nickname for p in players])))
		return

	target = players[0]

	if target.duel is not None and (target in target.duel.players or target in target.duel.tag_players):
		pl.notify(pl._("This player is already in a duel."))
		return
	elif target.room is not None:
		pl.notify(pl._("This player is already preparing to duel."))
		return
	elif pl.is_ignoring(target):
		pl.notify(pl._("You're ignoring this player."))
		return
	elif target.is_ignoring(pl):
		pl.notify(pl._("This player ignores you."))
		return

	success = room.invite(target)

	if success:

		if target.afk is True:
			pl.notify(pl._("%s is AFK and may not be paying attention.")%(target.nickname))

		target.notify(target._("%s invites you to join his duel room. Type join %s to do so.")%(pl.nickname, pl.nickname))

		pl.notify(pl._("An invitation was sent to %s.")%(target.nickname))

	else:
	
		pl.notify(pl._("{0} already got an invitation to this room.").format(target.nickname))

@RoomParser.command(names=['lifepoints'], args_regexp=r'([1-2]) (\d+)', allowed = lambda c: c.connection.player.room.creator is c.connection.player and not c.connection.player.room.open)
def lifepoints(caller):

	pl = caller.connection.player
	room = pl.room
	
	if len(caller.args) == 0 or caller.args[0] is None or caller.args[1] is None:
		pl.notify(pl._("Usage: lifepoints <team> <lp>"))
		return
	
	room.lp[int(caller.args[0])-1] = int(caller.args[1])
	
	pl.notify(pl._("Lifepoints for %s set to %d.")%(pl._("team %d")%(int(caller.args[0])), room.lp[int(caller.args[0])-1]))

@RoomParser.command(names=['save'], allowed = lambda c: c.connection.player.room.creator is c.connection.player and not c.connection.player.room.open)
def save(caller):

	con = caller.connection
	room = con.player.room
	account = con.player.get_account()
	
	account.banlist = room.banlist
	account.duel_rules = room.rules
	con.session.commit()
	
	con.notify(con._("Settings saved."))

@RoomParser.command(names=["remove"], args_regexp=RE_NICKNAME, allowed = lambda c: c.connection.player.room.creator is c.connection.player and c.connection.player.room.open)
def remove(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0:
		pl.notify(pl._("You can remove any player from this room, except yourself. Type remove <player> to do so."))
		return
	
	if caller.args[0] is None:
		pl.notify(pl._("No player with this name found."))
		return

	players = globals.server.guess_players(caller.args[0], pl.nickname)

	if len(players) == 0:
		pl.notify(pl._("No player with this name found."))
		return
	elif len(players)>1:
		pl.notify(pl._("Multiple players match this name: %s")%(', '.join([p.nickname for p in players])))
		return

	target = players[0]
	
	if target is pl:
		pl.notify(pl._("You cannot remove yourself from this room."))
		return

	if target.room is not pl.room:
		pl.notify(pl._("{0} is currently not in this room.").format(target.nickname))
		return
	
	if (room.started or room.duel_count > 0) and not target in room.teams[0]:
		pl.notify(pl._("You can only remove watchers after starting the duel or match."))
		return

	pl.notify(pl._("You ask {0} friendly to leave this room.").format(target.nickname))

	target.notify(target._("{0} asks you friendly to leave the room.").format(pl.nickname))

	for p in room.get_all_players():
		if p is target or p is pl:
			continue
		p.notify(p._("{0} asks {1} friendly to leave this room.").format(pl.nickname, target.nickname))

	room.leave(target)

@RoomParser.command(names=["match"], allowed = lambda c: c.connection.player.room.creator is c.connection.player and not c.connection.player.room.open)
def match(caller):

	pl = caller.connection.player
	room = pl.room
	
	room.match = not room.match
	
	if room.match:
		pl.notify(pl._("Match mode enabled."))
	else:
		pl.notify(pl._("Match mode disabled."))

@RoomParser.command(names=["exchange"], args_regexp=r'(\d+) (\d+)', allowed = lambda c: c.connection.player.room.open and not c.connection.player.room.started and c.connection.player.room.match)
def exchange(caller):

	pl = caller.connection.player

	if len(pl.deck.get('cards', [])) == 0:
		pl.notify(pl._("You have no deck loaded, so you can't exchange cards between main and side deck yet."))
		return

	if len(caller.args) == 0 or caller.args[0] is None or caller.args[1] is None:
		pl.notify(pl._("Main deck:"))
		pl.deck_editor.list(pl.deck['cards'][:])
		if len(pl.deck.get('side', [])):
			pl.notify(pl._("Side deck:"))
			pl.deck_editor.list(pl.deck['side'][:])
		
		return

	if pl.room.points[0] == 0 and pl.room.points[1] == 0:
		pl.notify(pl._("You can only exchange cards after the first duel of the match ended."))
		return

	if len(pl.deck.get('side', [])) == 0:
		pl.notify(pl._("Your side deck doesn't contain any cards, so you can't exchange cards with your main deck."))
		return
 
	monsters, spells, traps, extra, other = pl.deck_editor.group_sort_cards(pl.deck['cards'][:])
	# this entire thing gets utterly complicated since CPython 3.6+
	main = []
	main += [k for k in monsters.keys()]
	main += [k for k in spells.keys()]
	main += [k for k in traps.keys()]
	main += [k for k in extra.keys()]

	monsters, spells, traps, extra, other = pl.deck_editor.group_sort_cards(pl.deck['side'][:])
	side = []
	side += [k for k in monsters.keys()]
	side += [k for k in spells.keys()]
	side += [k for k in traps.keys()]
	side += [k for k in extra.keys()]

	main_pos = int(caller.args[0]) - 1
	side_pos = int(caller.args[1]) - 1

	main_card = Card(main[main_pos])
	side_card = Card(side[side_pos])

	if main_card.extra != side_card.extra:
		pl.notify(pl._("You can only exchange a card located in the main deck against another card from the main deck and same goes for the extra deck."))
		return

	pl.deck['cards'].remove(main_card.code)
	pl.deck['cards'].append(side_card.code)
	pl.deck['side'].remove(side_card.code)
	pl.deck['side'].append(main_card.code)

	pl.notify(pl._("You exchange {0} from your main deck against {1} from your side deck.").format(main_card.get_name(pl), side_card.get_name(pl)))

@RoomParser.command(names=["lock"], allowed = lambda c: c.connection.player.room.open and c.connection.player not in c.connection.player.room.teams[0])
def lock(caller):

	pl = caller.connection.player
	room = pl.room
	
	pl.locked = not pl.locked
	
	if pl.locked:
		for p in room.get_all_players():
			if p is pl:
				p.notify(p._("You're now locking the room."))
			else:
				p.notify(p._("{0} is now locking the room.").format(pl.nickname))
	else:
		for p in room.get_all_players():
			if p is pl:
				p.notify(p._("You are no longer locking the room."))
			else:
				p.notify(p._("{0} is no longer locking the room.").format(pl.nickname))

@RoomParser.command(names=["scoop"], allowed = lambda c: c.connection.player.room.open and c.connection.player not in c.connection.player.room.teams[0] and c.connection.player.room.duel_count > 0)
def scoop(caller):

	pl = caller.connection.player
	room = pl.room
	
	if pl in room.teams[1]:
		winner = room.teams[2][0]
	else:
		winner = room.teams[1][0]
	
	for p in room.get_all_players():
		if p is pl:
			p.notify(p._("You scooped."))
		else:
			p.notify(p._("%s scooped.")%(pl.nickname))

	room.announce_victory(winner)

	for p in room.get_all_players():
		room.restore(p, already_in_room = True)

	room.process()
