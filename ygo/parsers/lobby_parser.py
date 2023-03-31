from babel.dates import format_timedelta, format_date
import codecs
import collections
import datetime
from gsb.intercept import Reader
import json
import natsort
import os.path
import os.path
from twisted.internet import reactor
from twisted.python import log

from ..constants import *
from ..duel import Duel
from .. import globals
from .. import parser
from ..room import Room
from ..utils import process_duel, process_duel_replay
from ..websockets import start_websocket_server
from .deck_editor_parser import DeckEditorParser
from .duel_parser import DuelParser
from .room_parser import RoomParser
from .. import models

__ = lambda x: x

LobbyParser = parser.Parser(command_substitutions=COMMAND_SUBSTITUTIONS)

@LobbyParser.command(names=['afk'])
def afk(caller):
	conn = caller.connection
	if conn.player.afk is False:
		conn.notify(conn._("You are now AFK."))
		conn.player.afk = True
		return
	else:
		conn.notify(conn._("You are no longer AFK."))
		conn.player.afk = False
		return

@LobbyParser.command(names='deck', args_regexp=r'(.*)', allowed = lambda c: c.connection.player.duel is None and c.connection.player.room is None and c.connection.parser is LobbyParser)
def deck(caller):

	lst = caller.args[0].split(None, 1)
	if not lst:
		caller.connection.parser.handle_line(caller.connection, "help deck")
		return
	cmd = lst[0]
	caller.args = lst[1:]
	if cmd == 'list':
		caller.connection.player.deck_editor.list_decks(selector = DECK.OWNED, name = caller.args[0] if len(caller.args) > 0 else '')
		return

	elif cmd == 'publiclist':
		caller.connection.player.deck_editor.list_decks(selector = DECK.PUBLIC)
		return

	if len(caller.args) == 0:
		caller.connection.notify(caller.connection._("This command requires more information to operate with."))
		return

	if cmd == 'edit':
		caller.connection.player.deck_editor.edit(caller.args[0])
	elif cmd == 'clear':
		caller.connection.player.deck_editor.clear(caller.args[0])
	elif cmd == 'delete':
		caller.connection.player.deck_editor.delete(caller.args[0])
	elif cmd == 'rename':
		caller.connection.player.deck_editor.rename(caller.args[0])
	elif cmd == 'new':
		caller.connection.player.deck_editor.new(caller.args[0])
	elif cmd == 'copy':
		caller.connection.player.deck_editor.copy(caller.args[0])
	elif cmd == 'draw':
		caller.connection.player.deck_editor.draw(caller.args[0])
	elif cmd == 'import':
		caller.connection.player.deck_editor.deck_import(caller.args[0])
	elif cmd == 'export':
		caller.connection.player.deck_editor.deck_export(caller.args[0])
	elif cmd == 'public':
		caller.connection.player.deck_editor.set_public(caller.args[0], True)
	elif cmd == 'private':
		caller.connection.player.deck_editor.set_public(caller.args[0], False)
	elif cmd == 'view':

		pl = caller.connection.player
		session = caller.connection.session
		
		player_name = ''
		deck_name = caller.args[0]
		
		if '/' in deck_name:
			player_name = deck_name.split('/')[0].title()
			deck_name = deck_name[(len(player_name) + 1):]

		if player_name != '':
			if player_name.lower() == caller.connection.player.nickname.lower():
				pl.notify(pl._("You don't need to mention yourself if you want to use your own deck."))
				return

			account = session.query(models.Account).filter_by(name=player_name).first()

			if not account:
				pl.notify(pl._("Player {0} could not be found.").format(player_name))
				return
			
			deck = models.Deck.find_public(session, account, deck_name)

		else:

			account = pl.get_account()
			
			deck = models.Deck.find(session, account, deck_name)

		if not deck:
			pl.notify(pl._("Deck not found."))
			return

		pl.deck_editor.list(json.loads(deck.content)['cards'])

	else:
		caller.connection.notify(caller.connection._("Invalid deck command."))

@LobbyParser.command(names=["chat"], args_regexp=r'(.*)')
def chat(caller):
	text = caller.args[0]
	if not text:
		caller.connection.player.chat = not caller.connection.player.chat
		if caller.connection.player.chat:
			caller.connection.notify(caller.connection._("Chat on."))
		else:
			caller.connection.notify(caller.connection._("Chat off."))
		return
	if not caller.connection.player.chat:
		caller.connection.player.chat = True
		caller.connection.notify(caller.connection._("Chat on."))
	globals.server.chat.send_message(caller.connection.player, text)

@LobbyParser.command(names=["talk"], args_regexp=r'(.*)')
def talk(caller):
	language = caller.args[0]
	text = caller.args[0]
	if not language:
		language = caller.connection.player.language
	else:
		language = language.split(" ")[0].lower()
		if not language in globals.language_handler.get_available_languages():
			language = caller.connection.player.language
		else:
			text = text[len(language)+1:]
	if not text:
		caller.connection.player.toggle_language_chat(language)
		if caller.connection.player.is_language_chat_enabled(language):
			caller.connection.notify(caller.connection._("{language} talk on.").format(language = language[0].upper()+language[1:]))
		else:
			caller.connection.notify(caller.connection._("{language} talk off.").format(language = language[0].upper()+language[1:]))
		return
	if not caller.connection.player.is_language_chat_enabled(language):
		caller.connection.player.enable_language_chat(language)
		caller.connection.notify(caller.connection._("{language} talk on.").format(language = language[0].upper()+language[1:]))
	globals.language_handler.get_language(language)['channel'].send_message(caller.connection.player, text)

@LobbyParser.command(names=['talkhistory'], args_regexp=r'(\w*) ?(\d*)')
def talkhistory(caller):

	if len(caller.args) == 0 or caller.args[0] == '':
		count = 30
		language = caller.connection.player.language
	else:
		try:
			count = int(caller.args[0])
			language = caller.connection.player.language
		except ValueError:
			language = caller.args[0]
			if language not in globals.language_handler.get_available_languages():
				caller.connection.notify(caller.connection._("This language is unknown."))
				return
			if len(caller.args) == 2 and caller.args[1]:
				count = int(caller.args[1])
			else:
				count = 30

	globals.language_handler.get_language(language)['channel'].print_history(caller.connection.player, count)

@LobbyParser.command(names=["say"], args_regexp=r'(.*)', allowed = lambda c: c.connection.player.room is not None or c.connection.player.duel is not None)
def say(caller):
	text = caller.args[0]
	if caller.connection.player.room is not None:
		c = caller.connection.player.room.say
	elif caller.connection.player.duel is not None:
		c = caller.connection.player.duel.say

	if not text:
		caller.connection.player.say = not caller.connection.player.say
		if caller.connection.player.say:
			caller.connection.notify(caller.connection._("Say on."))
		else:
			caller.connection.notify(caller.connection._("Say off."))
		return

	if not caller.connection.player.say:
		caller.connection.player.say = True
		caller.connection.notify(caller.connection._("Say on."))

	c.send_message(caller.connection.player, text)

@LobbyParser.command(names=['who'], args_regexp=r'(.*)')
def who(caller):
	filters = ["duel", "watch", "idle", "prepare"]
	showing = ["duel", "watch", "idle", "prepare"]
	who_output = []
	text = caller.args[0]
	if text:
		showing = []
		text = text.split()
		for s in text:
			if s in filters:
				showing.append(s)
			else:
				caller.connection.notify(caller.connection._("Invalid filter: %s") % s)
				return
	caller.connection.notify(caller.connection._("Online players:"))
	for pl in natsort.natsorted(globals.server.get_all_players(), key=lambda x: x.nickname):
		s = pl.nickname
		if pl.afk is True:
			s += " " + caller.connection._("[AFK]")
		if pl.watching and "watch" in showing:
			if pl.duel.tag is True:
				pl0 = caller.connection._("team %s")%(pl.duel.players[0].nickname+", "+pl.duel.tag_players[0].nickname)
				pl1 = caller.connection._("team %s")%(pl.duel.players[1].nickname+", "+pl.duel.tag_players[1].nickname)
			else:
				pl0 = pl.duel.players[0].nickname
				pl1 = pl.duel.players[1].nickname
			who_output.append(caller.connection._("%s (Watching duel with %s and %s)") %(s, pl0, pl1))
		elif pl.duel and "duel" in showing:
			if pl.duel.tag is True:
				plteam = [pl.duel.players[pl.duel_player], pl.duel.tag_players[pl.duel_player]]
				plopponents = [pl.duel.players[1 - pl.duel_player], pl.duel.tag_players[1 - pl.duel_player]]
				partner = plteam[1 - plteam.index(pl)].nickname
				other = caller.connection._("team %s")%(plopponents[0].nickname+", "+plopponents[1].nickname)
				if pl.duel.private is True:
					who_output.append(caller.connection._("%s (privately dueling %s together with %s")%(pl.nickname, other, partner))
				else:
					who_output.append(caller.connection._("%s (dueling %s together with %s)")%(pl.nickname, other, partner))
			else:
				other = pl.duel.players[1 - pl.duel_player].nickname
				if pl.duel.private is True:
					who_output.append(caller.connection._("%s (privately dueling %s)") %(pl.nickname, other))
				else:
					who_output.append(caller.connection._("%s (dueling %s)") %(pl.nickname, other))
		elif pl.room and pl.room.open and not pl.room.private and "prepare" in showing:
			if pl.room.duel_count > 0:
				who_output.append(caller.connection._("%s (preparing to continue match)")%(pl.nickname))
			else:
				who_output.append(caller.connection._("%s (preparing to duel)")%(pl.nickname))
		elif not pl.duel and not pl.watching:
			if "idle" in showing:
				who_output.append(s)
	for pl in who_output:
		caller.connection.notify(pl)
	online = len(globals.server.get_all_players())
	caller.connection.notify(caller.connection._("%d online, %d max this reboot.") % (online, globals.server.max_online))

@LobbyParser.command(names=['replay'], args_regexp=r'([a-zA-Z0-9_\.:\-,]+)(?:=(\d+))?', allowed=lambda c: c.connection.player.is_admin and c.connection.player.duel is None and c.connection.player.room is None and c.connection.parser is LobbyParser)
def replay(caller):
	with open(os.path.join('duels', caller.args[0])) as fp:
		lines = [json.loads(line) for line in fp]
	if caller.args[1] is not None:
		limit = int(caller.args[1])
	else:
		limit = len(lines)
	for line in lines[:limit]:
		if line['event_type'] == 'start':
			players = line.get('players', [])
			decks = line.get('decks', [[]]*len(players))
			lp = line.get('lp', [8000, 8000])
			for i, pl in enumerate(players):
				p = globals.server.get_player(pl)
				if p is None:
					caller.connection.notify(caller.connection._("%s is not logged in.")%(pl))
					return
				if p.duel is not None:
					caller.connection.notify(caller.connection._("%s is already dueling.")%(p.nickname))
					return
				if p.room is not None:
					caller.connection.player.notify(caller.connection.player._("%s is currently in a duel room.")%(p.nickname))
					return
				players[i] = p
				p.deck = {'cards': decks[i]}
			duel = Duel(line.get('seed', 0))
			duel.add_players(players, shuffle_players = False, shuffle_decks = False)
			duel.set_player_info(0, lp[0])
			duel.set_player_info(1, lp[1])
			duel.start(line.get('options', 0))
		elif line['event_type'] == 'process':
			process_duel_replay(duel)
		elif line['event_type'] == 'set_responsei':
			duel.set_responsei(line['response'])
		elif line['event_type'] == 'set_responseb':
			duel.set_responseb(line['response'].encode('latin1'))
	reactor.callLater(0, process_duel, duel)

@LobbyParser.command(names=['help'], args_regexp=r'(.*)')
def help(caller):
	topic = caller.args[0]
	if not topic:
		topic = "start"
	topic = topic.replace('/', '_').strip()
	caller.connection.notify(caller.connection.player.get_help(topic))

@LobbyParser.command(names=['quit'], allowed = lambda c: c.connection.player.duel is None and c.connection.player.room is None)
def quit(caller):
	caller.connection.notify(caller.connection._("Goodbye."))
	globals.server.disconnect(caller.connection)

@LobbyParser.command(names=['lookup'], args_regexp=r'(.*)')
def lookup(caller):
	name = caller.args[0]
	card = globals.server.get_card_by_name(caller.connection.player, name)
	if not card:
		caller.connection.notify(caller.connection._("No results found."))
		return
	caller.connection.notify(card.get_info(caller.connection.player))

@LobbyParser.command(names='passwd', allowed = lambda c: c.connection.player.duel is None and c.connection.player.room is None and c.connection.parser is LobbyParser)
def passwd(caller):

	session = caller.connection.session
	account = caller.connection.player.get_account()
	new_password = ""
	old_parser = caller.connection.parser
	def r(caller):
		if not account.check_password(caller.text):
			caller.connection.notify(caller.connection._("Incorrect password."))
			return
		caller.connection.notify(Reader, r2, prompt=caller.connection._("New password:"), no_abort=caller.connection._("Invalid command."), restore_parser=old_parser)
	def r2(caller):
		nonlocal new_password
		new_password = caller.text
		if len(new_password) < 6:
			caller.connection.notify(caller.connection._("Passwords must be at least 6 characters."))
			caller.connection.notify(Reader, r2, prompt=caller.connection._("New password:"), no_abort=caller.connection._("Invalid command."), restore_parser=old_parser)
			return
		caller.connection.notify(Reader, r3, prompt=caller.connection._("Confirm password:"), no_abort=caller.connection._("Invalid command."), restore_parser=old_parser)
	def r3(caller):
		if new_password != caller.text:
			caller.connection.notify(caller.connection._("Passwords don't match."))
			return
		account.set_password(caller.text)
		session.commit()
		caller.connection.notify(caller.connection._("Password changed."))
	caller.connection.notify(Reader, r, prompt=caller.connection._("Current password:"), no_abort=caller.connection._("Invalid command."), restore_parser=old_parser)

@LobbyParser.command(names=['language'], args_regexp=r'(.*)')
def language(caller):
	lang = caller.args[0].lower()
	if lang not in globals.language_handler.get_available_languages():
		caller.connection.notify("Usage: language <"+'/'.join(globals.language_handler.get_available_languages())+">")
		return
	caller.connection.player.set_language(lang)
	caller.connection.notify(caller.connection._("Language set."))

@LobbyParser.command(args_regexp=r'(.*)')
def encoding(caller):
	if caller.connection.web:
		caller.connection.notify(caller.connection._("Encoding is not needed when using the web client."))
		return
	try:
		codec = codecs.lookup(caller.args[0])
		if not codec._is_text_encoding or codec.encode('test')[0] != b'test':
			raise LookupError
	except LookupError:
		caller.connection.notify(caller.connection._("Unknown encoding."))
		return
	caller.connection.encode_args = (caller.args[0], 'replace')
	caller.connection.decode_args = (caller.args[0], 'ignore')
	caller.connection.player.get_account().encoding = caller.args[0]
	caller.connection.session.commit()
	caller.connection.notify(caller.connection._("Encoding set."))

@LobbyParser.command(allowed=lambda c: c.connection.player.is_admin)
def restart_websockets(caller):
	if not globals.websocket_server:
		caller.connection.notify(caller.connection._("Websocket server not enabled."))
		return
	caller.connection.notify(caller.connection._("Stopping server..."))
	d = globals.websocket_server.stopListening()
	def stopped(r):
		caller.connection.notify(caller.connection._("Done, restarting."))
		start_websocket_server()
	d.addCallback(stopped)
	d.addErrback(log.err)

@LobbyParser.command(args_regexp=r'(.*)', allowed=lambda c: c.connection.player.is_admin)
def announce(caller):
	if not caller.args[0]:
		caller.connection.notify(caller.connection._("Announce what?"))
		return
	for pl in globals.server.get_all_players():
		pl.notify(pl._("Announcement: %s") % caller.args[0])

@LobbyParser.command(args_regexp=r'(.*)')
def tell(caller):
	args = caller.args[0].split(None, 1)
	if len(args) != 2:
		caller.connection.notify(caller.connection._("Usage: tell <player> <message>"))
		return
	player = args[0]
	players = globals.server.guess_players(player, caller.connection.player.nickname)
	if len(players) == 1:
		player = players[0]
	elif len(players) > 1:
		caller.connection.notify(caller.connection._("Multiple players match this name: %s")%(','.join([p.nickname for p in players])))
		return
	else:
		caller.connection.notify(caller.connection._("That player is not online."))
		return
	# need to handle ignorings here externally, to prevent buffering
	if caller.connection.player.is_ignoring(player):
		caller.connection.notify(caller.connection._("You are ignoring %s.")%(player.nickname))
		return
	elif player.is_ignoring(caller.connection.player):
		caller.connection.notify(caller.connection._("%s is ignoring you.")%(player.nickname))
		return
	if player.afk is True:
		caller.connection.notify(caller.connection._("%s is AFK and may not be paying attention.") %(player.nickname))
	res = player.tell.send_message(caller.connection.player, args[1])
	if res == 1:
		caller.connection.player.tell.send_message(None, args[1], receiving_player = player.nickname)
		player.reply_to = caller.connection.player.nickname

@LobbyParser.command(args_regexp=r'(.*)')
def reply(caller):
	if not caller.args[0]:
		caller.connection.notify(caller.connection._("Usage: reply <message>"))
		return
	if not caller.connection.player.reply_to:
		caller.connection.notify(caller.connection._("No one to reply to."))
		return
	player = globals.server.get_player(caller.connection.player.reply_to)
	if not player:
		caller.connection.notify(caller.connection._("That player is not online."))
		return
	# see above
	if caller.connection.player.is_ignoring(player):
		caller.connection.notify(caller.connection._("You are ignoring %s.")%(player.nickname))
		return
	elif player.is_ignoring(caller.connection.player):
		caller.connection.notify(caller.connection._("%s is ignoring you.")%(player.nickname))
		return
	if player.afk is True:
		caller.connection.notify(caller.connection._("%s is AFK and may not be paying attention.") %(player.nickname))
	res = player.tell.send_message(caller.connection.player, caller.args[0])
	if res == 1:
		caller.connection.player.tell.send_message(None, caller.args[0], receiving_player = player.nickname)
		player.reply_to = caller.connection.player.nickname

@LobbyParser.command
def soundpack_on(caller):
	caller.connection.player.soundpack = True

@LobbyParser.command(args_regexp=r'(.*)', allowed = lambda c: c.connection.player.room is None and c.connection.parser is not DeckEditorParser)
def watch(caller):

	con = caller.connection
	nick = caller.args[0]
	if not nick:
		con.player.watch = not con.player.watch
		if con.player.watch:
			con.notify(con._("Watch notification enabled."))
		else:
			con.notify(con._("Watch notification disabled."))
		return
	if nick == 'stop':
		if not con.player.watching:
			con.notify(con._("You aren't watching a duel."))
			return
		con.player.duel.remove_watcher(con.player)
		return
	players = globals.server.guess_players(nick, con.player.nickname)
	if con.player.duel:
		con.notify(con._("You are already in a duel."))
		return
	elif len(players) > 1:
		con.notify(con._("Multiple players match this name: %s")%(','.join([p.nickname for p in players])))
		return
	elif not len(players):
		con.notify(con._("That player is not online."))
		return
	elif not players[0].duel:
		con.notify(con._("That player is not in a duel."))
		return
	elif players[0].duel.private and not players[0].duel.can_join(con.player):
		con.notify(con._("That duel is private and you don't have an invitation to watch it."))
		return
	players[0].duel.join(con.player)
	players[0].duel.add_watcher(con.player, players[0].duel_player)

@LobbyParser.command(args_regexp=r'(.*)')
def ignore(caller):
	con = caller.connection
	name = caller.args[0]
	if not name:
		con.notify(con._("Ignored accounts:"))
		for account in con.player.get_account().ignores:
			con.notify(account.ignored_account.name)
		return
	name = name.capitalize()
	if name == con.player.nickname.capitalize():
		con.notify(con._("You cannot ignore yourself."))
		return
	account = con.session.query(models.Account).filter_by(name=name).first()
	if not account:
		con.notify(con._("That account doesn't exist. Make sure you enter the full name (no auto-completion for security reasons)."))
		return
	con_account = con.player.get_account()
	ignore = con.session.query(models.Ignore).filter_by(account_id=con_account.id, ignored_account_id=account.id).first()
	if not ignore:
		i = models.Ignore(account_id=con_account.id, ignored_account_id=account.id)
		con_account.ignores.append(i)
		con.notify(con._("Ignoring %s.") % name)
		con.player.ignores.add(name)
	else:
		con_account.ignores.remove(ignore)
		con.notify(con._("Stopped ignoring %s.") % name)
		con.player.ignores.discard(name)
	con.session.commit()

@LobbyParser.command
def challenge(caller):
	con = caller.connection
	con.player.challenge = not con.player.challenge
	if con.player.challenge:
		con.notify(con._("Challenge on."))
	else:
		con.notify(con._("Challenge off."))

@LobbyParser.command(args_regexp=r'(.*)', allowed=lambda c: c.connection.player.is_admin)
def reboot(caller):
	if caller.args[0] == "force":
		return globals.server.reboot()
	globals.rebooting = not globals.rebooting
	if globals.rebooting:
		for pl in globals.server.get_all_players():
			if pl.is_admin:
				pl.notify("Reboot started.")
		globals.server.check_reboot()
	else:
		for pl in globals.server.get_all_players():
			if pl.is_admin:
				pl.notify("Reboot canceled.")

@LobbyParser.command(args_regexp=r'(.*)')
def echo(caller):
	caller.connection.notify(caller.args[0])

@LobbyParser.command(names=['create'], allowed = lambda c: c.connection.player.room is None and c.connection.player.duel is None and c.connection.parser is LobbyParser)
def create(caller):

	pl = caller.connection.player

	if globals.rebooting:
		pl.notify(pl._("This server is going to reboot soon, you cannot create a room right now."))
		return

	r = Room(pl)
	r.join(pl)
	caller.connection.parser.prompt(caller.connection)

@LobbyParser.command(names=['join'], args_regexp=RE_NICKNAME, allowed = lambda c: c.connection.player.room is None and c.connection.player.duel is None and c.connection.parser is LobbyParser)
def join(caller):

	pl = caller.connection.player

	if len(caller.args) == 0:
		pl.notify("Usage: join <player>")
		return

	if caller.args[0] is None:
		pl.notify(pl._("Invalid player name."))
		return

	players = globals.server.guess_players(caller.args[0], pl.nickname)

	if len(players) == 0:
		pl.notify(pl._("This player isn't online."))
		return
	elif len(players) > 1:
		pl.notify(pl._("Multiple players match this name: %s")%(', '.join([p.nickname for p in players])))
		return

	target = players[0]  

	if pl.is_ignoring(target):
		pl.notify(pl._("You're ignoring this player."))
	elif target.is_ignoring(pl):
		pl.notify(pl._("This player ignores you."))
	elif target.duel is not None:
		pl.notify(pl._("This player is currently in a duel."))
	elif target.room is None or target.room.open is not True or (target.room.private is True and not target.room.can_join(pl)):
		pl.notify(pl._("This player currently doesn't prepare to duel or you may not enter the room."))
	elif pl.is_ignoring(target.room.creator):
		pl.notify(pl._("You're currently ignoring %s, who is the owner of this room.")%(target.room.creator.nickname))
	elif target.room.creator.is_ignoring(pl):
		pl.notify(pl._("%s, who is the owner of this room, is ignoring you.")%(target.room.creator.nickname))
	else:
		target.room.join(pl)
		caller.connection.parser.prompt(caller.connection)

@LobbyParser.command(names=['uptime'])
def uptime(caller):

	delta = datetime.datetime.utcnow() - globals.server.started

	caller.connection.notify(caller.connection._("This server has been running for %s.")%(format_timedelta(delta, locale=caller.connection.player.get_locale())))

	if globals.rebooting:
		caller.connection.notify(caller.connection._("This server is going to reboot soon."))

@LobbyParser.command(names=['chathistory'], args_regexp=r'(\d*)')
def chathistory(caller):

	if len(caller.args) == 0 or caller.args[0] == '':
		count = 30
	else:
		count = int(caller.args[0])

	globals.server.chat.print_history(caller.connection.player, count)

@LobbyParser.command(names=['sayhistory'], args_regexp=r'(\d*)', allowed = lambda c: c.connection.player.room is not None or c.connection.player.duel is not None)
def sayhistory(caller):

	if caller.connection.player.room is not None:
		c = caller.connection.player.room.say
	elif caller.connection.player.duel is not None:
		c = caller.connection.player.duel.say
	
	if len(caller.args) == 0 or caller.args[0] == '':
		count = 30
	else:
		count = int(caller.args[0])
	
	c.print_history(caller.connection.player, count)

@LobbyParser.command(names=['challengehistory'], args_regexp=r'(\d*)')
def challengehistory(caller):

	if len(caller.args) == 0 or caller.args[0] == '':
		count = 30
	else:
		count = int(caller.args[0])
	
	globals.server.challenge.print_history(caller.connection.player, count)

@LobbyParser.command(names=['tellhistory'], args_regexp=r'(\d*)')
def tellhistory(caller):

	if len(caller.args) == 0 or caller.args[0] == '':
		count = 30
	else:
		count = int(caller.args[0])
		
	caller.connection.player.tell.print_history(caller.connection.player)

@LobbyParser.command(names=['finger'], args_regexp=RE_NICKNAME)
def finger(caller):

	pl = caller.connection.player
	session = pl.connection.session

	name = caller.args[0]
	name = name[0].upper()+name[1:].lower()
	
	fp = globals.server.get_player(name)
	
	if fp is None:
		account = session.query(models.Account).filter_by(name=name).first()
		if account is None:
			pl.notify(pl._("No player with that name found."))
			return
	else:
		account = fp.get_account(session)

	pl.notify(pl._("Finger report for %s")%(account.name))

	pl.notify(pl._("Created on %s")%(format_date(account.created, format='medium', locale=pl.get_locale())))

	if fp is not None:
		pl.notify(pl._("Currently logged in"))
	else:
		pl.notify(pl._("Last logged in on %s")%(format_date(account.last_logged_in, format='medium', locale=pl.get_locale())))

	stats = account.statistics

	stats = natsort.natsorted(stats, key=lambda s: s.opponent.name)

	if len(stats) != 0:
		pl.notify(pl._("Duel statistics:"))

		for stat in stats:

			pl.notify(pl._("%s - Won: %d, Lost: %d, Drawn: %d")%(stat.opponent.name, stat.win, stat.lose, stat.draw))

		won = sum([s.win for s in stats])
		lost = sum([s.lose for s in stats])
		drawn = sum([s.draw for s in stats])

		pl.notify(pl._("Conclusion - Won: %d, Lost: %d, Drawn: %d")%(won, lost, drawn))

		if won+lost > 0:
			average = float(won)*100/(float(won)+float(lost))

			pl.notify(pl._("%.2f%% Success.")%(average))

	# admin information
	if account.is_admin:
		# tell the player that this is an admin
		pl.notify(pl._("This player is an admin."))
	if pl.is_admin:
		# show language and encoding
		pl.notify(pl._("Admin information:"))
		pl.notify(pl._("Language: %s.")%(account.language))
		pl.notify(pl._("Encoding: %s.")%(account.encoding))
		if account.banned:
			pl.notify(pl._("This account is banned."))
		pl.notify(pl._("IP address: %s.")%(account.ip_address))

@LobbyParser.command(names=["reloadlanguages"], allowed = lambda c: c.connection.player.is_admin)
def reloadlanguages(caller):
	caller.connection.notify(caller.connection._("Reloading languages..."))
	success = globals.language_handler.reload()
	if success == True:
		caller.connection.notify(caller.connection._("Success."))
	else:
		caller.connection.notify(caller.connection._("An error occurred: {error}").format(error = success))

@LobbyParser.command(names=["banlist"], args_regexp=RE_BANLIST + " ?" + RE_BANLIST)
def banlist(caller):

	pl = caller.connection.player
	
	if len(caller.args) == 0 or caller.args[0] is None:

		pl.notify(pl._("The following banlists are available (from newest to oldest):"))

		for k in globals.banlists.keys():
			pl.notify(k)

		return
		
	banlist = caller.args[0].lower()

	diff_list = None
	
	try:
		diff_list = caller.args[1].lower()

		if diff_list not in globals.banlists:
			pl.notify(pl._("Banlist {0} is unknown.").format(diff_list))

	except AttributeError:
		pass

	if banlist not in globals.banlists:
		pl.notify(pl._("Banlist {0} is unknown.").format(banlist))
		return

	if banlist is diff_list:
		pl.notify(pl._("You cannot compare a banlist to itself."))
		return

	if diff_list is None:
		globals.banlists[banlist].show(pl)
	else:
		globals.banlists[banlist].show_diff(globals.banlists[diff_list], pl)

@LobbyParser.command(names=["ban"], args_regexp='(.*)', allowed = lambda c: c.connection.player.is_admin)
def ban(caller):

	session = caller.connection.session
	
	if len(caller.args) == 0 or not caller.args[0].strip():
		banned = session.query(models.Account).filter_by(banned = True).all()

		if len(banned) == 0:
			caller.connection.notify(caller.connection._("No banned players yet."))
			return
		
		caller.connection.notify(caller.connection._("Banned players:"))

		for a in natsort.natsorted(banned, key = lambda a: a.name):
			caller.connection.notify("\t" + a.name.title())

		return
		
	nick = caller.args[0].strip()

	account = session.query(models.Account).filter_by(name=nick.title()).first()
	
	if not account:
		caller.connection.notify(caller.connection._("No account with that name found."))
		return
		
	if account.is_admin:
		caller.connection.notify(caller.connection._("You cannot ban admins. Please remove the admin status first."))
		return

	if account.banned:
		caller.connection.notify(caller.connection._("{player} is already banned.").format(player = account.name.title()))
		return

	account.banned = True

	ip = account.ip_address

	session.commit()
	
	players = globals.server.get_all_players()
	
	players = filter(lambda p: p.get_account().ip_address == ip, players)

	for p in players:
		p.notify(p._("You were banned by {admin}. Only you might know why.").format(admin = caller.connection.player.nickname))
		globals.server.disconnect(p.connection)

	caller.connection.notify(caller.connection._("Ban successful."))

@LobbyParser.command(names=["unban"], args_regexp='(.*)', allowed = lambda c: c.connection.player.is_admin)
def unban(caller):

	session = caller.connection.session
	
	if len(caller.args) == 0 or not caller.args[0].strip():
		caller.connection.notify(caller.connection._("You need to enter a nickname. To see a list ofanned players, use ban."))
		return

	nick = caller.args[0].strip()

	account = session.query(models.Account).filter_by(name=nick.title()).first()
	
	if not account:
		caller.connection.notify(caller.connection._("No account with that name found."))
		return
		
	if not account.banned:
		caller.connection.notify(caller.connection._("{player} is not banned.").format(player = account.name.title()))
		return

	account.banned = False

	session.commit()
	
	caller.connection.notify(caller.connection._("Ban removed."))

@LobbyParser.command(names=["email"], args_regexp='(.*)')
def email(caller):
	session = caller.connection.session
	account = caller.connection.player.get_account()
	if not caller.args or caller.args[0].strip() == '':
		caller.connection.notify(caller.connection._("Your current email address is %s.") % (account.email,))
		session.commit()
		return
	new_email = caller.args[0].strip()
	account.email = new_email
	session.commit()
	caller.connection.notify(caller.connection._("Your new email address is %s.") % (new_email,))


# not the nicest way, but it works
for key in LobbyParser.commands.keys():
	if not key in DeckEditorParser.commands:
		DeckEditorParser.commands[key] = LobbyParser.commands[key]
	if not key in DuelParser.commands:
		DuelParser.commands[key] = LobbyParser.commands[key]
	if not key in RoomParser.commands:
		RoomParser.commands[key] = LobbyParser.commands[key]
