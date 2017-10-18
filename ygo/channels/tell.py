from babel.dates import format_time

from ..channel import Channel

class Tell(Channel):
	def is_recipient(self, player):
		return True # needed so everyone can post on here
	
	def format_message(self, recipient, sender, message, params):
		if sender is None:
			return recipient._("You tell %s: %s")%(params['receiving_player'], message)
		else:
			return recipient._("%s tells you: %s")%(sender.nickname, message)
	
	def format_history_message(self, recipient, buffer_entry):
		if buffer_entry['sender'] is None:
			msg = recipient._("You tell %s: %s")%(buffer_entry['params']['receiving_player'], buffer_entry['message'])
		else:
			msg = recipient._("%s tells you: %s")%(buffer_entry['sender'], buffer_entry['message'])
		return format_time(buffer_entry['time'], format='short', locale=self.get_locale_for_recipient(recipient))+" - "+msg
