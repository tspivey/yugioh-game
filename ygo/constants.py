__ = lambda s: s

ATTRIBUTES = ('Earth', 'Water', 'Fire', 'Wind', 'Light', 'Dark', 'Divine')

COMMAND_SUBSTITUTIONS = {
	"'": "say",
	".": "chat",
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

LOCATION_DECK = 1
LOCATION_HAND = 2
LOCATION_MZONE = 4
LOCATION_SZONE = 8
LOCATION_GRAVE = 0x10
LOCATION_REMOVED = 0x20
LOCATION_EXTRA = 0x40
LOCATION_OVERLAY = 0x80

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

RACES = (
	"Warrior", "Spellcaster", "Fairy", "Fiend", "Zombie",
	"Machine", "Aqua", "Pyro", "Rock", "Wind Beast",
	"Plant", "Insect", "Thunder", "Dragon", "Beast",
	"Beast Warrior", "Dinosaur", "Fish", "Sea Serpent", "Reptile",
	"Psycho", "Divine", "Creator god", "Wyrm", "Cyberse",
)

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

TYPE_MONSTER = 0x1
TYPE_FUSION = 0x40
TYPE_SYNCHRO = 0x2000
TYPE_XYZ = 0x800000
TYPE_PENDULUM = 0x1000000
TYPE_LINK = 0x4000000
