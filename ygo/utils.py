import collections

from _duel import ffi, lib

def parse_lflist(filename):
  lst = collections.OrderedDict()
  with open(filename, 'r', encoding='utf-8') as fp:
    for line in fp:
      line = line.rstrip('\n')
      if not line or line.startswith('#'):
        continue
      elif line.startswith('!'):
        section = line[1:]
        lst[section] = lst.get(section, {})
      else:
        code, num_allowed, *extra = line.split(' ', 2)
        code = int(code)
        num_allowed = int(num_allowed)
        lst[section][code] = num_allowed
  return lst

def process_duel(d):
  while d.started:
    res = d.process()
    if res & 0x20000:
      break
    elif res & 0x10000 and res != 0x10000:
      if d.keep_processing:
        d.keep_processing = False
        continue
      break

def process_duel_replay(duel):
  res = lib.process(duel.duel)
  l = lib.get_message(duel.duel, ffi.cast('byte *', duel.buf))
  data = ffi.unpack(duel.buf, l)
  cb = duel.cm.callbacks
  duel.cm.callbacks = collections.defaultdict(list)
  def tp(t):
    duel.tp = t
  duel.cm.register_callback('new_turn', tp)
  def recover(player, amount):
    duel.lp[player] += amount
  def damage(player, amount):
    duel.lp[player] -= amount
  duel.cm.register_callback('recover', recover)
  duel.cm.register_callback('damage', damage)
  duel.process_messages(data)
  duel.cm.callbacks = cb
  return data

def check_sum(cards, acc):
  if acc < 0:
    return False
  if not cards:
    return acc == 0
  l = cards[0].param
  l1 = l & 0xffff
  l2 = l >> 16
  nc = cards[1:]
  res1 = check_sum(nc, acc - l1)
  if l2 > 0:
    res2 = check_sum(nc, acc - l2)
  else:
    res2 = False
  return res1 or res2

def parse_ints(text):
  ints = []
  try:
    for i in text.split():
      ints.append(int(i))
  except ValueError:
    pass
  return ints
