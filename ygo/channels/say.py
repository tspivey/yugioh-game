from ..channel import Channel

class Say(Channel):
	def format_message(self, recipient, sender, message, params):
		return recipient._("%s says: %s")%(sender.nickname, message)

	def is_enabled(self, recipient):
		return recipient.say
