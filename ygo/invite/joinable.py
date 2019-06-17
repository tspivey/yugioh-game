from .invitable import Invitable

class Joinable:
	def __init__(self):
		self.__invitations = []

	def can_join(self, obj):

		if not isinstance(obj, Invitable):
			return False

		if obj.invitable_id not in self.__invitations:
			return False

		return True

	def join(self, obj):

		if not self.can_join(obj):
			return False

		self.__invitations.remove(obj.invitable_id)

		return True

	def invite(self, obj):
	
		if not isinstance(obj, Invitable):
			return False

		if obj.invitable_id in self.__invitations:
			return False

		self.__invitations.append(obj.invitable_id)
		
		return True
