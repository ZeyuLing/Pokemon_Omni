#include <stdint.h>
#include "music.h"
#include "omni/audio.h"
#include "classic_audio.h"
#define REG(a) (*(volatile uint16_t*)(a))
#define REG32(a) (*(volatile uint32_t*)(a))
#define FAST_AUDIO __attribute__((section(".iwram"),target("arm")))
/* Direct Sound A: original ROM mixes, not a new PSG arrangement.
 * 16,384 Hz FIFO; each 256-sample block lasts 1/64 second. */
static int8_t ring[544] __attribute__((aligned(4)));
static int16_t decoded[256],effect[256];
static volatile uint8_t requested_track=1,requested_effect=255;
static volatile uint16_t pending_keys;
static uint16_t sampled_keys;
static uint8_t active_track=1,half,fade_out,fade_in;
static uint32_t block_index,effect_block;
static uint8_t active_effect=255;
static volatile uint32_t played_samples,loop_count;
static __attribute__((always_inline)) inline unsigned decode_clip(uint8_t id,uint32_t *block,int16_t *out){
 const OmniAudioClip *c=&omni_audio_clips[id];unsigned i;
 if(*block>=c->blocks){
  if(c->loop){*block=c->loop_start;++loop_count;}
  else{for(i=0;i<256;++i)out[i]=0;return 0;}
 }
 omni_audio_decode(omni_classic_audio_blob+c->offset+(*block)*132,out);++*block;return 1;
}
static FAST_AUDIO void fill(unsigned slot){
 unsigned i;int gain,scaled_gain;
 if(requested_track!=active_track&&!fade_out)fade_out=4;
 if(fade_out==1){active_track=requested_track;block_index=0;fade_out=0;fade_in=4;}
 decode_clip(active_track,&block_index,decoded);
 if(requested_effect!=255){active_effect=requested_effect;effect_block=0;requested_effect=255;}
 if(active_effect!=255&&!decode_clip(active_effect,&effect_block,effect))active_effect=255;
 gain=fade_out?(fade_out-1)*64:fade_in?(5-fade_in)*64:256;
 scaled_gain=(gain*205)>>8;
 for(i=0;i<256;++i){
  /* Moderate BGM level leaves headroom for the original confirmation sound. */
  int v=(decoded[i]*scaled_gain)>>16;
  if(active_effect!=255)v+=effect[i]>>8;
  if(v>127)v=127;if(v<-128)v=-128;ring[slot*256+i]=(int8_t)v;
 }
 if(fade_out)--fade_out;if(fade_in)--fade_in;
 if(slot==0)for(i=0;i<32;++i)ring[512+i]=ring[i];
}
/* BIOS calls an ARM callback. DMA has prefetched 32 bytes at ring wrap,
 * so resume at +32, preserving the already queued FIFO samples. */
static FAST_AUDIO void music_irq(void){
 uint16_t flags=REG(0x04000202);
 if(flags&0x10){
  played_samples+=256;
  if(half){REG32(0x040000c4)=0;REG32(0x040000bc)=(uint32_t)(uintptr_t)(ring+32);REG32(0x040000c4)=0xb6400004u;}
  fill(half);half^=1;
 }
 if(flags&0x20){
  uint16_t keys=(uint16_t)(~REG(0x04000130)&1023);
  pending_keys|=keys&~sampled_keys;sampled_keys=keys;
 }
 REG(0x03007ff8)|=flags;REG(0x04000202)=flags;
}
void omni_gba_music_request(uint8_t track){if(track<OMNI_AUDIO_SELECT)requested_track=track;}
void omni_gba_sound_select(void){requested_effect=OMNI_AUDIO_SELECT;}
uint32_t omni_gba_music_samples(void){return played_samples;}
uint32_t omni_gba_music_loops(void){return loop_count;}
uint32_t omni_gba_music_block(void){return block_index;}
uint8_t omni_gba_music_track(void){return active_track;}
uint16_t omni_gba_input_pressed(void){uint16_t value;REG(0x04000208)=0;value=pending_keys;pending_keys=0;REG(0x04000208)=1;return value;}
void omni_gba_input_clear(void){REG(0x04000208)=0;pending_keys=0;sampled_keys=(uint16_t)(~REG(0x04000130)&1023);REG(0x04000208)=1;}
void omni_gba_music_init(void){
 REG(0x04000208)=0;REG(0x04000084)=0x80;REG(0x04000080)=0;REG(0x04000088)=0x0200;
 REG(0x04000102)=0;REG(0x04000106)=0;REG(0x0400010a)=0;REG(0x0400010e)=0;
 fade_in=4;fill(0);fill(1);half=0;
 REG(0x04000082)=0x0b04;
 REG32(0x040000bc)=(uint32_t)(uintptr_t)ring;REG32(0x040000c0)=0x040000a0;REG32(0x040000c4)=0xb6400004u;
 *(void (*volatile *)(void))0x03007ffc=music_irq;
 REG(0x04000202)=0xffff;REG(0x04000200)=0x30;
 REG(0x04000104)=0xff00;REG(0x04000106)=0xc4;REG(0x04000100)=0xfc00;
 REG(0x0400010c)=0;REG(0x04000108)=0xff00;REG(0x0400010e)=0x84;REG(0x0400010a)=0xc3;
 REG(0x04000208)=1;REG(0x04000102)=0x80;
}
uint16_t omni_gba_clock(void){return REG(0x0400010c);}
