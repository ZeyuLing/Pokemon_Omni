#ifndef OMNI_GBA_POKEDEX_GAME_H
#define OMNI_GBA_POKEDEX_GAME_H
#include "omni/pokedex.h"
typedef int (*OmniDexSaveCallback)(const uint8_t *bytes,size_t length,void *context);
enum { OMNI_GAME_DEX_SAVE_FAILED=100 };
/* Bind the host's state and save transaction BEFORE processing events. No SRAM
 * addresses are touched when a host callback is installed. */
int omni_game_dex_bind(OmniDexState state,OmniDexSaveCallback save,void *context);
int omni_game_dex_restore(const uint8_t *bytes,size_t length);
/* Host owns the state. Call with trusted encounter/capture/form-unlock events.
 * The standalone reference cartridge has an explicit separate event-test menu. */
/* SAVE_FAILED retains the event in RAM; the host can retry the same event. */
int omni_game_dex_event(uint32_t entry_id,uint8_t event);
void omni_game_dex_open(void);
uint8_t omni_game_dex_is_open(void);
void omni_game_dex_tick(uint16_t keys);
/* Host-specific appearance; standalone official reference Dex stays unchanged. */
void omni_game_dex_art_override(uint32_t entry_id,const uint16_t *front,const uint16_t *back,const uint16_t *shiny_front,const uint16_t *shiny_back);
const OmniDexState *omni_game_dex_state(void);
#endif
