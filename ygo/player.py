import gettext

from .constants import *
from . import globals
from .deck_editor import DeckEditor
from .i18n import set_language as i18n_set_language
from .parsers.duel_parser import DuelParser
from .parsers.lobby_parser import LobbyParser
from . import models

class Player:

  def __init__(self, name):
    self._ = gettext.NullTranslations().gettext
    self.afk = False
    self.card_list = []
    self.challenge = True
    self.chat = True
    self.connection = None
    self.deck = {'cards': []}
    self.deck_editor = DeckEditor(self)
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

  def request_duel(self, nick, private=False):
    if nick == 'end':
      if self.watching or not self.duel:
        self.notify(self._("Not in a duel."))
        return
      for pl in self.duel.players + self.duel.watchers:
        pl.notify(pl._("%s has ended the duel.") % self.nickname)
      if not self.duel.private:
        for pl in globals.server.get_all_players():
          globals.server.announce_challenge(pl, pl._("%s has cowardly submitted to %s.") % (self.nickname, self.duel.orig_nicknames[1 - self.duel_player]))
        self.duel.end()
        return

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

  def set_parser(self, p):
    p=p.lower()
    if p == 'lobbyparser':
      self.connection.parser = LobbyParser
    elif p == 'duelparser':
      self.connection.parser = DuelParser
