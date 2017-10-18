from ..channel import Channel

class Chat(Channel):
	def format_message(self, recipient, sender, message):
		return recipient._("%s chats: %s")%(sender.nickname, message)

	def is_enabled(self, recipient):
		return recipient.chat
