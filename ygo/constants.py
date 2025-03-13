try:
	from enum import Flag, auto, unique, IntFlag
except ImportError:
	from aenum import Flag, auto, unique, IntFlag

__ = lambda s: s

AMOUNT_ATTRIBUTES = 7
AMOUNT_RACES = 26

ATTRIBUTES_OFFSET = 1010

COMMAND_SUBSTITUTIONS = {
	"'": "say",
	".": "chat",
	'"': "talk"
}

LINK_MARKERS = {
	0o0001: __("bottom left"),
	0o0002: __("bottom"),
	0o0004: __("bottom right"),
	0o0010: __("left"),
	0o0040: __("right"),
	0o0100: __("top left"),
	0o0200: __("top"),
	0o0400: __("top right")
}

@unique
class LOCATION(IntFlag):
	DECK = 0x1
	HAND = 0x2
	MZONE = 0x4
	SZONE = 0x8
	GRAVE = 0x10
	REMOVED = 0x20
	EXTRA = 0x40
	OVERLAY = 0x80
	ONFIELD = MZONE | SZONE
	FZONE = 0x100
	PZONE = 0x200

PHASES = {
	1: __('draw phase'),
	2: __('standby phase'),
	4: __('main1 phase'),
	8: __('battle start phase'),
	0x10: __('battle step phase'),
	0x20: __('damage phase'),
	0x40: __('damage calculation phase'),
	0x80: __('battle phase'),
	0x100: __('main2 phase'),
	0x200: __('end phase'),
}

@unique
class POSITION(IntFlag):
	FACEUP_ATTACK = 0x1
	FACEDOWN_ATTACK = 0x2
	FACEUP_DEFENSE = 0x4
	FACEUP = FACEUP_ATTACK | FACEUP_DEFENSE
	FACEDOWN_DEFENSE = 0x8
	FACEDOWN = FACEDOWN_ATTACK | FACEDOWN_DEFENSE
	ATTACK = FACEUP_ATTACK | FACEDOWN_ATTACK
	DEFENSE = FACEUP_DEFENSE | FACEDOWN_DEFENSE

RACES_OFFSET = 1020

RE_BANLIST = r"([0-9]+\.[0-9]+\.?[0-9]* ?[a-zA-Z]*)?"
RE_NICKNAME = r'^([A-Za-z][a-zA-Z0-9]+)$'

@unique
class QUERY(IntFlag):
	CODE = 0x1
	POSITION = 0x2
	ALIAS = 0x4
	TYPE = 0x8
	LEVEL = 0x10
	RANK = 0x20
	ATTRIBUTE = 0x40
	RACE = 0x80
	ATTACK = 0x100
	DEFENSE = 0x200
	BASE_ATTACK = 0x400
	BASE_DEFENSE = 0x800
	REASON = 0x1000
	REASON_CARD = 0x2000
	EQUIP_CARD = 0x4000
	TARGET_CARD = 0x8000
	OVERLAY_CARD = 0x10000
	COUNTERS = 0x20000
	OWNER = 0x40000
	STATUS = 0x80000
	LSCALE = 0x200000
	RSCALE = 0x400000
	LINK = 0x800000
	IS_HIDDEN = 0x1000000
	COVER = 0x2000000
	END = 0x80000000

@unique
class TYPE(IntFlag):
	MONSTER = 0x1
	SPELL = 0x2
	TRAP = 0x4
	NORMAL = 0x10
	EFFECT = 0x20
	FUSION = 0x40
	RITUAL = 0x80
	TRAPMONSTER = 0x100
	SPIRIT = 0x200
	UNION = 0x400
	DUAL = 0x800
	TUNER = 0x1000
	SYNCHRO = 0x2000
	TOKEN = 0x4000
	QUICKPLAY = 0x10000
	CONTINUOUS = 0x20000
	EQUIP = 0x40000
	FIELD = 0x80000
	COUNTER = 0x100000
	FLIP = 0x200000
	TOON = 0x400000
	XYZ = 0x800000
	PENDULUM = 0x1000000
	SPSUMMON = 0x2000000
	LINK = 0x4000000
	# for this mud only
	EXTRA = XYZ | SYNCHRO | FUSION | LINK

@unique
class REASON(IntFlag):
	DESTROY = 0x1
	RELEASE = 0x2
	TEMPORARY = 0x4
	MATERIAL = 0x8
	SUMMON = 0x10
	BATTLE = 0x20
	EFFECT = 0x40
	COST = 0x80
	ADJUST = 0x100
	LOST_TARGET = 0x200
	RULE = 0x400
	SPSUMMON = 0x800
	DISSUMMON = 0x1000
	FLIP = 0x2000
	DISCARD = 0x4000
	RDAMAGE = 0x8000
	RRECOVER = 0x10000
	RETURN = 0x20000
	FUSION = 0x40000
	SYNCHRO = 0x80000
	RITUAL = 0x100000
	XYZ = 0x200000
	REPLACE = 0x1000000
	DRAW = 0x2000000
	REDIRECT = 0x4000000
	LINK = 0x10000000
	
@unique
class INFORM(Flag):
	PLAYER = auto()
	OPPONENT = auto()
	TAG_PLAYER = auto()
	TAG_OPPONENT = auto()
	WATCHERS_PLAYER = auto()
	WATCHERS_OPPONENT = auto()
	WATCHERS = WATCHERS_PLAYER | WATCHERS_OPPONENT
	PLAYERS = PLAYER | OPPONENT
	TAG_PLAYERS = TAG_PLAYER | TAG_OPPONENT
	ALL_PLAYERS = PLAYERS | TAG_PLAYERS
	ALLIES = PLAYER | TAG_PLAYER | WATCHERS_PLAYER
	OPPONENTS = OPPONENT | TAG_OPPONENT | WATCHERS_OPPONENT
	NON_PLAYERS = TAG_PLAYERS | WATCHERS
	ALL = ALL_PLAYERS | WATCHERS
	OTHER = ALL ^ PLAYER

@unique
class DECK(Flag):
	OWNED = auto()
	OTHER = auto()
	PUBLIC = auto()
	ALL = OWNED | OTHER  # should only be used for admins
	VISIBLE = OWNED | PUBLIC  # default scope for players

@unique
class DuelOptions(IntFlag):
	DUEL_PZONE = 0x800
	DUEL_EMZONE = 0x2000
	DUEL_FSX_MMZONE = 0x4000
	DUEL_TRAP_MONSTERS_NOT_USE_ZONE = 0x8000
	DUEL_TRIGGER_ONLY_IN_LOCATION = 0x20000
	DUEL_MODE_MR5 = (DUEL_PZONE | DUEL_EMZONE | DUEL_FSX_MMZONE | DUEL_TRAP_MONSTERS_NOT_USE_ZONE | DUEL_TRIGGER_ONLY_IN_LOCATION)
