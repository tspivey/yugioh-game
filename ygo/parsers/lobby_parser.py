import gsb

from ..constants import *

LobbyParser = gsb.Parser(command_substitutions=COMMAND_SUBSTITUTIONS)

@LobbyParser.command(names=['afk'])
def afk(caller):
  conn = caller.connection
  if caller.connection.player.afk is False:
    conn.notify(conn.player._("You are now AFK."))
    conn.player.afk = True
    return
  else:
    conn.notify(conn.player._("You are no longer AFK."))
    conn.player.afk = False
    return

@LobbyParser.command(names=['duel'], args_regexp=r'(.*)')
def cmd_duel(caller):
  caller.connection.player.duel(caller.text)

@LobbyParser.command(args_regexp=r'(.*)')
def cmd_pd(caller):
  caller.connection.player.duel(caller.text, True)

@LobbyParser.command(names='deck', args_regexp=r'(.*)')
def deck(caller):
  lst = caller.args[0].split(None, 1)
  cmd = lst[0]
  caller.args = lst[1:]
  if cmd == 'list':
    caller.connection.player.deck_list()

  if len(caller.args) == 0:
    caller.connection.notify(caller.connection._("This command requires more information to operate with."))
    return

  if cmd == 'load':
    caller.connection.player.deck_load(caller.args[0])
  elif cmd == 'edit':
    caller.connection.player.deck_edit(caller.args[0])
  elif cmd == 'clear':
    caller.connection.player.deck_clear(caller.args[0])
  elif cmd == 'delete':
    caller.connection.player.deck_delete(caller.args[0])
  elif cmd == 'rename':
    caller.connection.player.deck_rename(caller.args[0])
  elif cmd == 'import':
    caller.connection.player.deck_import(caller.args[0])
  elif cmd == 'new':
    caller.connection.player.deck_new(caller.args[0])
  elif cmd == 'check':
    caller.connection.player.deck_check(caller.args[0])
  else:
    caller.connection.notify(caller.connection._("Invalid deck command."))

