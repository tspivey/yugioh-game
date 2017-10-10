from cffi import FFI
ffibuilder = FFI()
ffibuilder.set_source("_duel",
	r"""
#include "ocgapi.h"
#include "card.h"
#include "duel.h"
#include "field.h"
#include <vector>
int32 is_declarable(card_data const& cd, const std::vector<uint32>& opcode);
int32 declarable(card_data *cd, int32 size, uint32 *array) {
	std::vector<uint32> v;
	for (int i=0; i < size; i++) {
	v.push_back(array[i]);
	}
	return is_declarable(*cd, v);
}
// modified from query_card()
int32 query_linked_zone(ptr pduel, uint8 playerid, uint8 location, uint8 sequence) {
	if(playerid != 0 && playerid != 1)
		return 0;
	duel* ptduel = (duel*)pduel;
	card* pcard = 0;
	location &= 0x7f;
	if(location & LOCATION_ONFIELD)
		pcard = ptduel->game_field->get_field_card(playerid, location, sequence);
	else {
		field::card_vector* lst = 0;
		if(location == LOCATION_HAND )
			lst = &ptduel->game_field->player[playerid].list_hand;
		else if(location == LOCATION_GRAVE )
			lst = &ptduel->game_field->player[playerid].list_grave;
		else if(location == LOCATION_REMOVED )
			lst = &ptduel->game_field->player[playerid].list_remove;
		else if(location == LOCATION_EXTRA )
			lst = &ptduel->game_field->player[playerid].list_extra;
		else if(location == LOCATION_DECK )
			lst = &ptduel->game_field->player[playerid].list_main;
		if(!lst || sequence > lst->size())
			pcard = 0;
		else {
			auto cit = lst->begin();
			for(uint32 i = 0; i < sequence; ++i, ++cit);
			pcard = *cit;
		}
	}
	if(pcard)
		return pcard->get_linked_zone();
	else {
		return 0;
	}
}
""",
libraries = ['ygo'],
library_dirs=['.'],
source_extension='.cpp',
include_dirs=['../ygopro-core'],
extra_compile_args=['-std=c++0x'],
extra_link_args=['-Wl,-rpath,.'],
)
ffibuilder.cdef("""
typedef long ptr;
typedef uint32_t uint32;
typedef int32_t int32;
typedef uint8_t uint8;
typedef int32_t int32;
typedef uint8_t byte;
typedef uint64_t uint64;
struct card_data {
	uint32 code;
	uint32 alias;
	uint64 setcode;
	uint32 type;
	uint32 level;
	uint32 attribute;
	uint32 race;
	int32 attack;
	int32 defense;
	uint32 lscale;
	uint32 rscale;
	uint32 link_marker;
...;
};
extern "Python" uint32 card_reader_callback(uint32, struct card_data *);
typedef uint32 (*card_reader)(uint32, struct card_data*);
void set_card_reader(card_reader f);
typedef byte* (*script_reader)(const char*, int*);
typedef uint32 (*message_handler)(void*, uint32);
extern "Python" uint32 message_handler_callback (void *, int32);
void set_message_handler(message_handler f);
extern "Python" byte *script_reader_callback(const char *, int *);
void set_script_reader(script_reader f);
	ptr create_duel(uint32_t seed);
void start_duel(ptr pduel, int32 options);
void end_duel(ptr pduel);
void get_log_message(ptr pduel, byte* buf);
int32 get_message(ptr pduel, byte* buf);
int32 process(ptr pduel);
void new_card(ptr pduel, uint32 code, uint8 owner, uint8 playerid, uint8 location, uint8 sequence, uint8 position);
void set_player_info(ptr pduel, int32 playerid, int32 lp, int32 startcount, int32 drawcount);
void set_responsei(ptr pduel, int32 value);
void set_responseb(ptr pduel, byte *value);
int32 query_card(ptr pduel, uint8 playerid, uint8 location, uint8 sequence, int32 query_flag, byte* buf, int32 use_cache);
int32 query_field_count(ptr pduel, uint8 playerid, uint8 location);
int32 query_field_card(ptr pduel, uint8 playerid, uint8 location, int32 query_flag, byte* buf, int32 use_cache);
int32 query_linked_zone(ptr pduel, uint8 playerid, uint8 location, uint8 sequence);
int32 declarable(struct card_data *cd, int32 size, uint32 *array);
""")

if __name__ == "__main__":
	ffibuilder.compile(verbose=True)
