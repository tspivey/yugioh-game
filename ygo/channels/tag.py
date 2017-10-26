from babel.dates import format_time

from ..channel import Channel

class Tag(Channel):
	def format_message(self, recipient, sender, message, params):
		return recipient._("%s tags: %s")%(sender.nickname, message)

	def format_history_message(self, recipient, buffer_entry):
		return format_time(buffer_entry['time'], format='short', locale=recipient.get_locale())+' - '+buffer_entry['sender']+': '+buffer_entry['message']

	def is_ignoring(self, recipient, sender):
		return False
