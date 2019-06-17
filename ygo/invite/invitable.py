from abc import ABC, abstractmethod

class Invitable(ABC):

	@property
	@abstractmethod
	def invitable_id(self):
		pass
