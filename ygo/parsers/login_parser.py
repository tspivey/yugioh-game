import os
import re
from sqlalchemy import func
import gsb

from ..constants import RE_NICKNAME
from .. import globals
from .. import models
from ..player import Player

class login_parser(gsb.Parser):

	nickname_re = re.compile(RE_NICKNAME)

	def on_attach(self, connection, old_parser=None):
		connection.login_state = ("nickname", "Nickname (or new to create a new account):")
		self.prompt(gsb.Caller(connection=connection))

	def huh(self, caller):
		state_fn = getattr(self, "handle_"+caller.connection.login_state[0])
		state_fn(caller)

	def prompt(self, caller, text=None):
		if text:
			caller.connection.notify(text)
		caller.connection.notify(caller.connection.login_state[1])

	def handle_nickname(self, caller):
		if caller.text == 'new':
			caller.connection.notify("Please enter a nickname. Your nickname is what you will be known by while playing.")
			caller.connection.login_state = ("new", "Enter desired nickname:")
			return self.prompt(caller)
		nickname = caller.text.capitalize()
		account = self.find_account(caller.connection.session, nickname)
		if not account:
			return self.prompt(caller, "That account doesn't exist. Type new to create a new account.")
		caller.connection.login_state = ('password', "Password:", account)
		return self.prompt(caller)

	def handle_password(self, caller):
		account = caller.connection.login_state[2]
		if account.check_password(caller.text):
			self.login(caller.connection, account)
		else:
			caller.connection.notify("Wrong password.")
			globals.server.disconnect(caller.connection)

	def handle_new(self, caller):
		if not caller.text:
			return self.prompt(caller)
		if not 3 <= len(caller.text) <= 15:
			return self.prompt(caller, "Nicknames must be between 3 and 15 characters.")
		nickname = caller.text.capitalize()
		if not self.nickname_re.match(nickname):
			return self.prompt(caller, "Nicknames must start with a letter and consist of letters and digits.")
		existing_account = self.find_account(caller.connection.session, nickname)
		caller.connection.session.commit()
		if existing_account:
			return self.prompt(caller, "An account with that name already exists.")
		caller.connection.account = models.Account(name=nickname)
		caller.connection.login_state = ("new_password", "Enter a password for the account:")
		return self.prompt(caller)

	def handle_new_password(self, caller):
		password = caller.text
		if len(password) < 6:
			return self.prompt(caller, "Passwords must be at least 6 characters.")
		caller.connection.account.temp_password = password
		caller.connection.login_state = ("confirm_password", "Please re-enter password:")
		return self.prompt(caller)

	def handle_confirm_password(self, caller):
		if caller.text != caller.connection.account.temp_password:
			caller.connection.notify("Passwords do not match.")
			caller.connection.login_state = ("new_password", "Enter a password for the account:")
			return self.prompt(caller)
		del caller.connection.account.temp_password
		caller.connection.account.set_password(caller.text)
		caller.connection.notify("Please enter your email address. An email address is required in case the game administrators need to contact you.")
		caller.connection.login_state = ("email", "E-mail address:")
		self.prompt(caller)

	def handle_email(self, caller):
		if not caller.text or '@' not in caller.text:
			return self.prompt(caller, "Invalid email address.")
		caller.connection.account.email = caller.text.strip()
		caller.connection.session.add(caller.connection.account)
		caller.connection.session.commit()
		caller.connection.notify("Account created.")
		self.login(caller.connection, caller.connection.account)

	def find_account(self, session, nickname):
		return session.query(models.Account).filter_by(name=nickname).first()

	def login(self, connection, account):
		if not connection.web:
			connection.encode_args = (account.encoding, 'replace')
			connection.decode_args = (account.encoding, 'ignore')
		pl = globals.server.get_player(account.name.lower())
		if pl:
			if pl.connection is not None:
				connection.notify(pl._("Disconnecting old connection."))
				globals.server.connections.remove(pl.connection)
				pl.connection.dont_process = True
				globals.server.disconnect(pl.connection)
				connection.parser = pl.connection.parser
				pl.detach_connection()
				connection.player = pl
				pl.attach_connection(connection)
			else:
				connection.notify(pl._("Reconnecting..."))
				for opl in [p for p in globals.server.get_all_players() if p is not pl]:
					opl.notify(opl._("%s reconnected.")%(pl.nickname))
				connection.player = pl
				pl.attach_connection(connection)
				if pl.duel is not None:
					pl.duel.player_reconnected(pl)
		else:
			connection.player = Player(account.name)
			connection.player.attach_connection(connection)
			connection.player.set_parser('LobbyParser')
			connection.player.is_admin = account.is_admin
			connection.player.set_language(globals.language_handler.get_long(account.language))
			for i in account.ignores:
				connection.player.ignores.add(i.ignored_account.name)
			for opl in globals.server.get_all_players():
				opl.notify(opl._("%s logged in.") % connection.player.nickname)
			globals.server.add_player(connection.player)
			connection.notify(connection.player.motd)
		connection.account = None
		account.last_logged_in = func.now()
		connection.session.commit()

LoginParser = login_parser()
