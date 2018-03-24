import gettext
import glob
import os.path
import sqlite3

from .exceptions import LanguageError
from .utils import get_root_directory

# a class which manages all resources which are language dependent
# should be singleton
# allows for on-the-fly reloads as well
# can also contain one primary language (will probably be english most of the time)
# allows for quick switching of primary language, to take e.g. the german database
# with higher priority than the english one
class LanguageHandler:
	languages = dict()
	primary_language = ''

	def add(self, lang, short, path = None):
		lang = lang.lower()
		short = short.lower()
		print("Adding language "+lang+" with shortage "+short)
		try:
			l = {'short': short}
			if path is None:
				path = os.path.join(get_root_directory(), 'locale', short)
			l['path'] = path
			l['db'] = self.__connect_database(path)
			l['strings'] = self.__parse_strings(os.path.join(path, 'strings.conf'))
			l['motd'] = self.__load_motd(path)
			self.languages[lang] = l
		except LanguageError as e:
			print("Error adding language "+lang+": "+str(e))

	def __connect_database(self, path):
		if not os.path.exists(os.path.join(path, 'cards.cdb')):
			raise LanguageError("cards.cdb not found")
		cdb = sqlite3.connect(os.path.join(path, 'cards.cdb'))
		cdb.row_factory = sqlite3.Row
		cdb.create_function('UPPERCASE', 1, lambda s: s.upper())
		extending_dbs = glob.glob(os.path.join(path, '*.cdb'))
		count = 0
		for p in extending_dbs:
			if os.path.relpath(p, os.path.dirname(p)) == 'cards.cdb':
				continue
			count += 1
			cdb.execute("ATTACH ? as new", (p, ))
			cdb.execute("INSERT OR REPLACE INTO datas SELECT * FROM new.datas")
			cdb.execute("INSERT OR REPLACE INTO texts SELECT * FROM new.texts")
			cdb.execute("DETACH new")
		print("Merged {count} databases into cards.cdb".format(count = count))
		return cdb

	def __parse_strings(self, filename):
		if not os.path.exists(filename):
			raise LanguageError("strings.conf not found")
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

	def is_loaded(self, lang):
		return lang in self.languages

	def set_primary_language(self, lang):
		if not self.is_loaded(lang):
			raise LanguageError("language "+lang+" not loaded and can therefore not be set as primary language")
		self.primary_language = lang

	def get_language(self, lang):
		try:
			return self.languages[lang]
		except KeyError:
			raise LanguageError("language not found")

	def get_motd(self, lang):
		if self.get_language[lang]['motd'] == '':
			return self.primary_motd
		return self.get_language(lang)['motd']

	def __load_motd(self, path):
		if not os.path.exists(os.path.join(path, 'motd.txt')):
			return ""
		return open(os.path.join(path, 'motd.txt'), 'r', encoding='utf-8').read()

	def _(self, lang, text):
		if lang == 'english':
			return gettext.NullTranslations().gettext(text)
		else:
			return gettext.translation('game', 'locale', languages=[self.get_language(lang)['short']], fallback=True).gettext(text)

	def get_short(self, lang):
		return self.get_language(lang)['short']

	def get_available_languages(self):
		return self.languages.keys()

	def get_long(self, short):
		short = short.lower()
		for l in self.languages.keys():
			if self.languages[l]['short'] == short:
				return l
		return self.primary_language

	def get_strings(self, lang):
		return self.get_language(lang)['strings']

	# reloads all available languages
	def reload(self):
		backup = self.languages
		for l in self.languages.keys():
			self.languages[l]['db'].close()
		self.languages = dict()
		try:
			for l in backup.keys():
				self.add(l, backup[l]['short'], backup[l]['path'])
			return True
		except LanguageError as e:
			self.languages = backup
			return str(e)

	@property
	def primary_database(self):
		return self.get_language(self.primary_language)['db']

	@property
	def primary_motd(self):
		return self.get_language(self.primary_language)['motd']
