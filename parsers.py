import os
import re
from sqlalchemy import func
from attr import attrs, attrib
import gsb
import game
import models
import i18n

command_substitutions = {
	"'": "say",
	".": "chat",
}

parser = gsb.Parser(command_substitutions=command_substitutions)
duel_parser = gsb.Parser(command_substitutions=command_substitutions)

class LoginParser(gsb.Parser):

	nickname_re = re.compile(r'^[A-Za-z][a-zA-Z0-9]+$')

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
			caller.connection.notify("Plese enter a nickname. Your nickname is what you will be known by while playing.")
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
			game.server.disconnect(caller.connection)

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
			return self.prompt("Invalid email address.")
		caller.connection.account.email = caller.text.strip()
		caller.connection.session.add(caller.connection.account)
		caller.connection.session.commit()
		caller.connection.notify("Account created.")
		self.login(caller.connection, caller.connection.account)

	def find_account(self, session, nickname):
		return session.query(models.Account).filter_by(name=nickname).first()

	def login(self, connection, account):
		i18n.set_language(connection, account.language)
		if not connection.web:
			connection.encode_args = (account.encoding, 'replace')
			connection.decode_args = (account.encoding, 'ignore')
		if account.name.lower() in game.players:
			old_con = game.players[account.name.lower()]
			connection.notify(connection._("Disconnecting old connection."))
			game.server.connections.remove(old_con)
			game.server.on_disconnect(gsb.Caller(connection=old_con))
			game.server.disconnect(old_con)
		connection.account = account
		connection.nickname = account.name
		connection.parser = parser
		connection.is_admin = account.is_admin
		account.last_logged_in = func.now()
		connection.session.commit()
		for pl in game.players.values():
			pl.notify(pl._("%s logged in.") % connection.nickname)
		game.players[connection.nickname.lower()] = connection
		motd_file = os.path.join('locale', connection.language, 'motd.txt')
		if not os.path.exists(motd_file):
			motd_file = os.path.join('locale', 'en', 'motd.txt')
		if os.path.exists(motd_file):
			with open(motd_file, 'r') as fp:
				connection.notify(fp.read())

class YesOrNo(gsb.Parser):

	def __init__(self, question, yes=None, no=None, restore_parser=None, *args, **kwargs):
		self.question = question
		self.yes = yes
		self.no = no
		self.restore_parser = restore_parser
		super().__init__(*args, **kwargs)

	def on_attach(self, connection, old_parser):
		for key in duel_parser.commands.keys():
			self.commands[key] = duel_parser.commands[key]
		connection.notify(self.question)

	def huh(self, caller):
		if caller.text.lower().startswith('y'):
			self.yes(caller)
		elif caller.text.lower().startswith('n'):
			self.no(caller)
		else:
			caller.connection.notify(caller.connection._("Please enter y or n."))
			caller.connection.notify(self.question)
			return
		caller.connection.parser = self.restore_parser
