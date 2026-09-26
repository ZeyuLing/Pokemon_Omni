#ifndef OMNI_GBA_MUSIC_H
#define OMNI_GBA_MUSIC_H
#include "omni/presentation.h"
void omni_gba_music_init(void);
uint16_t omni_gba_clock(void);
void omni_gba_music_request(uint8_t track);
void omni_gba_sound_select(void);
uint16_t omni_gba_input_pressed(void);
void omni_gba_input_clear(void);
uint32_t omni_gba_music_samples(void);
uint32_t omni_gba_music_loops(void);
uint32_t omni_gba_music_block(void);
uint8_t omni_gba_music_track(void);
#endif
