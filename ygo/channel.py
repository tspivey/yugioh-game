from babel.dates import format_time
from collections import deque
import datetime

NO_SEND_CHECK = 0x1
NO_ESCAPE = 0x2

class Channel:

	_unformatter = str.maketrans({'{': '{{', '}': '}}'})
	# buffer_size: amount of messages stored for history
	# flags: possible values
	#   NO_SEND_CHECK - don't check if player is a recipient of this channel when
	#                   sending a message
	#   NO_ESCAPE - don't escape strings sent to this channel
	def __init__(self, buffer_size=100, flags = 0):
		self.buffer = deque(maxlen = buffer_size)
		self.flags = flags
		self.recipients = []
	
	# derive to add additional checks
	def is_enabled(self, recipient):
		return True

	# derive to add e.g. messages, whenever message sent to ignorant person
	def is_ignoring(self, recipient, sender):
		return recipient.is_ignoring(sender)

	# adds a recipient into the list
	def add_recipient(self, player):
		if not self.is_recipient(player):
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

		if not self.flags & NO_SEND_CHECK and not self.is_recipient(sender):
			return

		if not self.flags & NO_ESCAPE:
			message = message.translate(self._unformatter)

		success = 0
		
		for r in self.recipients:
			if not self.is_enabled(r) or self.is_ignoring(r, sender):
				continue
			r.notify(self.format_message(r, sender, message, kwargs).format())
			success += 1
		
		self.buffer.append(self.format_buffer_entry(sender, message, kwargs))
		
		return success
	
	# formats the message printed in the history
	def format_history_message(self, recipient, buffer_entry):
		return format_time(buffer_entry['time'], format='short', locale=recipient.get_locale())+" - "+buffer_entry['sender']+": "+buffer_entry['message'].format(buffer_entry['params'])
	
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
