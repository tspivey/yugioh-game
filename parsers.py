import os
import re
from sqlalchemy import func
import gsb
import game
import models

command_substitutions = {
	"'": "say",
	".": "chat",
}

parser = gsb.Parser(command_substitutions=command_substitutions)
duel_parser = gsb.Parser(command_substitutions=command_substitutions)

class LoginParser(gsb.Parser):

	nickname_re = re.compile(r'^[A-Za-z][a-zA-Z0-9]+$')

	def on_attach(self, connection, old_parser=None):
		connection.state = ("nickname", "Nickname (or new to create a new account):")
		self.prompt(gsb.Caller(connection=connection))

	def huh(self, caller):
		state_fn = getattr(self, "handle_"+caller.connection.state[0])
		state_fn(caller)

	def prompt(self, caller, text=None):
		if text:
			caller.connection.notify(text)
		caller.connection.notify(caller.connection.state[1])

	def handle_nickname(self, caller):
		if caller.text == 'new':
			caller.connection.notify("Plese enter a nickname. Your nickname is what you will be known by while playing.")
			caller.connection.state = ("new", "Enter desired nickname:")
			return self.prompt(caller)
		nickname = caller.text.capitalize()
		account = self.find_account(caller.connection.session, nickname)
		if not account:
			return self.prompt(caller, "That account doesn't exist. Type new to create a new account.")
		caller.connection.state = ('password', "Password:", account)
		return self.prompt(caller)

	def handle_password(self, caller):
		account = caller.connection.state[2]
		if account.check_password(caller.text):
			self.login(caller.connection, account)
		else:
			caller.connection.notify("Wrong password.")
			game.server.disconnect(caller.connection)

	def handle_new(self, caller):
		if not caller.text:
			return self.prompt(caller)
		if 3 < len(caller.text) > 15:
			return self.prompt(caller, "Nicknames must be between 3 and 15 characters.")
		nickname = caller.text.capitalize()
		if not self.nickname_re.match(nickname):
			return self.prompt(caller, "Nicknames must start with a letter and consist of letters and digits.")
		existing_account = self.find_account(caller.connection.session, nickname)
		caller.connection.session.commit()
		if existing_account:
			return self.prompt(caller, "An account with that name already exists.")
		caller.connection.account = models.Account(name=nickname)
		caller.connection.state = ("new_password", "Enter a password for the account:")
		return self.prompt(caller)

	def handle_new_password(self, caller):
		password = caller.text
		if len(password) < 6:
			return self.prompt(caller, "Passwords must be at least 6 characters.")
		caller.connection.account.temp_password = password
		caller.connection.state = ("confirm_password", "Please re-enter password:")
		return self.prompt(caller)

	def handle_confirm_password(self, caller):
		if caller.text != caller.connection.account.temp_password:
			caller.connection.notify("Passwords do not match.")
			caller.connection.state = ("new_password", "Enter a password for the account:")
			return self.prompt(caller)
		del caller.connection.account.temp_password
		caller.connection.account.set_password(caller.text)
		caller.connection.notify("Please enter your email address. An email address is required in case the game administrators need to contact you.")
		caller.connection.state = ("email", "E-mail address:")
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
		if account.name.lower() in game.players:
			old_con = game.players[account.name.lower()]
			connection.notify("Disconnecting old connection.")
			game.server.connections.remove(old_con)
			game.server.on_disconnect(gsb.Caller(connection=old_con))
			game.server.disconnect(old_con)
		connection.account = account
		connection.nickname = account.name
		connection.parser = parser
		account.last_logged_in = func.now()
		connection.session.commit()
		for pl in game.players.values():
			pl.notify("%s logged in." % connection.nickname)
		game.players[connection.nickname.lower()] = connection
		if os.path.exists("motd.txt"):
			with open('motd.txt', 'r') as fp:
				connection.notify(fp.read())
