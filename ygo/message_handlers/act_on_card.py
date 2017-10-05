from twisted.internet import reactor

from ygo.duel_reader import DuelReader
from ygo.utils import process_duel
from ygo.parsers.duel_parser import DuelParser

def act_on_card(self, caller, card):
  pl = self.players[self.tp]
  name = card.get_name(pl)
  if card in self.idle_activate:
    card = self.idle_activate[self.idle_activate.index(card)]
  def prompt(menu=True):
    if not menu:
      return pl.notify(DuelReader, action, no_abort=pl._("Invalid command."), prompt=pl._("Select action for {card}").format(card=name), restore_parser=DuelParser)
    pl.notify(name)
    activate_count = self.idle_activate.count(card)
    if card in self.summonable:
      pl.notify("s: "+pl._("Summon this card in face-up attack position."))
    if card in self.idle_set:
      pl.notify("t: "+pl._("Set this card."))
    if card in self.idle_mset:
      pl.notify("m: "+pl._("Summon this card in face-down defense position."))
    if card in self.repos:
      pl.notify("r: "+pl._("reposition this card."))
    if card in self.spsummon:
      pl.notify("c: "+pl._("Special summon this card."))
    if activate_count > 0:
      effect_descriptions = []
      for i in range(activate_count):
        ind = self.idle_activate[self.idle_activate.index(card)+i].extra
        effect_descriptions.append(card.get_effect_description(pl, ind))

      if activate_count == 1:
        pl.notify("v: "+effect_descriptions[0])
      else:
        for i in range(activate_count):
          pl.notify("v"+chr(97+i)+": "+effect_descriptions[i])
    pl.notify("i: "+pl._("Show card info."))
    pl.notify("z: "+pl._("back."))
    pl.notify(DuelReader, action, no_abort=pl._("Invalid command."), prompt=pl._("Select action for {card}").format(card=name), restore_parser=DuelParser)
  def action(caller):
    if caller.text == 's' and card in self.summonable:
      self.set_responsei(self.summonable.index(card) << 16)
    elif caller.text == 't' and card in self.idle_set:
      self.set_responsei((self.idle_set.index(card) << 16) + 4)
    elif caller.text == 'm' and card in self.idle_mset:
      self.set_responsei((self.idle_mset.index(card) << 16) + 3)
    elif caller.text == 'r' and card in self.repos:
      self.set_responsei((self.repos.index(card) << 16) + 2)
    elif caller.text == 'c' and card in self.spsummon:
      self.set_responsei((self.spsummon.index(card) << 16) + 1)
    elif caller.text == 'i':
      self.show_info(card, pl)
      return prompt(False)
    elif caller.text == 'z':
      reactor.callLater(0, self.idle_action, pl)
      return
    elif caller.text.startswith('v'):
      activate_count = self.idle_activate.count(card)
      if len(caller.text)>2 or activate_count == 0 or (len(caller.text) == 1 and activate_count > 1) or (len(caller.text) == 2 and activate_count == 1):
        pl.notify(pl._("Invalid action."))
        prompt()
        return
      index = self.idle_activate.index(card)
      if len(caller.text) == 2:
        # parse the second letter
        try:
          o = ord(caller.text[1])
        except TypeError:
          o = -1
        ad = o - ord('a')
        if not (0 <= ad <= 25) or ad >= activate_count:
          pl.notify(pl._("Invalid action."))
          prompt()
          return
        index += ad
      self.set_responsei((index << 16) + 5)
    else:
      pl.notify(pl._("Invalid action."))
      prompt()
      return
    reactor.callLater(0, process_duel, self)
  prompt()
