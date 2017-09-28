import gettext
import json

from .constants import *
import globals
from .i18n import set_language as i18n_set_language
import models

class Player:

  def __init__(self, name):
    self._ = gettext.NullTranslations().gettext
    self.afk = False
    self.card_list = []
    self.challenge = True
    self.chat = True
    self.connection = None
    self.deck = {'cards': []}
    self.deck_edit_pos = 0
    self.duel = None
    self.ignores = set()
    self.is_admin = False
    self.language = 'en'
    self.nickname = name
    self.paused_parser = None
    self.reply_to = ""
    self.requested_opponent = (None, False)
    self.say = True
    self.seen_waiting = None
    self.session = Session()
    self.soundpack = False
    self.watch = True
    self.watching = False

  def set_language(self, lang):
    i18n_set_language(self, lang)

  def attach_connection(self, connection):
    self.connection = connection

  def detach_connection(self):
    self.connection = None

  def notify(self, *args, **kwargs):

    if self.connection:
      self.connection.notify(*args, **kwargs)

  def count_deck_cards(self, deck = None):
    if deck is None:
      deck = self.deck['cards']
    rows = self.cdb.execute('select id, type from datas where id in (%s)'%(','.join([str(c) for c in set(deck)])))
    main = 0
    extra = 0
    for row in rows:
      if row[1]&(TYPE_XYZ | TYPE_SYNCHRO | TYPE_FUSION | TYPE_LINK):
        extra += deck.count(row[0])
      else:
        main += deck.count(row[0])

    return (main, extra)

  def duel(self, text, private=False):
    nick = text[0]
    if nick == 'end':
      if self.watching or not self.duel:
        self.notify(self._("Not in a duel."))
        return
      for pl in self.duel.players + self.duel.watchers:
        if pl is None:
          continue
        pl.notify(pl._("%s has ended the duel.") % self.nickname)
      if not self.duel.private:
        for pl in globals.players.values():
          globals.server.announce_challenge(pl, pl._("%s has cowardly submitted to %s.") % (self.nickname, self.duel.orig_nicknames[1 - self.duel_player]))
        self.duel.end()
        return
    # TODO: duel recovery code goes here
    # since players will stay in the duel, even when their connection dropped,
    # we don't need to restore any relevant data anymore

    players = globals.server.guess_players(nick, self.nickname)
    if self.duel:
      self.notify(self._("You are already in a duel."))
      return
    elif len(players) > 1:
      self.notify(self._("Multiple players match this name: %s")%(','.join([p.nickname for p in players])))
      return
    elif not len(players):
      self.notify(self._("That player is not online."))
      return
    elif players[0].duel:
      self.notify(self._("That player is already in a duel."))
      return
    elif not self.deck['cards']:
      self.notify(self._("You can't duel without a deck. Try deck load public/starter."))
      return
    elif players[0].nickname in self.ignores:
      self.notify(self._("You are ignoring %s.") % players[0].nickname)
      return
    elif self.nickname in players[0].ignores:
      self.notify(self._("%s is ignoring you.") % players[0].nickname)
      return
    player = players[0]
    if player.afk is True:
      self.notify(self._("%s is AFK and may not be paying attention.") %(player.nickname))

    main, extra = self.count_deck_cards()

    if main < 40 or main > 200:
      self.notify(self._("Your main deck must contain between 40 and 200 cards (currently %d).") % main)
      return

    if extra > 15:
      self.notify(self._("Your extra deck may not contain more than 15 cards (currently %d).")%extra)
      return

    if player.requested_opponent[0] == self.nickname:
      player.notify(player._("Duel request accepted, dueling with %s.") % self.nickname)
      globals.server.start_duel(self, player)
      self.duel.private = player.requested_opponent[1]
      if not self.duel.private:
        players = self.duel.players

        for pl in globals.server.get_all_players():
          globals.server.announce_challenge(pl, pl._("The duel between %s and %s has begun!") % (players[0].nickname, players[1].nickname))
      player.requested_opponent = (None, False)
    else:
      player.notify(player._("%s wants to duel. Type duel %s to accept.") % (self.nickname, self.nickname))
      self.requested_opponent = (player.nickname, private)
      self.notify(self._("Duel request sent to %s.") % player.nickname)

  def deck_list(self):
    decks = self.connection.account.decks
      if not decks:
      self.notify(self._("No decks."))
      self.connection.session.commit()
      return
    for deck in decks:
      self.notify(deck.name)
    caller.connection.session.commit()

  def deck_load(self, name):
    session = self.connection.session
    account = self.connection.account
    if name.startswith('public/'):
      account = session.query(models.Account).filter_by(name='Public').first()
      name = name[7:]
  deck = session.query(models.Deck).filter_by(account_id=account.id, name=name).first()
  if not deck:
    self.notify(self._("Deck doesn't exist."))
      session.commit()
      return
    content = json.loads(deck.content)
    self.deck = content
    session.commit()
    self.notify(self._("Deck loaded with %d cards.") % len(content['cards']))

  def deck_clear(self, name):
    account = self.connection.account
    session = self.connection.session
    deck = models.Deck.find(session, account, name)
    if not deck:
      self.notify(self._("Deck not found."))
      session.commit()
      return
    deck.content = json.dumps({'cards': []})
    session.commit()
    self.notify(self._("Deck cleared."))

  def deck_delete(self, name):
    account = self.connection.account
    session = self.connection.session
    deck = models.Deck.find(session, account, name)
    if not deck:
    self.notify(self._("Deck not found."))
      session.commit()
      return
    session.delete(deck)
    session.commit()
  self.notify(self._("Deck deleted."))

  def deck_rename(self, args):
    if '=' not in args:
      self.notify(self._("Usage: deck rename <old>=<new>"))
      return
    args = args.strip().split('=', 1)
    name = args[0].strip()
    dest = args[1].strip()
    if not name or not dest:
      self.notify(self._("Usage: deck rename <old>=<new>"))
      return
    if '=' in dest:
      self.notify(self._("Deck names may not contain =."))
      return
    account = self.connection.account
    session = self.connection.session
    deck = models.Deck.find(session, account, name)
    if not deck:
      self.notify(self._("Deck not found."))
      session.commit()
      return
    dest_deck = models.Deck.find(session, account, dest)
    if dest_deck:
      self.notify(self._("Destination deck already exists"))
      session.commit()
      return
    deck.name = dest
    session.commit()
    self.notify(self._("Deck renamed."))

