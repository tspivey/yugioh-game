from babel.dates import format_time
from collections import deque
import datetime
import locale

class Channel:
	# buffer_size: amount of messages stored for history
	def __init__(self, buffer_size=100):
		self.buffer = deque(maxlen = buffer_size)
		self.recipients = []
	
	# derive to add additional checks
	def is_enabled(self, recipient):
		return True

	# derive to add e.g. messages, whenever message sent to ignorant person
	def is_ignoring(self, recipient, sender):
		return sender is not None and sender.nickname in recipient.ignores

	# adds a recipient into the list
	def add_recipient(self, player):
		if player not in self.recipients:
			self.recipients.append(player)
	
	# removes recipient from channel
	def remove_recipient(self, player):
		if self.is_recipient(player):
			self.recipients.remove(player)
	
	# check if its a recipient already
	def is_recipient(self, player):
		return player in self.recipients or player is None

	# derive to produce more individual channel messages
	def format_message(self, recipient, sender, message, params):
		return sender.nickname+": "+message.format(**params)

	# derive to add individual details to buffered entry
	def format_buffer_entry(self, sender, message, params):
		return {'time': datetime.datetime.utcnow(), 'sender': None if not sender else sender.nickname, 'message': message, 'params': params}

	# sends any message and will deliver it to all recipients
	# kwargs will be passed into format_message() and format_buffer_entry()
	# methods as well, so they can be used to format message like with
	# message.format()
	def send_message(self, sender, message, **kwargs):

		if not self.is_recipient(sender):
			return

		for r in self.recipients:
			if not self.is_enabled(r) or self.is_ignoring(r, sender):
				continue
			r.notify(self.format_message(r, sender, message, kwargs))
		
		self.buffer.append(self.format_buffer_entry(sender, message, kwargs))
	
	# formats the message printed in the history
	def format_history_message(self, recipient, buffer_entry):
		return format_time(buffer_entry['time'], format='short', locale=self.get_locale_for_recipient(recipient))+" - "+buffer_entry['sender']+": "+buffer_entry['message'].format(buffer_entry['params'])
	
	# prints the history to a player
	# perform recipient check (player not a recipient, error message)
	def print_history(self, player, amount=30):
		if not self.is_recipient(player):
			player.notify(player._("You currently don't receive messages from this channel, so you may not see the history."))
			return
			
		if len(self.buffer) == 0:
			player.notify(player._("No messages yet."))
			return

		amount = min(len(self.buffer), amount)

		start = len(self.buffer) - amount

		for i in range(start, start+amount):
			player.notify(self.format_history_message(player, self.buffer[i]))

	@staticmethod
	def get_locale_for_recipient(recipient):
		return locale.normalize(recipient.language).split('_')[0]
