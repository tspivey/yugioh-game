from cffi import FFI
ffibuilder = FFI()
ffibuilder.set_source("_duel",
	r"""
#include "ocgapi.h"
#include "card.h"
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
""")

if __name__ == "__main__":
	ffibuilder.compile(verbose=True)
