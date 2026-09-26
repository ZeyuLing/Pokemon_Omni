#ifndef OMNI_PRESENTATION_H
#define OMNI_PRESENTATION_H
#include <stdint.h>
/* Real-time presentation clock: 64 Hz, independent of simulation steps.
 * All platforms feed elapsed clock ticks, never accelerated game ticks. */
typedef struct {
 uint16_t clock, scene_ticks, music_ticks;
 uint8_t speed, scene, scene_count, playing, skip_prompt, track, note;
 uint32_t music_steps;
} OmniPresentation;
void omni_presentation_init(OmniPresentation *, uint16_t clock);
void omni_presentation_speed(OmniPresentation *);
unsigned omni_presentation_steps(const OmniPresentation *, int allow_acceleration);
void omni_presentation_begin(OmniPresentation *, uint8_t count);
void omni_presentation_advance(OmniPresentation *, uint16_t clock, uint16_t scene_duration);
void omni_presentation_next(OmniPresentation *);
void omni_presentation_skip(OmniPresentation *, int confirm);
void omni_presentation_track(OmniPresentation *, uint8_t track);
#endif
