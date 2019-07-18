from .constants import *
from .exceptions import CardNotFoundError
from . import globals

class Card(object):
	def __init__(self, code):
		row = globals.language_handler.primary_database.execute('select * from datas where id=?', (code,)).fetchone()
		if row is None:
			raise CardNotFoundError("Card %d not found" % code)
		self.data = 0 # additional data fetched in certain cases (see Duel.read_cardlist)
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
		row = globals.language_handler.primary_database.execute('select * from texts where id = ?', (self.code, )).fetchone()
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
			s = pl.strings['system'].get(i, '')
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
				types.append(pl.strings['system'][1050+i])
		for i in range(AMOUNT_ATTRIBUTES):
			if self.attribute & (1 << i):
				types.append(pl.strings['system'][ATTRIBUTES_OFFSET+i])
		for i in range(AMOUNT_RACES):
			if self.race & (1 << i):
				types.append(pl.strings['system'][RACES_OFFSET+i])

		lst.append("%s (%s)" % (self.get_name(pl), ", ".join(types)))
		if self.type & TYPE_MONSTER:
			if self.type & TYPE_LINK:
				lst.append(pl._("Attack: %d Link rating: %d")%(self.attack, self.level))
			elif self.type & TYPE_XYZ:
				lst.append(pl._("Attack: %d Defense: %d Rank: %d") % (self.attack, self.defense, self.level))
			else:
				lst.append(pl._("Attack: %d Defense: %d Level: %d") % (self.attack, self.defense, self.level))
		if self.type & TYPE_PENDULUM:
			lst.append(pl._("Pendulum scale: %d/%d") % (self.lscale, self.rscale))
		elif self.type & TYPE_LINK:
			lst.append(pl._("Link Markers: %s")%(self.get_link_markers(pl)))
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

	def get_link_markers(self, pl):

		lst = []

		for m in LINK_MARKERS.keys():
			if self.defense & m:
				lst.append(pl._(LINK_MARKERS[m]))

		return ', '.join(lst)

	@property
	def extra(self):
		return bool(self.type & (TYPE_XYZ | TYPE_SYNCHRO | TYPE_FUSION | TYPE_LINK))
