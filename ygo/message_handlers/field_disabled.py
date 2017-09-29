def field_disabled(self, locations):
  specs = self.flag_to_usable_cardspecs(locations, reverse=True)
  opspecs = []
  for spec in specs:
    if spec.startswith('o'):
      opspecs.append(spec[1:])
    else:
      opspecs.append('o'+spec)
  self.players[0].notify(self.players[0]._("Field locations %s are disabled.") % ", ".join(specs))
  self.players[1].notify(self.players[1]._("Field locations %s are disabled.") % ", ".join(opspecs))
