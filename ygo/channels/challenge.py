from babel.dates import format_time
import copy

from ..channel import Channel, NO_ESCAPE

class Challenge(Channel):
	def __init__(self):
		Channel.__init__(self, flags = NO_ESCAPE)

	def format_message(self, recipient, sender, message, params):
		return 'Challenge: '+recipient._(message).format(**self.resolve_closures(recipient, params))
	
	def is_enabled(self, recipient):
		return recipient.challenge
	
	def format_history_message(self, recipient, buffer_entry):
		return format_time(buffer_entry['time'], format='short', locale=recipient.get_locale())+' - '+recipient._(buffer_entry['message']).format(**self.resolve_closures(recipient, buffer_entry['params']))

	def resolve_closures(self, recipient, params):
		params = copy.copy(params)
		for k in params.keys():
			if type(params[k]) is not str:
				params[k] = params[k](recipient)
		return params
