#ifdef NDEBUG
#undef NDEBUG
#endif
#ifdef OMNI_TEST_WASM
static unsigned failure_line;
unsigned test_failure_line(void){return failure_line;}
#define assert(condition) do { if(!(condition)){failure_line=__LINE__;__builtin_trap();} } while(0)
#define puts(...) ((void)0)
#define main omni_gba_host_test
#else
#include <assert.h>
#include <stdio.h>
#endif
#include "omni/memory.h"
#include "pokedex_game.h"
#include "catalog.h"
#include "gba_data.h"
/* Rendering is deliberately not invoked in this host storage-contract test. */
const GbaInfo gba_info[1]={{0}};
const GbaMove gba_moves[1]={{0}};
const GbaPlanText gba_plan_text[1]={{0}};
const GbaExtra gba_extra[1]={{0}};
const uint32_t gba_variants[1][8]={{0}};
const uint16_t gba_learnsets[1]={0},gba_plan_indexes[1]={0};
const char *const gba_move_sources[1]={""};
const char *const gba_move_sources_readable[1]={""};
const unsigned char gba_art[1]={0},gba_font[1]={0};
const GbaGlyph gba_glyphs[1]={{0}},gba_small_glyphs[1]={{0}};
const unsigned gba_glyph_count=0,gba_small_glyph_count=0;
static uint8_t saved[12288];
static size_t saved_length;
static int writes,fail;
static int save(const uint8_t *bytes,size_t length,void *context){
 assert(context==&writes);++writes;if(fail)return 0;
 memcpy(saved,bytes,length);saved_length=length;return 1;
}
int main(void){
 uint8_t flags[OMNI_CATALOG_ENTRY_COUNT]={0};
 OmniDexState state={flags,OMNI_CATALOG_ENTRY_COUNT};
 uint32_t id=omni_pokedex_catalog.entries[0].id;
 unsigned i;
 assert(omni_game_dex_bind(state,0,&writes)==OMNI_DEX_ARGUMENT);
 assert(omni_game_dex_bind(state,save,&writes)==OMNI_DEX_OK);
 assert(omni_game_dex_event(id,OMNI_DEX_REGISTERED)==OMNI_DEX_OK);
 assert(writes==1&&flags[0]==3&&saved_length==21);
 memset(flags,0,sizeof(flags));assert(omni_game_dex_restore(saved,saved_length)==OMNI_DEX_OK);assert(flags[0]==3);
 saved[20]^=1;assert(omni_game_dex_restore(saved,saved_length)==OMNI_DEX_BAD_SAVE);assert(flags[0]==3);
 fail=1;assert(omni_game_dex_event(id,OMNI_DEX_UNLOCKED)==OMNI_GAME_DEX_SAVE_FAILED);assert(flags[0]==7);
 fail=0;assert(omni_game_dex_event(id,OMNI_DEX_UNLOCKED)==OMNI_DEX_OK);assert(writes==3);
 for(i=0;i<OMNI_CATALOG_ENTRY_COUNT;++i)if(omni_pokedex_catalog.entries[i].research_only){assert(omni_game_dex_event(omni_pokedex_catalog.entries[i].id,OMNI_DEX_REGISTERED)==OMNI_DEX_RESEARCH);break;}
 assert(writes==3);
 puts("PASS: host-owned state, save callback, atomic corrupt import, failed-save retry and research gate; no standalone SRAM access");
 return 0;
}
