from ygo import globals

def counters(self, card, type, count, added):

  for pl in self.players+self.watchers:

    stype = globals.strings[pl.language]['counter'][type]

    if added:
       pl.notify(pl._("{amount} counters of type {counter} placed on {card}").format(amount=count, counter=stype, card=card.get_name(pl)))

    else:
       pl.notify(pl._("{amount} counters of type {counter} removed from {card}").format(amount=count, counter=stype, card=card.get_name(pl)))

