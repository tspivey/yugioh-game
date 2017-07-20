from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Unicode, Integer, String, func, DateTime
from passlib.hash import pbkdf2_sha256

Base = declarative_base()

class Account(Base):
	__tablename__ = 'accounts'
	id = Column(Integer, primary_key=True)
	name = Column(Unicode, index=True, unique=True, nullable=False)
	password = Column(String, nullable=False)
	email = Column(String(50))
	created = Column(DateTime, default=func.now())
	last_logged_in = Column(DateTime, default=func.now())

	def set_password(self, password):
		self.password = pbkdf2_sha256.hash(password)

	def check_password(self, password):
		return pbkdf2_sha256.verify(password, self.password)
