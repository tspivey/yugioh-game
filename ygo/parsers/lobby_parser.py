import codecs
import gsb
import json
import natsort
import os.path
from twisted.internet import reactor
from twisted.python import log

from ..constants import *
from ..duel import Duel
from .. import globals
from ..room import Room
from ..utils import process_duel, process_duel_replay
from ..websockets import start_websocket_server
from .duel_parser import DuelParser
from .room_parser import RoomParser

LobbyParser = gsb.Parser(command_substitutions=COMMAND_SUBSTITUTIONS)

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

@LobbyParser.command(names='deck', args_regexp=r'(.*)', allowed = lambda c: c.connection.player.duel is None and c.connection.player.room is None)
def deck(caller):

	lst = caller.args[0].split(None, 1)
	cmd = lst[0]
	caller.args = lst[1:]
	if cmd == 'list':
		caller.connection.player.deck_editor.list()
		return
	elif cmd == 'check':
		if len(caller.args) == 0:
			caller.connection.player.deck_editor.check()
		else:
			caller.connection.player.deck_editor.check(caller.args[0])
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
	for pl in globals.server.get_all_players():
		if pl.chat and caller.connection.player.nickname not in pl.ignores:
			pl.notify(pl._("%s chats: %s") % (caller.connection.player.nickname, caller.args[0]))

@LobbyParser.command(names=["say"], args_regexp=r'(.*)')
def say(caller):
	text = caller.args[0]
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
	if not caller.connection.player.duel:
		caller.connection.notify(caller.connection._("Not in a duel."))
		return
	for pl in caller.connection.player.duel.players + caller.connection.player.duel.watchers:
		if caller.connection.player.nickname not in pl.ignores and pl.say:
			pl.notify(pl._("%s says: %s") % (caller.connection.player.nickname, caller.args[0]))

@LobbyParser.command(names=['who'], args_regexp=r'(.*)')
def who(caller):
	filters = ["duel", "watch", "idle", '"prepare"]
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
			pl0 = pl.duel.players[0].nickname
			pl1 = pl.duel.players[1].nickname
			who_output.append(caller.connection._("%s (Watching duel with %s and %s)") %(s, pl0, pl1))
		elif pl.duel and "duel" in showing:
			other = None
			if pl.duel.players[0] is pl:
				other = pl.duel.players[1]
			else:
				other = pl.duel.players[0]
			other = other.nickname
			if pl.duel.private is True:
				who_output.append(caller.connection._("%s (privately dueling %s)") %(pl.nickname, other))
			else:
				who_output.append(caller.connection._("%s (dueling %s)") %(pl.nickname, other))
		elif pl.room and "prepare" in showing:
			who_output.append(caller.connection._("%s (preparing to duel)")%(pl.nickname))
		elif not pl.duel and not pl.watching:
			if "idle" in showing:
				who_output.append(s)
	for pl in who_output:
		caller.connection.notify(pl)

@LobbyParser.command(names=['replay'], args_regexp=r'([a-zA-Z0-9_\.:\-]+)(?:=(\d+))?', allowed=lambda caller: caller.connection.player.is_admin)
def replay(caller):
	with open(os.path.join('duels', caller.args[0])) as fp:
		lines = [json.loads(line) for line in fp]
	if caller.args[1] is not None:
		limit = int(caller.args[1])
	else:
		limit = len(lines)
	for line in lines[:limit]:
		if line['event_type'] == 'start':
			player0 = globals.server.get_player(line['player0'])
			player1 = globals.server.get_player(line['player1'])
			if not player0 or not player1:
				caller.connection.notify(caller.connection._("One of the players is not logged in."))
				return
			if player0.duel or player1.duel:
				caller.connection.notify(caller.connection._("One of the players is in a duel."))
				return
			if player0.room or player1.room:
				pl.notify(pl._("At least one player is currently in a duel room."))
				return
			duel = Duel(line.get('seed', 0))
			duel.load_deck(0, line['deck0'], shuffle=False)
			duel.load_deck(1, line['deck1'], shuffle=False)
			duel.players = [player0, player1]
			player0.duel = duel
			player1.duel = duel
			player0.duel_player = 0
			player1.duel_player = 1
			duel.start()
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
	fn = os.path.join('help', topic)
	if not os.path.isfile(fn):
		caller.connection.notify(caller.connection._("No help topic."))
		return
	with open(fn, encoding='utf-8') as fp:
		caller.connection.notify(fp.read().rstrip('\n'))

@LobbyParser.command(names=['quit'])
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

@LobbyParser.command(names='passwd', allowed = lambda c: c.connection.player.duel is None and c.connection.player.room is None)
def passwd(caller):

	session = caller.connection.session
	account = caller.connection.account
	new_password = ""
	old_parser = caller.connection.parser
	def r(caller):
		if not account.check_password(caller.text):
			caller.connection.notify(caller.connection._("Incorrect password."))
			session.commit()
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
			session.commit()
			return
		account.set_password(caller.text)
		session.commit()
		caller.connection.notify(caller.connection._("Password changed."))
	caller.connection.notify(Reader, r, prompt=caller.connection._("Current password:"), no_abort=caller.connection._("Invalid command."), restore_parser=old_parser)

@LobbyParser.command(names=['language'], args_regexp=r'(.*)')
def language(caller):
	lang = caller.args[0]
	if lang not in ('english', 'german', 'japanese', 'spanish'):
		caller.connection.notify("Usage: language <english/german/japanese/spanish>")
		return
	if lang == 'english':
		caller.connection.player.set_language('en')
	elif lang == 'german':
		caller.connection.player.set_language('de')
	elif lang == 'japanese':
		caller.connection.player.set_language('ja')
	elif lang == 'spanish':
		caller.connection.player.set_language('es')
	caller.connection.account.language = caller.connection.player.language
	caller.connection.session.commit()
	caller.connection.notify(caller.connection._("Language set."))

@LobbyParser.command(args_regexp=r'(.*)')
def encoding(caller):
	if caller.connection.web:
		caller.connection.notify(caller.connection._("Encoding is not needed when using the web client."))
		return
	try:
		codec = codecs.lookup(caller.args[0])
		if not codec._is_text_encoding:
			raise LookupError
	except LookupError:
		caller.connection.notify(caller.connection._("Unknown encoding."))
		return
	caller.connection.encode_args = (caller.args[0], 'replace')
	caller.connection.decode_args = (caller.args[0], 'ignore')
	caller.connection.account.encoding = caller.args[0]
	caller.connection.session.commit()
	caller.connection.notify(caller.connection._("Encoding set."))

@LobbyParser.command(allowed=lambda caller: caller.connection.player.is_admin)
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

@LobbyParser.command(args_regexp=r'(.*)', allowed=lambda caller: caller.connection.player.is_admin)
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
	if caller.connection.player.nickname in player.ignores:
		caller.connection.notify(caller.connection._("%s is ignoring you.") % player.nickname)
		return
	caller.connection.notify(caller.connection._("You tell %s: %s") % (player.nickname, args[1]))
	if player.afk is True:
		caller.connection.notify(caller.connection._("%s is AFK and may not be paying attention.") %(player.nickname))
	player.notify(player._("%s tells you: %s") % (caller.connection.player.nickname, args[1]))
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
	caller.connection.notify(caller.connection._("You reply to %s: %s") % (player.nickname, caller.args[0]))
	player.notify(player._("%s replies: %s") % (caller.connection.player.nickname, caller.args[0]))
	player.reply_to = caller.connection.player.nickname

@LobbyParser.command
def soundpack_on(caller):
	caller.connection.player.soundpack = True

@LobbyParser.command(args_regexp=r'(.*)', allowed = lambda c: c.connection.player.room is None)
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
	elif players[0].duel.private:
		con.notify(con._("That duel is private."))
		return
	players[0].duel.add_watcher(con.player)

@LobbyParser.command(args_regexp=r'(.*)')
def ignore(caller):
	con = caller.connection
	name = caller.args[0]
	if not name:
		con.notify(con._("Ignored accounts:"))
		for account in con.account.ignores:
			con.notify(account.ignored_account.name)
		con.session.commit()
		return
	name = name.capitalize()
	if name == con.player.nickname.capitalize():
		con.notify(con._("You cannot ignore yourself."))
		return
	account = con.session.query(models.Account).filter_by(name=name).first()
	if not account:
		con.notify(con._("That account doesn't exist. Make sure you enter the full name (no auto-completion for security reasons)."))
		con.session.commit()
		return
	ignore = con.session.query(models.Ignore).filter_by(account_id=con.account.id, ignored_account_id=account.id).first()
	if not ignore:
		i = models.Ignore(account_id=con.account.id, ignored_account_id=account.id)
		con.account.ignores.append(i)
		con.session.add(i)
		con.notify(con._("Ignoring %s.") % name)
		con.player.ignores.add(name)
		con.session.commit()
		return
	else:
		con.session.delete(ignore)
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

@LobbyParser.command(allowed=lambda caller: caller.connection.player.is_admin)
def reboot(caller):
	globals.rebooting = True
	globals.server.check_reboot()

# watchers and duelists in paused games need to see them too
@LobbyParser.command(names=['sc', 'score'], allowed = lambda c: c.connection.player.duel is not None)
def score(caller):
	caller.connection.player.duel.show_score(caller.connection.player)

@LobbyParser.command(args_regexp=r'(.*)')
def echo(caller):
	caller.connection.notify(caller.args[0])

@LobbyParser.command(names=['create'], allowed = lambda c: c.connection.player.room is None and c.connection.player.duel is None and c.connection.parser is LobbyParser)
def create(caller):
	r = Room(caller.connection.player)
	r.join(caller.connection.player)
	caller.connection.parser.prompt(caller.connection)

# not the nicest way, but it works
for key in LobbyParser.commands.keys():
	DuelParser.commands[key] = LobbyParser.commands[key]
	RoomParser.commands[key] = LobbyParser.commands[key]
