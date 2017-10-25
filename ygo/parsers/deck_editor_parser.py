import gsb

from ..card import Card
from .. import globals

class deck_editor_parser(gsb.Parser):

	def huh(self, caller):
		caller.connection.notify(caller.connection._("Invalid command."))

	def handle_line(self, connection, line):
		super(deck_editor_parser, self).handle_line(connection, line)
		if connection.parser is self:
			self.prompt(connection)
	
	def prompt(self, connection):
		pl = connection.player
		editor = pl.deck_editor
		cards = pl.deck['cards']
		pos = editor.deck_edit_pos
		code = globals.server.all_cards[pos]
		in_deck = cards.count(code)
		if in_deck > 0:
			pl.notify(pl._("%d in deck.") % in_deck)
		card = Card(code)
		pl.notify(card.get_info(pl))
		pl.notify(pl._("u: up d: down /: search forward ?: search backward t: top"))
		pl.notify(pl._("s: send to deck r: remove from deck l: list deck g: go to card in deck q: quit"))
		pl.notify(pl._("c: check deck against banlist"))
		main, extra = pl.count_deck_cards(pl.deck['cards'])
		pl.notify(pl._("Command (%d cards in main deck, %d cards in extra deck):") % (main, extra))

DeckEditorParser = deck_editor_parser(command_substitutions={"/": "/", "?": "?"})

@DeckEditorParser.command(names=['d'])
def down(caller):

	caller.connection.player.deck_editor.deck_edit_pos += 1
	if caller.connection.player.deck_editor.deck_edit_pos > len(globals.server.all_cards) - 1:
		caller.connection.player.deck_editor.deck_edit_pos = len(globals.server.all_cards) - 1
		caller.connection.notify(caller.connection._("bottom of list."))

@DeckEditorParser.command(names=['u'])
def up(caller):

	if caller.connection.player.deck_editor.deck_edit_pos == 0:
		caller.connection.notify(caller.connection._("Top of list."))
		return
	caller.connection.player.deck_editor.deck_edit_pos -= 1

@DeckEditorParser.command(names=['t'])
def top(caller):
	caller.connection.player.deck_editor.deck_edit_pos = 0
	caller.connection.notify(caller.connection._("Top."))

@DeckEditorParser.command(names=['s'])
def send(caller):
	cards = caller.connection.player.deck['cards']
	code = globals.server.all_cards[caller.connection.player.deck_editor.deck_edit_pos]
	if cards.count(code) == 3:
		caller.connection.notify(caller.connection._("You already have 3 of this card in your deck."))
		return
	cards.append(code)
	caller.connection.player.deck_editor.save()
	caller.connection.session.commit()

@DeckEditorParser.command(names=['r'], args_regexp=r'(\d+)?')
def remove(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	cards = pl.deck['cards']
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

@DeckEditorParser.command(names=['/'], args_regexp=r'(.*)')
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

@DeckEditorParser.command(names=['?'], args_regexp=r'(.*)')
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

@DeckEditorParser.command(names=['l'])
def cmd_list(caller):
	pl = caller.connection.player
	editor = pl.deck_editor
	cards = pl.deck['cards']
	groups = editor.group_sort_cards(cards.copy())
	monsters, spells, traps, extra, other = groups
	i = 1
	if len(monsters):
		pl.notify(pl._("monsters (%d):")%(sum(monsters.values())))
		for code, count in monsters.items():
			card = Card(code)
			if count > 1:
				pl.notify("%d: %s (x %d)" % (i, card.get_name(pl), count))
			else:
				pl.notify("%d: %s" % (i, card.get_name(pl)))
			i += 1
	if len(spells):
		pl.notify(pl._("spells (%d):")%(sum(spells.values())))
		for code, count in spells.items():
			card = Card(code)
			if count > 1:
				pl.notify("%d: %s (x %d)" % (i, card.get_name(pl), count))
			else:
				pl.notify("%d: %s" % (i, card.get_name(pl)))
			i += 1
	if len(traps):
		pl.notify(pl._("traps (%d):")%(sum(traps.values())))
		for code, count in traps.items():
			card = Card(code)
			if count > 1:
				pl.notify("%d: %s (x %d)" % (i, card.get_name(pl), count))
			else:
				pl.notify("%d: %s" % (i, card.get_name(pl)))
			i += 1
	if len(extra):
		pl.notify(pl._("extra (%d):")%(sum(extra.values())))
		for code, count in extra.items():
			card = Card(code)
			if count > 1:
				pl.notify("%d: %s (x %d)" % (i, card.get_name(pl), count))
			else:
				pl.notify("%d: %s" % (i, card.get_name(pl)))
			i += 1

@DeckEditorParser.command(names=['g'], args_regexp=r'(\d+)')
def goto(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	cards = pl.deck['cards']
	cnt = editor.group_cards_combined(cards.copy())
	n = int(caller.args[0]) - 1
	if n < 0 or n > len(cnt) - 1:
		pl.notify(pl._("Invalid card."))
		return
	code = list(cnt.keys())[n]
	editor.deck_edit_pos = globals.server.all_cards.index(code)

@DeckEditorParser.command(names=['q'])
def quit(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	
	pl.notify(pl._("Quit."))
	editor.deck_name = ''
	pl.connection.parser = pl.paused_parser
	pl.paused_parser = None

@DeckEditorParser.command(names=['c'], args_regexp='([a-zA-Z0-9\.\- ]+)?')
def check(caller):

	pl = caller.connection.player
	editor = pl.deck_editor
	cards = pl.deck['cards']
	search = caller.args[0]
	if search is not None:
		search = search.lower()
	editor.check(cards, search)
