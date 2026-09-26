#ifndef OMNI_AUDIO_H
#define OMNI_AUDIO_H
#include <stdint.h>
/* Standard mono IMA ADPCM, with independently seekable 256-sample blocks.
 * Header is signed LE predictor, index, reserved; low nibble first. */
void omni_audio_decode(const uint8_t block[132],int16_t samples[256]);
#endif
