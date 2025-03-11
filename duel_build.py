from cffi import FFI
ffibuilder = FFI()
ffibuilder.set_source("_duel",
	r"""
#include "ocgapi.h"
#include "card.h"
#include "duel.h"
#include "field.h"
#include <vector>
int32_t is_declarable(card_data const& cd, const std::vector<uint64_t>& opcodes);
int32_t declarable(card_data *cd, int32_t size, uint32_t *array) {
	std::vector<uint64_t> v;
	for (int i=0; i < size; i++) {
	v.push_back(array[i]);
	}
	return is_declarable(*cd, v);
}
// modified from query_card()
uint32_t query_linked_zone(intptr_t pduel, uint8_t playerid, uint8_t location, uint8_t sequence) {
	if(playerid != 0 && playerid != 1)
		return 0;
	duel* ptduel = (duel*)pduel;
	card* pcard = 0;
	location &= 0x7f;
	if(location & LOCATION_ONFIELD)
		pcard = ptduel->game_field->get_field_card(playerid, location, sequence);
	else {
		card_vector* lst = 0;
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
			for(uint32_t i = 0; i < sequence; ++i, ++cit);
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
include_dirs=['../ygopro-core', './core', '/usr/include/lua5.3'],
extra_compile_args=['-std=c++17'],
extra_link_args=['-Wl,-rpath,.'],
)
ffibuilder.cdef("""
typedef void* OCG_Duel;
typedef long ptr;
typedef uint32_t uint32;
typedef int32_t int32;
typedef uint8_t uint8;
typedef int32_t int32;
typedef uint8_t byte;
typedef uint64_t uint64;
typedef struct OCG_CardData {
        uint32_t code;
        uint32_t alias;
        uint16_t* setcodes;
        uint32_t type;
        uint32_t level;
        uint32_t attribute;
        uint64_t race;
        int32_t attack;
        int32_t defense;
        uint32_t lscale;
        uint32_t rscale;
        uint32_t link_marker;
}OCG_CardData;
typedef struct OCG_Player {
        uint32_t startingLP;
        uint32_t startingDrawCount;
        uint32_t drawCountPerTurn;
}OCG_Player;
typedef void (*OCG_DataReader)(void* payload, uint32_t code, OCG_CardData* data);
typedef int (*OCG_ScriptReader)(void* payload, OCG_Duel duel, const char* name);
typedef void (*OCG_LogHandler)(void* payload, const char* string, int type);
typedef void (*OCG_DataReaderDone)(void* payload, OCG_CardData* data);
typedef struct OCG_NewCardInfo {
        uint8_t team; /* either 0 or 1 */
        uint8_t duelist; /* index of original owner */
        uint32_t code;
        uint8_t con;
        uint32_t loc;
        uint32_t seq;
        uint32_t pos;
}OCG_NewCardInfo;
typedef struct OCG_QueryInfo {
        uint32_t flags;
        uint8_t con;
        uint32_t loc;
        uint32_t seq;
        uint32_t overlay_seq;
}OCG_QueryInfo;
typedef struct OCG_DuelOptions {
        uint64_t seed[4];
        uint64_t flags;
        OCG_Player team1;
        OCG_Player team2;
        OCG_DataReader cardReader;
        void* payload1; /* relayed to cardReader */
        OCG_ScriptReader scriptReader;
        void* payload2; /* relayed to scriptReader */
        OCG_LogHandler logHandler;
        void* payload3; /* relayed to errorHandler */
        OCG_DataReaderDone cardReaderDone;
        void* payload4; /* relayed to cardReaderDone */
        uint8_t enableUnsafeLibraries;
}OCG_DuelOptions;

extern "Python" void card_reader_callback(void *, uint32_t, struct OCG_CardData *);
typedef void (*card_reader)(void *, uint32_t, struct OCG_CardData*);
typedef int (*script_reader)(void *, OCG_Duel, const char *);
typedef uint32 (*message_handler)(intptr_t, uint32);
extern "Python" uint32 message_handler_callback (intptr_t, uint32);
extern "Python" int script_reader_callback(void *, OCG_Duel, const char *);
	extern "Python" void log_handler_callback(void *, char *, int);
	int OCG_CreateDuel(OCG_Duel* out_ocg_duel, OCG_DuelOptions options);
void OCG_DestroyDuel(OCG_Duel ocg_duel);
void OCG_StartDuel(OCG_Duel ocg_duel);
int OCG_DuelProcess(OCG_Duel ocg_duel);
void* OCG_DuelGetMessage(OCG_Duel ocg_duel, uint32_t* length);
void OCG_DuelNewCard(OCG_Duel ocg_duel, OCG_NewCardInfo info);
void OCG_DuelSetResponse(OCG_Duel ocg_duel, const void* buffer, uint32_t length);
int OCG_LoadScript(OCG_Duel ocg_duel, const char* buffer, uint32_t length, const char* name);
uint32_t OCG_DuelQueryCount(OCG_Duel ocg_duel, uint8_t team, uint32_t loc);
void* OCG_DuelQuery(OCG_Duel ocg_duel, uint32_t* length, OCG_QueryInfo info);
void* OCG_DuelQueryLocation(OCG_Duel ocg_duel, uint32_t* length, OCG_QueryInfo info);
void* OCG_DuelQueryField(OCG_Duel ocg_duel, uint32_t* length);
int32 declarable(struct card_data *cd, int32 size, uint32 *array);
""")

if __name__ == "__main__":
	ffibuilder.compile(verbose=True)
