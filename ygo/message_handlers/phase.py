import io
from twisted.internet import reactor

from ygo.constants import PHASES
from ygo.duel_reader import DuelReader
from ygo.utils import process_duel

def msg_new_phase(self, data):
	data = io.BytesIO(data[1:])
	phase = self.read_u16(data)
	self.cm.call_callbacks('phase', phase)
	return data.read()

def phase(self, phase):
	phase_str = PHASES.get(phase, str(phase))
	for pl in self.players + self.watchers:
		pl.notify(pl._('entering %s.') % pl._(phase_str))
	self.current_phase = phase

MESSAGES = {41: msg_new_phase}

CALLBACKS = {'phase': phase}