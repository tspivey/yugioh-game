import gettext
import re

from . import globals

def set_language(pl, language):
	if language == 'en':
		pl.cdb = globals.server.db
		pl._ = gettext.NullTranslations().gettext
		pl.language = 'en'
	elif language == 'de':
		pl.cdb = globals.german_db
		pl._ = gettext.translation('game', 'locale', languages=['de'], fallback=True).gettext
		pl.language = 'de'
	elif language == 'ja':
		pl.cdb = globals.japanese_db
		pl._ = gettext.translation('game', 'locale', languages=['ja'], fallback=True).gettext
		pl.language = 'ja'
	elif language == 'es':
		pl.cdb = globals.spanish_db
		pl._ = gettext.translation('game', 'locale', languages=['es'], fallback=True).gettext
		pl.language = 'es'

def parse_strings(filename):
	res = {}
	with open(filename, 'r', encoding='utf-8') as fp:
		for line in fp:
			line = line.rstrip('\n')
			if not line.startswith('!'):
				continue
			type, id, s = line[1:].split(' ', 2)
			if id.startswith('0x'):
				id = int(id, 16)
			else:
				id = int(id)
			if type not in res:
				res[type] = {}
			res[type][id] = s.replace('\xa0', ' ')
	return res
