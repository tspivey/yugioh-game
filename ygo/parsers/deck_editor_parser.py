from ..card import Card
from ..constants import COMMAND_SUBSTITUTIONS
from .. import globals
from .. import parser

class deck_editor_parser(parser.Parser):

	def huh(self, caller):
		caller.connection.notify(caller.connection._("Invalid command."))

	def handle_line(self, connection, line):
		super(deck_editor_parser, self).handle_line(connection, line)
		if connection.parser is self:
			self.prompt(connection)
	
	def prompt(self, connection):
		pl = connection.player
		editor = pl.deck_editor
		pos = editor.deck_edit_pos
		code = globals.server.all_cards[pos]

		in_deck = pl.deck.get('cards', []).count(code)
		if in_deck > 0:
			pl.notify(pl._("%d in deck.") % in_deck)
		in_deck = pl.deck.get('side', []).count(code)
		if in_deck > 0:
			pl.notify(pl._("%d in side deck.") % in_deck)
		
		if editor.deck_key == 'cards':
			pl.notify(pl._("editing main deck."))
		elif editor.deck_key == 'side':
			pl.notify(pl._("editing side deck."))

		card = Card(code)
		pl.notify(card.get_info(pl))
		pl.notify(pl._("u: up d: down /: search forward ?: search backward t: top"))
		pl.notify(pl._("s: send to deck r: remove from deck l: list deck g: go to card in deck q: quit"))
		pl.notify(pl._("c: check deck against banlist w: switch between main deck and side deck"))
		main, extra = pl.count_deck_cards(pl.deck['cards'])
		pl.notify(pl._("Command (%d cards in main deck, %d cards in extra deck, %d cards in side deck):") % (main, extra, len(pl.deck.get('side', []))))

substitutions = {
	'/': 'search_forward',
	'?': 'search_backward',
	'c': 'check',
	'd': 'down',
	'g': 'goto',
	'l': 'cmd_list',
	'q': 'quit',
	'r': 'remove',
	's': 'send',
	't': 'top',
	'u': 'up',
	'w': 'switch'
}

substitutions.update(COMMAND_SUBSTITUTIONS)

DeckEditorParser = deck_editor_parser(command_substitutions=substitutions)

@DeckEditorParser.command
def down(caller):

	caller.connection.player.deck_editor.deck_edit_pos += 1
	if caller.connection.player.deck_editor.deck_edit_pos > len(globals.server.all_cards) - 1:
		caller.connection.player.deck_editor.deck_edit_pos = len(globals.server.all_cards) - 1
		caller.connection.notify(caller.connection._("bottom of list."))

@DeckEditorParser.command
def up(caller):

	if caller.connection.player.deck_editor.deck_edit_pos == 0:
		caller.connection.notify(caller.connection._("Top of list."))
		return
	caller.connection.player.deck_editor.deck_edit_pos -= 1

@DeckEditorParser.command
def top(caller):
	caller.connection.player.deck_editor.deck_edit_pos = 0
	caller.connection.notify(caller.connection._("Top."))

@DeckEditorParser.command
def send(caller):
	code = globals.server.all_cards[caller.connection.player.deck_editor.deck_edit_pos]
	found = caller.connection.player.deck_editor.count_occurrence_in_deck(code)
	if found >= 3:
		caller.connection.notify(caller.connection._("You may only have 3 of this card (or cards with the same name) in your deck."))
		return
	caller.connection.player.deck[caller.connection.player.deck_editor.deck_key].append(code)
	caller.connection.player.deck_editor.save()
	caller.connection.session.commit()

@DeckEditorParser.command(args_regexp=r'(\d+)?')
def remove(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	cards = pl.deck[caller.connection.player.deck_editor.deck_key]
	cnt = editor.group_cards_combined(cards.copy())

	if caller.args[0] is None:
		code = globals.server.all_cards[editor.deck_edit_pos]
	else:
		n = int(caller.args[0]) - 1
		if n < 0 or n > len(cnt) - 1:
			pl.notify(pl._("Invalid card."))
			return
		code = list(cnt.keys())[n]
	
	if cards.count(code) == 0:
		pl.notify(pl._("This card isn't in your deck."))
		return
	cards.remove(code)
	pl.notify(pl._("Removed %s from your deck." %(Card(code).get_name(pl))))
	editor.save()
	caller.connection.session.commit()

@DeckEditorParser.command(args_regexp=r'(.*)')
def search_forward(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	
	text = caller.args[0] or editor.last_search
	editor.last_search = text

	search_pos = editor.deck_edit_pos + 1
	if search_pos >= len(globals.server.all_cards):
		search_pos = 0
	
	pos = editor.find_next(text, search_pos)
	
	if pos is None:
		pl.notify(pl._("Not found."))
	else:
		editor.deck_edit_pos = pos

@DeckEditorParser.command(args_regexp=r'(.*)')
def search_backward(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	
	text = caller.args[0] or editor.last_search
	editor.last_search = text
	
	search_start = editor.deck_edit_pos - 1
	if search_start < 0:
		search_start = len(globals.server.all_cards) - 1
	
	pos = editor.find_prev(text, search_start)
	
	if pos is None:
		pl.notify(pl._("Not found."))
	else:
		editor.deck_edit_pos = pos

@DeckEditorParser.command
def cmd_list(caller):
	pl = caller.connection.player
	editor = pl.deck_editor

	if len(pl.deck.get('cards', [])):
		cards = pl.deck['cards']

		pl.notify(pl._("main deck:"))

		editor.list(cards.copy())

	if len(pl.deck.get('side', [])):
		cards = pl.deck['side']

		pl.notify(pl._("side deck:"))

		editor.list(cards.copy())

@DeckEditorParser.command(args_regexp=r'(\d+)')
def goto(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	cards = pl.deck[editor.deck_key]
	cnt = editor.group_cards_combined(cards.copy())
	n = int(caller.args[0]) - 1
	if n < 0 or n > len(cnt) - 1:
		pl.notify(pl._("Invalid card."))
		return
	code = list(cnt.keys())[n]
	editor.deck_edit_pos = globals.server.all_cards.index(code)

@DeckEditorParser.command
def quit(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	
	pl.notify(pl._("Quit."))
	editor.deck_name = ''
	pl.connection.parser = pl.paused_parser
	pl.paused_parser = None

@DeckEditorParser.command(args_regexp='([a-zA-Z0-9\.\- ]+)?')
def check(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	cards = pl.deck.get('cards', []) + pl.deck.get('side', [])
	search = caller.args[0]
	if search is not None:
		search = search.lower()
	editor.check(cards, search)

@DeckEditorParser.command
def switch(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	
	if editor.deck_key == 'cards':
		editor.deck_key = 'side'
		pl.notify(pl._('now editing side deck'))
	elif editor.deck_key == 'side':
		editor.deck_key = 'cards'
		pl.notify(pl._("now editing main deck"))
	
	if not editor.deck_key in pl.deck:
		pl.deck[editor.deck_key] = []
