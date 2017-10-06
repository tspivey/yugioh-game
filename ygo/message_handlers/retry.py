def msg_retry(self, buf):
  print("retry")
  return buf[1:]

MESSAGES = {1: msg_retry}
