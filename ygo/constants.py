try:
	from enum import Flag, auto, unique, IntFlag
except ImportError:
	from aenum import Flag, auto, unique, IntFlag

__ = lambda s: s

AMOUNT_ATTRIBUTES = 7
AMOUNT_RACES = 25

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
	ONFIELD = 0x0c
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

POS_FACEUP_ATTACK = 0x1
POS_FACEDOWN_ATTACK = 0x2
POS_FACEUP_DEFENSE = 0x4
POS_FACEUP = 0x5
POS_FACEDOWN_DEFENSE = 0x8
POS_FACEDOWN = 0xa

RACES_OFFSET = 1020

RE_BANLIST = r"([0-9]+\.[0-9]+\.?[0-9]* ?[a-zA-Z]*)?"
RE_NICKNAME = r'^([A-Za-z][a-zA-Z0-9]+)$'

QUERY_CODE = 1
QUERY_POSITION = 0x2
QUERY_LEVEL = 0x10
QUERY_RANK = 0x20
QUERY_ATTACK = 0x100
QUERY_DEFENSE = 0x200
QUERY_EQUIP_CARD = 0x4000
QUERY_OVERLAY_CARD = 0x10000
QUERY_COUNTERS = 0x20000
QUERY_LINK = 0x800000

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
