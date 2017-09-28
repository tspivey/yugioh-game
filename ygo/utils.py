import collections

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
