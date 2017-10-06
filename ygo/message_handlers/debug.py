import json

def debug(self, **kwargs):
	if not self.debug_mode:
		return
	s = json.dumps(kwargs)
	self.debug_fp.write(s+'\n')
	self.debug_fp.flush()

CALLBACKS = {'debug': debug}
