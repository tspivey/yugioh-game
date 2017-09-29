from ..constants import PHASES

def phase(self, phase):
  phase_str = PHASES.get(phase, str(phase))
  for pl in self.players + self.watchers:
    pl.notify(pl._('entering %s.') % pl._(phase_str))
  self.current_phase = phase
