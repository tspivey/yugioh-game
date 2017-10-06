import io

def msg_chain_solved(self, data):
  data = io.BytesIO(data[1:])
  count = self.read_u8(data)
  self.cm.call_callbacks('chain_solved', count)
  return data.read()

def chain_solved(self, count):
  self.revealed = {}

MESSAGES = {73: msg_chain_solved}

CALLBACKS = {'chain_solved': chain_solved}
