from babel.dates import format_time

from ..channel import Channel, NO_SEND_CHECK

class Tell(Channel):
	def __init__(self):
		Channel.__init__(self, flags = NO_SEND_CHECK)
	
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
		return format_time(buffer_entry['time'], format='short', locale=recipient.get_locale())+" - "+msg
