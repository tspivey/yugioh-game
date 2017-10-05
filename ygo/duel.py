from _duel import ffi, lib
import os
import io
import struct
import random
import binascii
from functools import partial
import pkgutil
import re
import datetime

from . import callback_manager
from .card import Card
from .constants import *
from . import globals
from . import message_handlers

@ffi.def_extern()
def card_reader_callback(code, data):
  cd = data[0]
  row = globals.server.db.execute('select * from datas where id=?', (code,)).fetchone()
  cd.code = code
  cd.alias = row['alias']
  cd.setcode = row['setcode']
  cd.type = row['type']
  cd.level = row['level'] & 0xff
  cd.lscale = (row['level'] >> 24) & 0xff
  cd.rscale = (row['level'] >> 16) & 0xff
  cd.attack = row['atk']
  cd.defense = row['def']
  cd.race = row['race']
  cd.attribute = row['attribute']
  return 0

lib.set_card_reader(lib.card_reader_callback)

scriptbuf = ffi.new('char[131072]')
@ffi.def_extern()
def script_reader_callback(name, lenptr):
  fn = ffi.string(name)
  if not os.path.exists(fn):
    lenptr[0] = 0
    return ffi.NULL
  s = open(fn, 'rb').read()
  buf = ffi.buffer(scriptbuf)
  buf[0:len(s)] = s
  lenptr[0] = len(s)
  return ffi.cast('byte *', scriptbuf)

lib.set_script_reader(lib.script_reader_callback)

class Duel:
  def __init__(self, seed=None):
    self.buf = ffi.new('char[]', 4096)
    if seed is None:
      seed = random.randint(0, 0xffffffff)
    self.seed = seed
    self.duel = lib.create_duel(seed)
    lib.set_player_info(self.duel, 0, 8000, 5, 1)
    lib.set_player_info(self.duel, 1, 8000, 5, 1)
    self.bind_message_handlers()
    self.cm = callback_manager.CallbackManager()
    self.keep_processing = False
    self.to_ep = False
    self.to_m2 = False
    self.current_phase = 0
    self.watchers = []
    self.private = False
    self.started = False
    self.debug_mode = False
    self.players = [None, None]
    self.lp = [8000, 8000]
    self.started = False
    self.register_callbacks()
    self.message_map = {
      90: self.msg_draw,
      40: self.msg_new_turn,
      41: self.msg_new_phase,
      11: self.msg_idlecmd,
      1: self.msg_retry,
      2: self.msg_hint,
      18: self.msg_select_place,
      24: self.msg_select_place,
      37: self.msg_reversedeck,
      38: self.msg_decktop,
      50: self.msg_move,
      55: self.msg_swap,
      56: self.msg_field_disabled,
      60: self.msg_summoning,
      16: self.msg_select_chain,
      61: self.msg_summoned,
      64: self.msg_flipsummoning,
      54: self.msg_set,
      10: self.msg_select_battlecmd,
      101: self.msg_counters,
      102: self.msg_counters,
      110: self.msg_attack,
      113: self.msg_begin_damage,
      114: self.msg_end_damage,
      111: self.msg_battle,
      91: self.msg_damage,
      15: self.msg_select_card,
      14: self.msg_select_option,
      92: self.msg_recover,
      20: self.msg_select_tribute,
      53: self.msg_pos_change,
      70: self.msg_chaining,
      19: self.msg_select_position,
      13: self.msg_yesno,
      62: partial(self.msg_summoning, special=True),
      12: self.msg_select_effectyn,
      5: self.msg_win,
      100: self.msg_pay_lpcost,
      21: self.msg_sort_chain,
      141: self.msg_announce_attrib,
      142: self.msg_announce_card,
      143: self.msg_announce_number,
      144: self.msg_announce_card_filter,
      23: self.msg_select_sum,
      140: self.msg_announce_race,
      22: self.msg_select_counter,
      83: self.msg_become_target,
      25: self.msg_sort_card,
      130: self.msg_toss_coin,
      131: partial(self.msg_toss_coin, dice=True),
      31: self.msg_confirm_cards,
      73: self.msg_chain_solved,
      93: self.msg_equip,
      94: self.msg_lpupdate,
      32: self.msg_shuffle,
    }
    self.state = ''
    self.cards = [None, None]
    self.revealed = {}

  def load_deck(self, player, cards, shuffle=True):
    self.cards[player] = cards[:]
    if shuffle:
      random.shuffle(self.cards[player])
    for c in self.cards[player][::-1]:
      lib.new_card(self.duel, c, player, player, LOCATION_DECK, 0, POS_FACEDOWN_DEFENSE);

  def start(self):
    lib.start_duel(self.duel, 0)
    self.started = True

  def end(self):
    lib.end_duel(self.duel)
    self.started = False
    for pl in self.players + self.watchers:
      if pl is None:
        continue
      pl.duel = None
      pl.intercept = None
      op = pl.connection.parser
      if isinstance(op, DuelReader):
        op.done = lambda caller: None
      pl.connection.parser = LobbyParserparser
      pl.watching = False
      pl.card_list = []
    for pl in self.watchers:
      pl.notify(pl._("Watching stopped."))
    globals.server.check_reboot()

  def process(self):
    res = lib.process(self.duel)
    l = lib.get_message(self.duel, ffi.cast('byte *', self.buf))
    data = ffi.unpack(self.buf, l)
    self.cm.call_callbacks('debug', event_type='process', result=res, data=data.decode('latin1'))
    data = self.process_messages(data)
    return res

  def process_messages(self, data):
    while data:
      msg = int(data[0])
      fn = self.message_map.get(msg)
      if fn:
        data = fn(data)
      else:
        print("msg %d unhandled" % msg)
        data = b''
    return data

  def msg_swap(self, data):
    data = io.BytesIO(data[1:])

    code1 = self.read_u32(data)
    location1 = self.read_u32(data)
    code2 = self.read_u32(data)
    location2 = self.read_u32(data)

    card1 = Card(code1)
    card1.set_location(location1)
    card2 = Card(code2)
    card2.set_location(location2)
    self.cm.call_callbacks('swap', card1, card2)

    return data.read()

  def msg_counters(self, data):
    data = io.BytesIO(data[0:])

    msg = self.read_u8(data)

    ctype = self.read_u16(data)

    pl = self.read_u8(data)

    loc = self.read_u8(data)

    seq = self.read_u8(data)

    count = self.read_u16(data)

    card = self.get_card(pl, loc, seq)

    self.cm.call_callbacks('counters', card, ctype, count, msg==101)
      
    return data.read()

  def msg_reversedeck(self, data):
    for pl in self.players+self.watchers:
      pl.notify(pl._("all decks are now reversed."))
    return data[1:]

  def msg_decktop(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    self.read_u8(data) # don't know what this number does
    code = self.read_u32(data)
    if code & 0x80000000:
      code = code ^ 0x80000000 # don't know what this actually does
    self.cm.call_callbacks('decktop', player, Card(code))
    return data.read()

  def msg_draw(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    drawed = self.read_u8(data)
    cards = []
    for i in range(drawed):
      c = self.read_u32(data)
      card = Card(c & 0x7fffffff)
      cards.append(card)
    self.cm.call_callbacks('draw', player, cards)
    return data.read()

  def msg_new_turn(self, data):
    tp = int(data[1])
    self.cm.call_callbacks('new_turn', tp)
    return data[2:]

  def msg_new_phase(self, data):
    phase = struct.unpack('h', data[1:])[0]
    self.cm.call_callbacks('phase', phase)
    return b''

  def msg_idlecmd(self, data):
    self.state = 'idle'
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    summonable = self.read_cardlist(data)
    spsummon = self.read_cardlist(data)
    repos = self.read_cardlist(data)
    idle_mset = self.read_cardlist(data)
    idle_set = self.read_cardlist(data)
    idle_activate = self.read_cardlist(data, True)
    to_bp = self.read_u8(data)
    to_ep = self.read_u8(data)
    cs = self.read_u8(data)
    self.cm.call_callbacks('idle', summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs)
    return data.read()

  def read_cardlist(self, data, extra=False, extra8=False):
    res = []
    size = self.read_u8(data)
    for i in range(size):
      code = self.read_u32(data)
      controller = self.read_u8(data)
      location = self.read_u8(data)
      sequence = self.read_u8(data)
      card = self.get_card(controller, location, sequence)
      card.extra = 0
      if extra:
        if extra8:
          card.extra = self.read_u8(data)
        else:
          card.extra = self.read_u32(data)
      res.append(card)
    return res

  def msg_retry(self, buf):
    print("retry")
    return buf[1:]

  def msg_hint(self, data):
    data = io.BytesIO(data[1:])
    msg = self.read_u8(data)
    player = self.read_u8(data)
    value = self.read_u32(data)
    self.cm.call_callbacks('hint', msg, player, value)
    return data.read()

  def msg_select_place(self, data):
    data = io.BytesIO(data)
    msg = self.read_u8(data)
    player = self.read_u8(data)
    count = self.read_u8(data)
    flag = self.read_u32(data)
    self.cm.call_callbacks('select_place', player, count, flag)
    return data.read()

  def msg_select_battlecmd(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    activatable = self.read_cardlist(data, True)
    attackable = self.read_cardlist(data, True, True)
    to_m2 = self.read_u8(data)
    to_ep = self.read_u8(data)
    self.cm.call_callbacks('select_battlecmd', player, activatable, attackable, to_m2, to_ep)
    return data.read()

  def msg_attack(self, data):
    data = io.BytesIO(data[1:])
    attacker = self.read_u32(data)
    ac = attacker & 0xff
    al = (attacker >> 8) & 0xff
    aseq = (attacker >> 16) & 0xff
    apos = (attacker >> 24) & 0xff
    target = self.read_u32(data)
    tc = target & 0xff
    tl = (target >> 8) & 0xff
    tseq = (target >> 16) & 0xff
    tpos = (target >> 24) & 0xff
    self.cm.call_callbacks('attack', ac, al, aseq, apos, tc, tl, tseq, tpos)
    return data.read()

  def msg_begin_damage(self, data):
    self.cm.call_callbacks('begin_damage')
    return data[1:]

  def msg_end_damage(self, data):
    self.cm.call_callbacks('end_damage')
    return data[1:]

  def msg_battle(self, data):
    data = io.BytesIO(data[1:])
    attacker = self.read_u32(data)
    aa = self.read_u32(data)
    ad = self.read_u32(data)
    bd0 = self.read_u8(data)
    tloc = self.read_u32(data)
    da = self.read_u32(data)
    dd = self.read_u32(data)
    bd1 = self.read_u8(data)
    self.cm.call_callbacks('battle', attacker, aa, ad, bd0, tloc, da, dd, bd1)
    return data.read()

  def msg_select_card(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    cancelable = self.read_u8(data)
    min = self.read_u8(data)
    max = self.read_u8(data)
    size = self.read_u8(data)
    cards = []
    for i in range(size):
      code = self.read_u32(data)
      loc = self.read_u32(data)
      c = loc & 0xff
      l = (loc >> 8) & 0xff;
      s = (loc >> 16) & 0xff
      card = self.get_card(c, l, s)
      card = Card(code)
      card.set_location(loc)
      cards.append(card)
    self.cm.call_callbacks('select_card', player, cancelable, min, max, cards)
    return data.read()

  def msg_select_tribute(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    cancelable = self.read_u8(data)
    min = self.read_u8(data)
    max = self.read_u8(data)
    size = self.read_u8(data)
    cards = []
    for i in range(size):
      code = self.read_u32(data)
      card = Card(code)
      card.controller = self.read_u8(data)
      card.location = self.read_u8(data)
      card.sequence = self.read_u8(data)
      card.position = self.get_card(card.controller, card.location, card.sequence).position
      card.release_param = self.read_u8(data)
      cards.append(card)
    self.cm.call_callbacks('select_tribute', player, cancelable, min, max, cards)
    return data.read()

  def msg_damage(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    amount = self.read_u32(data)
    self.cm.call_callbacks('damage', player, amount)
    return data.read()

  def msg_recover(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    amount = self.read_u32(data)
    self.cm.call_callbacks('recover', player, amount)
    return data.read()

  def msg_move(self, data):
    data = io.BytesIO(data[1:])
    code = self.read_u32(data)
    location = self.read_u32(data)
    newloc = self.read_u32(data)
    reason = self.read_u32(data)
    self.cm.call_callbacks('move', code, location, newloc, reason)
    return data.read()

  def msg_field_disabled(self, data):
    data = io.BytesIO(data[1:])
    locations = self.read_u32(data)
    self.cm.call_callbacks('field_disabled', locations)
    return data.read()

  def msg_summoning(self, data, special=False):
    data = io.BytesIO(data[1:])
    code = self.read_u32(data)
    card = Card(code)
    card.set_location(self.read_u32(data))
    self.cm.call_callbacks('summoning', card, special=special)
    return data.read()

  def msg_select_chain(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    size = self.read_u8(data)
    spe_count = self.read_u8(data)
    forced = self.read_u8(data)
    hint_timing = self.read_u32(data)
    other_timing = self.read_u32(data)
    chains = []
    for i in range(size):
      et = self.read_u8(data)
      code = self.read_u32(data)
      loc = self.read_u32(data)
      card = Card(code)
      card.set_location(loc)
      desc = self.read_u32(data)
      chains.append((et, card, desc))
    self.cm.call_callbacks('select_chain', player, size, spe_count, forced, chains)
    return data.read()

  def msg_summoned(self, data):
    return data[1:]

  def msg_set(self, data):
    data = io.BytesIO(data[1:])
    code = self.read_u32(data)
    loc = self.read_u32(data)
    card = Card(code)
    card.set_location(loc)
    self.cm.call_callbacks('set', card)
    return data.read()

  def msg_select_option(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    size = self.read_u8(data)
    options = []
    for i in range(size):
      options.append(self.read_u32(data))
    self.cm.call_callbacks("select_option", player, options)
    return data.read()

  def msg_pos_change(self, data):
    data = io.BytesIO(data[1:])
    code = self.read_u32(data)
    card = Card(code)
    card.controller = self.read_u8(data)
    card.location = self.read_u8(data)
    card.sequence = self.read_u8(data)
    prevpos = self.read_u8(data)
    card.position = self.read_u8(data)
    self.cm.call_callbacks('pos_change', card, prevpos)
    return data.read()

  def msg_chaining(self, data):
    data = io.BytesIO(data[1:])
    code = self.read_u32(data)
    card = Card(code)
    card.set_location(self.read_u32(data))
    tc = self.read_u8(data)
    tl = self.read_u8(data)
    ts = self.read_u8(data)
    desc = self.read_u32(data)
    cs = self.read_u8(data)
    self.cm.call_callbacks('chaining', card, tc, tl, ts, desc, cs)
    return data.read()

  def msg_select_position(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    code = self.read_u32(data)
    card = Card(code)
    positions = self.read_u8(data)
    self.cm.call_callbacks('select_position', player, card, positions)
    return data.read()

  def msg_yesno(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    desc = self.read_u32(data)
    self.cm.call_callbacks('yesno', player, desc)
    return data.read()

  def msg_select_effectyn(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    card = Card(self.read_u32(data))
    card.set_location(self.read_u32(data))
    desc = self.read_u32(data)
    self.cm.call_callbacks('select_effectyn', player, card, desc)
    return data.read()

  def msg_win(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    reason = self.read_u8(data)
    self.cm.call_callbacks('win', player, reason)
    return data.read()

  def msg_pay_lpcost(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    cost = self.read_u32(data)
    self.cm.call_callbacks('pay_lpcost', player, cost)
    return data.read()

  def msg_sort_chain(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    size = self.read_u8(data)
    cards = []
    for i in range(size):
      code = self.read_u32(data)
      card = Card(code)
      card.controller = self.read_u8(data)
      card.location = self.read_u8(data)
      card.sequence = self.read_u8(data)
      cards.append(card)
    self.cm.call_callbacks('sort_chain', player, cards)
    return data.read()

  def msg_announce_attrib(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    count = self.read_u8(data)
    avail = self.read_u32(data)
    self.cm.call_callbacks('announce_attrib', player, count, avail)
    return data.read()

  def msg_announce_card(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    type = self.read_u32(data)
    self.cm.call_callbacks('announce_card', player, type)
    return data.read()

  def msg_announce_number(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    size = self.read_u8(data)
    opts = [self.read_u32(data) for i in range(size)]
    self.cm.call_callbacks('announce_number', player, opts)
    return data.read()

  def msg_announce_card_filter(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    size = self.read_u8(data)
    options = []
    for i in range(size):
      options.append(self.read_u32(data))
    self.cm.call_callbacks('announce_card_filter', player, options)
    return data.read()

  def msg_select_sum(self, data):
    data = io.BytesIO(data[1:])
    mode = self.read_u8(data)
    player = self.read_u8(data)
    val = self.read_u32(data)
    select_min = self.read_u8(data)
    select_max = self.read_u8(data)
    count = self.read_u8(data)
    must_select = []
    for i in range(count):
      code = self.read_u32(data)
      card = Card(code)
      card.controller = self.read_u8(data)
      card.location = self.read_u8(data)
      card.sequence = self.read_u8(data)
      card.param = self.read_u32(data)
      must_select.append(card)
    count = self.read_u8(data)
    select_some = []
    for i in range(count):
      code = self.read_u32(data)
      card = Card(code)
      card.controller = self.read_u8(data)
      card.location = self.read_u8(data)
      card.sequence = self.read_u8(data)
      card.param = self.read_u32(data)
      select_some.append(card)
    self.cm.call_callbacks('select_sum', mode, player, val, select_min, select_max, must_select, select_some)
    return data.read()

  def msg_select_counter(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    countertype = self.read_u16(data)
    count = self.read_u16(data)
    size = self.read_u8(data)
    cards = []
    for i in range(size):
      card = Card(self.read_u32(data))
      card.controller = self.read_u8(data)
      card.location = self.read_u8(data)
      card.sequence = self.read_u8(data)
      card.counter = self.read_u16(data)
      cards.append(card)
    self.cm.call_callbacks('select_counter', player, countertype, count, cards)
    return data.read()

  def msg_become_target(self, data):
    data = io.BytesIO(data[1:])
    u = self.read_u8(data)
    target = self.read_u32(data)
    tc = target & 0xff
    tl = (target >> 8) & 0xff
    tseq = (target >> 16) & 0xff
    tpos = (target >> 24) & 0xff
    self.cm.call_callbacks('become_target', tc, tl, tseq)
    return data.read()

  def msg_announce_race(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    count = self.read_u8(data)
    avail = self.read_u32(data)
    self.cm.call_callbacks('announce_race', player, count, avail)
    return data.read()

  def msg_sort_card(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    size = self.read_u8(data)
    cards = []
    for i in range(size):
      card = Card(self.read_u32(data))
      card.controller = self.read_u8(data)
      card.location = self.read_u8(data)
      card.sequence = self.read_u8(data)
      cards.append(card)
    self.cm.call_callbacks('sort_card', player, cards)
    return data.read()

  def msg_toss_coin(self, data, dice=False):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    count = self.read_u8(data)
    options = [self.read_u8(data) for i in range(count)]
    if dice:
      self.cm.call_callbacks('toss_dice', player, options)
    else:
      self.cm.call_callbacks('toss_coin', player, options)
    return data.read()

  def msg_confirm_cards(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    size = self.read_u8(data)
    cards = []
    for i in range(size):
      code = self.read_u32(data)
      c = self.read_u8(data)
      l = self.read_u8(data)
      s = self.read_u8(data)
      card = self.get_card(c, l, s)
      cards.append(card)
    self.cm.call_callbacks('confirm_cards', player, cards)
    return data.read()

  def msg_chain_solved(self, data):
    data = io.BytesIO(data[1:])
    count = self.read_u8(data)
    self.cm.call_callbacks('chain_solved', count)
    return data.read()

  def msg_equip(self, data):
    data = io.BytesIO(data[1:])
    loc = self.read_u32(data)
    target = self.read_u32(data)
    u = self.unpack_location(loc)
    card = self.get_card(u[0], u[1], u[2])
    u = self.unpack_location(target)
    target = self.get_card(u[0], u[1], u[2])
    self.cm.call_callbacks('equip', card, target)
    return data.read()

  def msg_lpupdate(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    lp = self.read_u32(data)
    self.cm.call_callbacks('lpupdate', player, lp)
    return data.read()

  def msg_shuffle(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    self.cm.call_callbacks('shuffle', player)
    return data.read()

  def msg_flipsummoning(self, data):
    data = io.BytesIO(data[1:])
    code = self.read_u32(data)
    location = self.read_u32(data)
    c = location & 0xff
    loc = (location >> 8) & 0xff;
    seq = (location >> 16) & 0xff
    card = self.get_card(c, loc, seq)
    self.cm.call_callbacks('flipsummoning', card)
    return data.read()

  def read_u8(self, buf):
    return struct.unpack('b', buf.read(1))[0]

  def read_u16(self, buf):
    return struct.unpack('h', buf.read(2))[0]

  def read_u32(self, buf):
    return struct.unpack('I', buf.read(4))[0]

  def set_responsei(self, r):
    lib.set_responsei(self.duel, r)
    self.cm.call_callbacks('debug', event_type='set_responsei', response=r)

  def set_responseb(self, r):
    buf = ffi.new('char[64]', r)
    lib.set_responseb(self.duel, ffi.cast('byte *', buf))
    self.cm.call_callbacks('debug', event_type='set_responseb', response=r.decode('latin1'))

  def get_cards_in_location(self, player, location):
    cards = []
    flags = QUERY_CODE | QUERY_POSITION | QUERY_LEVEL | QUERY_ATTACK | QUERY_DEFENSE | QUERY_EQUIP_CARD | QUERY_OVERLAY_CARD | QUERY_COUNTERS
    bl = lib.query_field_card(self.duel, player, location, flags, ffi.cast('byte *', self.buf), False)
    buf = io.BytesIO(ffi.unpack(self.buf, bl))
    while True:
      if buf.tell() == bl:
        break
      length = self.read_u32(buf)
      if length == 4:
        continue #No card here
      f = self.read_u32(buf)
      code = self.read_u32(buf)
      card = Card(code)
      position = self.read_u32(buf)
      card.set_location(position)
      level = self.read_u32(buf)
      if (level & 0xff) > 0:
        card.level = level & 0xff
      card.attack = self.read_u32(buf)
      card.defense = self.read_u32(buf)

      card.equip_target = None

      if f & QUERY_EQUIP_CARD == QUERY_EQUIP_CARD: # optional

        equip_target = self.read_u32(buf)
        pl = equip_target & 0xff
        loc = (equip_target >> 8) & 0xff
        seq = (equip_target >> 16) & 0xff
        card.equip_target = self.get_card(pl, loc, seq)

      card.xyz_materials = []

      xyz = self.read_u32(buf)

      for i in range(xyz):
        card.xyz_materials.append(Card(self.read_u32(buf)))

      cs = self.read_u32(buf)
      card.counters = []
      for i in range(cs):
        card.counters.append(self.read_u32(buf))
      cards.append(card)
    return cards

  def get_card(self, player, loc, seq):
    flags = QUERY_CODE | QUERY_ATTACK | QUERY_DEFENSE | QUERY_POSITION | QUERY_LEVEL
    bl = lib.query_card(self.duel, player, loc, seq, flags, ffi.cast('byte *', self.buf), False)
    buf = io.BytesIO(ffi.unpack(self.buf, bl))
    f = self.read_u32(buf)
    if f == 4:
      return
    f = self.read_u32(buf)
    code = self.read_u32(buf)
    card = Card(code)
    position = self.read_u32(buf)
    card.set_location(position)
    level = self.read_u32(buf)
    if (level & 0xff) > 0:
      card.level = level & 0xff
    card.attack = self.read_u32(buf)
    card.defense = self.read_u32(buf)
    return card

  def unpack_location(self, loc):
    controller = loc & 0xff
    location = (loc >> 8) & 0xff
    sequence = (loc >> 16) & 0xff
    position = (loc >> 24) & 0xff
    return (controller, location, sequence, position)

  def bind_message_handlers(self):

    for importer, modname, ispkg in pkgutil.iter_modules(message_handlers.__path__):
      if not ispkg:
        m = importer.find_module(modname).load_module(modname)
        # we bind the functions in those modules to this object
        # the functions need to have the same name as the module
        setattr(self, modname, getattr(m, modname).__get__(self))

  def register_callbacks(self):
    self.cm.register_callback('draw', self.draw)
    self.cm.register_callback('shuffle', self.shuffle)
    self.cm.register_callback('phase', self.phase)
    self.cm.register_callback('new_turn', self.new_turn)
    self.cm.register_callback('idle', self.idle)
    self.cm.register_callback('select_place', self.select_place)
    self.cm.register_callback('select_chain', self.select_chain)
    self.cm.register_callback('summoning', self.summoning)
    self.cm.register_callback('flipsummoning', self.flipsummoning)
    self.cm.register_callback("select_battlecmd", self.select_battlecmd)
    self.cm.register_callback('attack', self.attack)
    self.cm.register_callback('begin_damage', self.begin_damage)
    self.cm.register_callback('end_damage', self.end_damage)
    self.cm.register_callback('decktop', self.decktop)
    self.cm.register_callback('battle', self.battle)
    self.cm.register_callback('damage', self.damage)
    self.cm.register_callback('hint', self.hint)
    self.cm.register_callback('select_card', self.select_card)
    self.cm.register_callback('move', self.move)
    self.cm.register_callback('select_option', self.select_option)
    self.cm.register_callback('recover', self.recover)
    self.cm.register_callback('select_tribute', partial(self.select_card, is_tribute=True))
    self.cm.register_callback('pos_change', self.pos_change)
    self.cm.register_callback('set', self.set)
    self.cm.register_callback("chaining", self.chaining)
    self.cm.register_callback('select_position', self.select_position)
    self.cm.register_callback('yesno', self.yesno)
    self.cm.register_callback('select_effectyn', self.select_effectyn)
    self.cm.register_callback('win', self.win)
    self.cm.register_callback('pay_lpcost', self.pay_lpcost)
    self.cm.register_callback('sort_chain', self.sort_chain)
    self.cm.register_callback('announce_attrib', self.announce_attrib)
    self.cm.register_callback('announce_card', self.announce_card)
    self.cm.register_callback('announce_number', self.announce_number)
    self.cm.register_callback('announce_card_filter', self.announce_card_filter)
    self.cm.register_callback('select_sum', self.select_sum)
    self.cm.register_callback('select_counter', self.select_counter)
    self.cm.register_callback('announce_race', self.announce_race)
    self.cm.register_callback('become_target', self.become_target)
    self.cm.register_callback('sort_card', self.sort_card)
    self.cm.register_callback('field_disabled', self.field_disabled)
    self.cm.register_callback('toss_coin', self.toss_coin)
    self.cm.register_callback('toss_dice', self.toss_dice)
    self.cm.register_callback('confirm_cards', self.confirm_cards)
    self.cm.register_callback('chain_solved', self.chain_solved)
    self.cm.register_callback('equip', self.equip)
    self.cm.register_callback('lpupdate', self.lpupdate)
    self.cm.register_callback('debug', self.debug)
    self.cm.register_callback('counters', self.counters)
    self.cm.register_callback('swap', self.swap)

  def show_usable(self, pl):
    summonable = natsort.natsorted([card.get_spec(pl.duel_player) for card in self.summonable])
    spsummon = natsort.natsorted([card.get_spec(pl.duel_player) for card in self.spsummon])
    repos = natsort.natsorted([card.get_spec(pl.duel_player) for card in self.repos])
    mset = natsort.natsorted([card.get_spec(pl.duel_player) for card in self.idle_mset])
    idle_set = natsort.natsorted([card.get_spec(pl.duel_player) for card in self.idle_set])
    idle_activate = natsort.natsorted([card.get_spec(pl.duel_player) for card in self.idle_activate])
    if summonable:
      pl.notify(pl._("Summonable in attack position: %s") % ", ".join(summonable))
    if mset:
      pl.notify(pl._("Summonable in defense position: %s") % ", ".join(mset))
    if spsummon:
      pl.notify(pl._("Special summonable: %s") % ", ".join(spsummon))
    if idle_activate:
      pl.notify(pl._("Activatable: %s") % ", ".join(idle_activate))
    if repos:
      pl.notify(pl._("Repositionable: %s") % ", ".join(repos))
    if idle_set:
      pl.notify(pl._("Settable: %s") % ", ".join(idle_set))

  def cardspec_to_ls(self, text):
    if text.startswith('o'):
      text = text[1:]
    r = re.search(r'^([a-z]+)(\d+)', text)
    if not r:
      return (None, None)
    if r.group(1) == 'h':
      l = LOCATION_HAND
    elif r.group(1) == 'm':
      l = LOCATION_MZONE
    elif r.group(1) == 's':
      l = LOCATION_SZONE
    elif r.group(1) == 'g':
      l = LOCATION_GRAVE
    elif r.group(1) == 'x':
      l = LOCATION_EXTRA
    elif r.group(1) == 'r':
      l = LOCATION_REMOVED
    else:
      return None, None
    return l, int(r.group(2)) - 1

  def flag_to_usable_cardspecs(self, flag, reverse=False):
    pm = flag & 0xff
    ps = (flag >> 8) & 0xff
    om = (flag >> 16) & 0xff
    os = (flag >> 24) & 0xff
    zone_names = ('m', 's', 'om', 'os')
    specs = []
    for zn, val in zip(zone_names, (pm, ps, om, os)):
      for i in range(8):
        if reverse:
          avail = val & (1 << i) != 0
        else:
          avail = val & (1 << i) == 0
        if avail:
          specs.append(zn + str(i + 1))
    return specs

  def cardlist_info_for_player(self, card, pl):
    spec = card.get_spec(pl.duel_player)
    if card.location == LOCATION_DECK:
      spec = pl._("deck")
    cls = (card.controller, card.location, card.sequence)
    if card.controller != pl.duel_player and card.position in (0x8, 0xa) and cls not in self.revealed:
      position = card.get_position(pl)
      return (pl._("{position} card ({spec})")
        .format(position=position, spec=spec))
    name = card.get_name(pl)
    return "{name} ({spec})".format(name=name, spec=spec)

  def show_table(self, pl, player, hide_facedown=False):
    mz = self.get_cards_in_location(player, LOCATION_MZONE)
    sz = self.get_cards_in_location(player, LOCATION_SZONE)
    if len(mz+sz) == 0:
      pl.notify(pl._("Table is empty."))
      return
    for card in mz:
      s = "m%d: " % (card.sequence + 1)
      if hide_facedown and card.position in (0x8, 0xa):
        s += card.get_position(pl)
      else:
        s += card.get_name(pl) + " "
        s += (pl._("({attack}/{defense}) level {level}")
          .format(attack=card.attack, defense=card.defense, level=card.level))
        s += " " + card.get_position(pl)

        if len(card.xyz_materials):
          s += " ("+pl._("xyz materials: %d")%(len(card.xyz_materials))+")"
        counters = []
        for c in card.counters:
          counter_type = c & 0xffff
          counter_val = (c >> 16) & 0xffff
          counter_type = globals.strings[pl.language]['counter'][counter_type]
          counter_str = "%s: %d" % (counter_type, counter_val)
          counters.append(counter_str)
        if counters:
          s += " (" + ", ".join(counters) + ")"
      pl.notify(s)
    for card in sz:
      s = "s%d: " % (card.sequence + 1)
      if hide_facedown and card.position in (0x8, 0xa):
        s += card.get_position(pl)
      else:
        s += card.get_name(pl) + " "
        s += card.get_position(pl)

        if card.equip_target:

          s += ' ' + pl._('(equipped to %s)')%(card.equip_target.get_spec(pl.duel_player))

        counters = []
        for c in card.counters:
          counter_type = c & 0xffff
          counter_val = (c >> 16) & 0xffff
          counter_type = globals.strings[pl.language]['counter'][counter_type]
          counter_str = "%s: %d" % (counter_type, counter_val)
          counters.append(counter_str)
        if counters:
          s += " (" + ", ".join(counters) + ")"

      pl.notify(s)

  def show_cards_in_location(self, pl, player, location, hide_facedown=False):
    cards = self.get_cards_in_location(player, location)
    if not cards:
      pl.notify(pl._("Table is empty."))
      return
    for card in cards:
      s = card.get_spec(player) + " "
      if hide_facedown and card.position in (0x8, 0xa):
        s += card.get_position(pl)
      else:
        s += card.get_name(pl) + " "
        s += card.get_position(pl)
        if card.type & TYPE_MONSTER:
          s += " " + pl._("level %d") % card.level
      pl.notify(s)

  def show_hand(self, pl, player):
    h = self.get_cards_in_location(player, LOCATION_HAND)
    if not h:
      pl.notify(pl._("Your hand is empty."))
      return
    for c in h:
      pl.notify("h%d: %s" % (c.sequence + 1, c.get_name(pl)))

  def show_score(self, pl):
    player = pl.duel_player
    deck = self.get_cards_in_location(player, LOCATION_DECK)
    odeck = self.get_cards_in_location(1 - player, LOCATION_DECK)
    grave = self.get_cards_in_location(player, LOCATION_GRAVE)
    ograve = self.get_cards_in_location(1 - player, LOCATION_GRAVE)
    hand = self.get_cards_in_location(player, LOCATION_HAND)
    ohand = self.get_cards_in_location(1 - player, LOCATION_HAND)
    removed = self.get_cards_in_location(player, LOCATION_REMOVED)
    oremoved = self.get_cards_in_location(1 - player, LOCATION_REMOVED)
    if pl.watching:
      nick0 = self.players[0].nickname
      nick1 = self.players[1].nickname
      pl.notify(pl._("LP: %s: %d %s: %d") % (nick0, self.lp[player], nick1, self.lp[1 - player]))
      pl.notify(pl._("Hand: %s: %d %s: %d") % (nick0, len(hand), nick1, len(ohand)))
      pl.notify(pl._("Deck: %s: %d %s: %d") % (nick0, len(deck), nick1, len(odeck)))
      pl.notify(pl._("Grave: %s: %d %s: %d") % (nick0, len(grave), nick1, len(ograve)))
      pl.notify(pl._("Removed: %s: %d %s: %d") % (nick0, len(removed), nick1, len(oremoved)))
    else:
      pl.notify(pl._("Your LP: %d Opponent LP: %d") % (self.lp[player], self.lp[1 - player]))
      pl.notify(pl._("Hand: You: %d Opponent: %d") % (len(hand), len(ohand)))
      pl.notify(pl._("Deck: You: %d Opponent: %d") % (len(deck), len(odeck)))
      pl.notify(pl._("Grave: You: %d Opponent: %d") % (len(grave), len(ograve)))
      pl.notify(pl._("Removed: You: %d Opponent: %d") % (len(removed), len(oremoved)))

  def show_info(self, card, pl):
    pln = pl.duel_player
    cs = card.get_spec(pln)
    if card.position in (0x8, 0xa) and (pl.watching or card in self.get_cards_in_location(1 - pln, LOCATION_MZONE) + self.get_cards_in_location(1 - pln, LOCATION_SZONE)):
      pl.notify(pl._("%s: %s card.") % (cs, card.get_position(pl)))
      return
    pl.notify(card.get_info(pl))

  def show_info_cmd(self, pl, spec):
    cards = []
    for i in (0, 1):
      for j in (LOCATION_MZONE, LOCATION_SZONE, LOCATION_GRAVE, LOCATION_REMOVED, LOCATION_HAND, LOCATION_EXTRA):
        cards.extend(card for card in self.get_cards_in_location(i, j) if card.controller == pl.duel_player or card.position not in (0x8, 0xa))
    specs = {}
    for card in cards:
      specs[card.get_spec(pl.duel_player)] = card
    for i, card in enumerate(pl.card_list):
      specs[str(i + 1)] = card
    if spec not in specs:
      pl.notify(pl._("Invalid card."))
      return
    self.show_info(specs[spec], pl)

  def start_debug(self):
    self.debug_mode = True
    lt = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    fn = lt+"_"+self.players[0].nickname+"_"+self.players[1].nickname
    self.debug_fp = open(os.path.join('duels', fn), 'w')
    self.debug(event_type='start', player0=self.players[0].nickname, player1=self.players[1].nickname,
    deck0=self.cards[0], deck1=self.cards[1], seed=self.seed)

  def debug(self, **kwargs):
    if not self.debug_mode:
      return
    s = json.dumps(kwargs)
    self.debug_fp.write(s+'\n')
    self.debug_fp.flush()

  def player_disconnected(self, con):
    if any(pl is None for pl in self.players):
      self.end()
      return
    self.players[con.duel_player] = None
    duels[con.nickname] = weakref.ref(self)
    self.lost_parser = con.parser
    for pl in self.players + self.watchers:
      if pl is None:
        continue
      pl.notify(pl._("%s disconnected, the duel is paused.") % con.nickname)
    for pl in self.players:
      if pl is None:
        continue
      pl.paused_parser = pl.parser
      pl.parser = parser

class TestDuel(Duel):
  def __init__(self):
    super(TestDuel, self).__init__()
    self.cm.register_callback('draw', self.on_draw)

  def on_draw(self, player, cards):
    print("player %d draw %d cards:" % (player, len(cards)))
    for c in cards:
      print(c.name + ": " + c.desc)

if __name__ == '__main__':
  d = TestDuel()
  d.load_deck(0, deck)
  d.load_deck(1, deck)
  d.start()

  while True:
    flag = d.process()
    if flag & 0x10000:
      resp = input()
      if resp.startswith('`'):
        b = binascii.unhexlify(resp[1:])
        d.set_responseb(b)
      else:
        resp = int(resp, 16)
        d.set_responsei(resp)
