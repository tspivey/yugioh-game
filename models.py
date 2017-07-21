from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Unicode, Integer, String, func, DateTime, ForeignKey
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
	decks = relationship('Deck')

	def set_password(self, password):
		self.password = pbkdf2_sha256.hash(password)

	def check_password(self, password):
		return pbkdf2_sha256.verify(password, self.password)

class Deck(Base):
	__tablename__ = 'decks'
	id = Column(Integer, primary_key=True)
	account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
	name = Column(Unicode)
	content = Column(Unicode, nullable=False)

	@staticmethod
	def find(session, account, name):
		return session.query(Deck).filter_by(account_id=account.id, name=name).first()
