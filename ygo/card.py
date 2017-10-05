from .constants import *
from . import globals

class Card(object):
  def __init__(self, code):
    row = globals.server.db.execute('select * from datas where id=?', (code,)).fetchone()
    self.code = code
    self.alias = row['alias']
    self.setcode = row['setcode']
    self.type = row['type']
    self.level = row['level'] & 0xff
    self.lscale = (row['level'] >> 24) & 0xff
    self.rscale = (row['level'] >> 16) & 0xff
    self.attack = row['atk']
    self.defense = row['def']
    self.race = row['race']
    self.attribute = row['attribute']
    self.category = row['category']
    row = globals.server.db.execute('select * from texts where id = ?', (self.code, )).fetchone()
    self.name = row[1]
    self.desc = row[2]
    self.strings = []
    for i in range(3, len(row), 1):
      self.strings.append(row[i])

  def set_location(self, location):
    self.controller = location & 0xff
    self.location = (location >> 8) & 0xff;
    self.sequence = (location >> 16) & 0xff
    self.position = (location >> 24) & 0xff

  def __eq__(self, other):
    return self.code == other.code and self.location == other.location and self.sequence == other.sequence

  def get_name(self, pl):
    name = self.name
    row = pl.cdb.execute('select name from texts where id=?', (self.code,)).fetchone()
    if row:
      return row[0]
    return name

  def get_desc(self, pl):
    desc = self.desc
    row = pl.cdb.execute('select desc from texts where id=?', (self.code,)).fetchone()
    if row:	
      return row[0]
    return desc

  def get_strings(self, pl, code=None):
    row = pl.cdb.execute('select * from texts where id = ?', (code or self.code, )).fetchone()
    if not row:
      return self.strings
    strings = []
    for i in range(3, len(row), 1):
      strings.append(row[i])
    return strings

  def get_effect_description(self, pl, i, existing=False):
    s = ''
    e = False
    if i > 10000:
      code = i >> 4
    else:
      code = self.code
    lstr = self.get_strings(pl, code)

    try:

      if i == 0 or lstr[i-code*16].strip() == '':
        s = pl._("Activate this card.")
      else:
        s = lstr[i-code*16].strip()
        e = True
    except IndexError:
      s = strings[pl.language]['system'].get(i, '')
      if s != '':
        e = True

    if existing and not e:
      s = ''

    return s

  def get_info(self, pl):
    lst = []
    types = []
    t = str(self.type)
    for i in range(26):
      if self.type & (1 << i):
        types.append(globals.strings[pl.language]['system'][1050+i])
    for i in range(7):
      if self.attribute & (1 << i):
        types.append(globals.strings[pl.language]['system'][1010+i])
    for i in range(25):
      if self.race & (1 << i):
        types.append(globals.strings[pl.language]['system'][1020+i])

    lst.append("%s (%s)" % (self.get_name(pl), ", ".join(types)))
    if self.type & TYPE_MONSTER:
      lst.append(pl._("Attack: %d Defense: %d Level: %d") % (self.attack, self.defense, self.level))
    if self.type & TYPE_PENDULUM:
      lst.append(pl._("Pendulum scale: %d/%d") % (self.lscale, self.rscale))
    lst.append(self.get_desc(pl))

    try:

      if self.type & TYPE_XYZ and self.location == LOCATION_MZONE:

        if len(self.xyz_materials):

          lst.append(pl._("attached xyz materials:"))

          for i in range(len(self.xyz_materials)):
            lst.append(str(i+1)+": "+self.xyz_materials[i].get_name(pl))

        else:

          lst.append(pl._("no xyz materials attached"))


    except AttributeError:
      pass

    return "\n".join(lst)

  def get_position(self, pl):
    if self.position == POS_FACEUP_ATTACK:
      return pl._("face-up attack")
    elif self.position == POS_FACEDOWN_ATTACK:
      return pl._("face-down attack")
    elif self.position == POS_FACEUP_DEFENSE:
      return pl._("face-up defense")
    elif self.position == POS_FACEUP:
      return pl._("face-up")
    elif self.position == POS_FACEDOWN_DEFENSE:
      return pl._("face-down defense")
    elif self.position == POS_FACEDOWN:
      return pl._("face down")

  def get_spec(self, player):
    s = ""
    if self.controller != player:
      s += "o"
    if self.location == LOCATION_HAND:
      s += "h"
    elif self.location == LOCATION_MZONE:
      s += "m"
    elif self.location == LOCATION_SZONE:
      s += "s"
    elif self.location == LOCATION_GRAVE:
      s += "g"
    elif self.location == LOCATION_EXTRA:
      s += "x"
    elif self.location == LOCATION_REMOVED:
      s += "r"
    s += str(self.sequence + 1)
    return s
