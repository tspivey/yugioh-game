import struct

from ygo.constants import PHASES

def msg_new_phase(self, data):
	phase = struct.unpack('h', data[1:])[0]
	self.cm.call_callbacks('phase', phase)
	return b''

def phase(self, phase):
	phase_str = PHASES.get(phase, str(phase))
	for pl in self.players + self.watchers:
		pl.notify(pl._('entering %s.') % pl._(phase_str))
	self.current_phase = phase

MESSAGES = {41: msg_new_phase}

CALLBACKS = {'phase': phase}