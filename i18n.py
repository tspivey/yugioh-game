import gettext
import duel as dm
import game

def set_language(con, language):
	if language == 'en':
		con.cdb = dm.db
		con._ = gettext.NullTranslations().gettext
		con.language = 'en'
	elif language == 'de':
		con.cdb = game.german_db
		con._ = gettext.translation('game', 'locale', languages=['de'], fallback=True).gettext
		con.language = 'de'
	elif language == 'ja':
		con.cdb = game.japanese_db
		con._ = gettext.translation('game', 'locale', languages=['ja'], fallback=True).gettext
		con.language = 'ja'
	elif language == 'es':
		con.cdb = game.spanish_db
		con._ = gettext.translation('game', 'locale', languages=['es'], fallback=True).gettext
		con.language = 'es'
