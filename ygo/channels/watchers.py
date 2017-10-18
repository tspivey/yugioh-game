from babel.dates import format_time

from ..channel import Channel

class Watchers(Channel):
	def is_enabled(self, recipient):
		return recipient.watch
	
	def format_message(self, recipient, sender, message, params):
		return recipient._(message).format(player = sender.nickname)
	
	def format_history_message(self, recipient, buffer_entry):
		return format_time(buffer_entry['time'], format='short', locale=self.get_locale_for_recipient(recipient))+" - "+recipient._(buffer_entry['message']).format(buffer_entry['sender'])
	
	def is_recipient(self, player):
		return True