import gsb
import json

from ..card import Card
from ..constants import COMMAND_SUBSTITUTIONS
from .. import globals
from .. import models

class room_parser(gsb.Parser):

	def prompt(self, connection):
		connection.notify(connection._("Enter ? to show all commands and room preferences"))

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

	pl.notify(pl._("The following settings are defined for this room:"))

	pl.notify(pl._("Banlist: %s")%(room.get_banlist()))

	s = pl._("Duel Rules:")+" "

	if room.rules == 4:
		s += pl._("Link")
	elif room.rules == 1:
		s += pl._("Traditional")
	elif room.rules == 0:
		s += pl._("Default")

	pl.notify(s)

	pl.notify(pl._("Privacy: %s")%(pl._("private") if room.private is True else pl._("public")))

	pl.notify(pl._("The following commands are available for you:"))

	if not room.open:
		pl.notify(pl._("banlist - define banlist"))
		pl.notify(pl._("finish - finish room creation and open it to other players"))
		pl.notify(pl._("private - toggles privacy"))
		pl.notify(pl._("rules - define duel rules"))
		pl.notify(pl._("save - saves the current preferences as default for future rooms you create"))

	if room.open:
		pl.notify(pl._("deck - select a deck to duel with"))
		pl.notify(pl._("move - move yourself into a team of your choice"))
		pl.notify(pl._("teams - show teams and associated players"))

		if room.creator is pl:
			pl.notify(pl._("invite - invite player into this room"))
			pl.notify(pl._("start - start duel with current teams"))

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
		for p in globals.server.get_all_players():
			if not pl.nickname in p.ignores:
				globals.server.announce_challenge(p, "%s created a new duel room.")%(pl.nickname))

@RoomParser.command(names=['leave'])
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

		pl.notify(pl._("You can also set the banlist to one of the following:"))
		for k in globals.lflist.keys():
			pl.notify(k)

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

@RoomParser.command(names=['move'], args_regexp=r'([0-2])', allowed = lambda c: c.connection.player.room.open)
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
					p.notify(p._("%s was removed from any team."))
		else:
			for p in room.get_all_players():
				if p is pl:
					pl.notify(pl._("You were moved into %s.")%(pl._("team %d")%(team)))
				else:
					p.notify(p._("%s was moved into %s.")%(p._("team %d")%(team)))

@RoomParser.command(names=['private'])
def private(caller):

	pl = caller.connection.player
	room = pl.room

	room.private = not room.private

	if room.private is True:
		pl.notify(pl._("This room is now private."))
	else:
		pl.notify(pl._("This room is now public."))

@RoomParser.command(names=['rules'], args_regexp=r'([a-zA-Z]+)', allowed = lambda c: c.connection.player.room.creator is c.connection.player and not c.connection.player.room.open)
def rules(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0:
		pl.notify(pl._("Following rules can be defined:"))
		pl.notify(pl._("Default - The default duelling behaviour before link summons came in"))
		pl.notify(pl._("Link - Enable link summons"))
		pl.notify(pl._("Traditional - Duel rules from the first days of Yu-Gi-Oh"))
	elif caller.args[0] is None or caller.args[0].lower() not in ('link', 'default', 'traditional'):
		pl.notify(pl._("Invalid duel rules specified. See rules command to get the possible arguments."))
	else:
		rule = caller.args[0].lower()
		if rule == 'link':
			room.rules = 4
		elif rule == 'traditional':
			room.rules = 1
		else:
			room.rules = 0

		s = pl._("Duel rules were set to %s.")

		if room.rules == 0:
			s2 = pl._("Traditional")
		elif room.rules == 1:
			s2 = pl._("Default")
		elif room.rules == 4:
			s2 = pl._("Link")

		s = s%(s2)

		pl.notify(s)

@RoomParser.command(names=['deck'], args_regexp=r'(.*)', allowed = lambda c: c.connection.player.room.open)
def deck(caller):

	pl = caller.connection.player
	room = pl.room

	if len(caller.args) == 0:
		pl.deck_editor.list()
		return

	name = caller.args[0]

	# first the loading algorithm
	# parsing the string, loading from database
	session = caller.connection.session
	account = caller.connection.account
	if name.startswith('public/'):
		account = session.query(models.Account).filter_by(name='Public').first()
		name = name[7:]
	deck = session.query(models.Deck).filter_by(account_id=account.id, name=name).first()
	if not deck:
		pl.notify(pl._("Deck doesn't exist."))
		session.commit()
		return

	content = json.loads(deck.content)

	# we parsed the deck now we execute several checks
	# we check card limits first
	main, extra = pl.count_deck_cards(content)
	if main < 40 or main > 200:
		pl.notify(pl._("Your main deck must contain between 40 and 200 cards (currently %d).") % main)
		return

	if extra > 15:
		pl.notify(pl._("Your extra deck may not contain more than 15 cards (currently %d).")%extra)
		return

	# check against selected banlist
	codes = set(content['cards'])
	errors = 0
	for code in codes:
		count = content['cards'].count(code)
		if code not in globals.lflist[room.get_banlist()] or count <= globals.lflist[room.get_banlist()][code]:
			continue
		card = Card(code)
		pl.notify(pl._("%s: limit %d, found %d.") % (card.get_name(pl), globals.lflist[room.get_banlist()][code], count))
		errors += 1

	if errors > 0:
		pl.notify(pl._("Check completed with %d errors.") % errors)
		return

	pl.deck = content
	session.commit()
	pl.notify(pl._("Deck loaded with %d cards.") % len(content['cards']))

	for p in room.get_all_players():
		if p is not pl:
			p.notify(p._("%s loaded a deck.")%(pl.nickname))
