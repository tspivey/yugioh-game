from ..channel import Channel

class LanguageChat(Channel):
	def __init__(self, lang):
		Channel.__init__(self)
		self.language = lang

	def format_message(self, recipient, sender, message, params):
		return recipient._("%s talks in %s: %s")%(sender.nickname, self.language[0].upper()+self.language[1:], message)

	def is_enabled(self, recipient):
		return recipient.is_language_chat_enabled(self.language)
