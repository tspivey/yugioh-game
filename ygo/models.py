from alembic.config import Config as alembic_config
from alembic import command as alembic_command

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Unicode, Integer, String, func, DateTime, ForeignKey, Index, collate, Boolean, UniqueConstraint
from sqlalchemy import PrimaryKeyConstraint
from passlib.hash import pbkdf2_sha256

Base = declarative_base()

class Statistics(Base):
	__tablename__ = 'statistics'
	account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
	opponent_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
	win = Column(Integer, nullable=False, default='0')
	lose = Column(Integer, nullable=False, default='0')
	draw = Column(Integer, nullable=False, default='0')
	giveup = Column(Integer, nullable=False, default='0')
	account = relationship('Account', foreign_keys=[account_id])
	opponent = relationship('Account', foreign_keys=[opponent_id])
	__table_args__ = (
		PrimaryKeyConstraint('account_id', 'opponent_id'),
		Index('account_statistics', 'account_id', 'opponent_id', unique=True),
	)

class Account(Base):
	__tablename__ = 'accounts'
	id = Column(Integer, primary_key=True)
	name = Column(Unicode, index=True, unique=True, nullable=False)
	password = Column(String, nullable=False)
	email = Column(String(50))
	created = Column(DateTime, default=func.now())
	last_logged_in = Column(DateTime, default=func.now())
	language = Column(Unicode, nullable=False, default='en')
	encoding = Column(Unicode, nullable=False, default='utf-8')
	is_admin = Column(Boolean, nullable=False, default=False)
	decks = relationship('Deck', backref = "account")
	ignores = relationship('Ignore', cascade='all, delete-orphan', foreign_keys='Ignore.account_id')
	duel_rules = Column(Integer, nullable=False, default=5)
	banlist = Column(String(50), nullable = False, default = 'tcg')
	ip_address = Column(String(100), nullable=False, default='')
	banned = Column(Boolean, nullable=False, default=False)
	statistics = relationship('Statistics', cascade='all, delete-orphan', foreign_keys=[Statistics.account_id])

	def set_password(self, password):
		self.password = pbkdf2_sha256.hash(password)

	def check_password(self, password):
		return pbkdf2_sha256.verify(password, self.password)

class Deck(Base):
	__tablename__ = 'decks'
	id = Column(Integer, primary_key=True)
	account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
	name = Column(Unicode(collation='NOCASE'), nullable=False)
	content = Column(Unicode, nullable=False)
	public = Column(Boolean, nullable=False, default=False)
	__table_args__ = (
		Index('decks_account_name', 'account_id', 'name'),
	)

	@staticmethod
	def find(session, account, name):
		return session.query(Deck).filter_by(account_id=account.id, name=name).first()

	@staticmethod
	def find_public(session, account, name):
		return session.query(Deck).filter_by(account_id=account.id, name=name, public = True).first()

class Ignore(Base):
	__tablename__ = 'ignores'
	account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
	ignored_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
	ignored_account = relationship('Account', foreign_keys=[ignored_account_id])
	__table_args__ = (
		PrimaryKeyConstraint('account_id', 'ignored_account_id'),
	)

def setup():
	global Base
	engine = create_engine('sqlite:///game.db')
	Base.metadata.bind = engine
	Session = sessionmaker(bind=engine)
	Base.metadata.create_all()

	# stamp the database with the latest version tag
	alembic_cfg = alembic_config("alembic.ini")
	alembic_cfg.attributes['configure_logger'] = False
	alembic_command.stamp(alembic_cfg, "head")

	return Session
