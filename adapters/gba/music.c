#include <stdint.h>
#include "music.h"
#define REG(a) (*(volatile uint16_t*)(a))
/* Original two-voice sketch, not an imported soundtrack. PSG2 remains available
 * for button effects. Timer2+3 form a 64-Hz clock independent of gameplay. */
static const uint16_t frequency[]={0,1547,1575,1602,1627,1650,1673,1694,1714,1732,1750,1767,1783,1798,1812,1825,1837,1849,1860,1871,1881,1890,1899,1907,1915};
static const uint8_t themes[3][32]={
 {1,0,8,0,13,12,8,0,4,0,11,0,16,15,11,0,6,0,13,0,18,16,13,0,8,0,15,0,12,11,8,0},
 {13,0,17,20,18,0,17,13,11,0,13,15,13,0,8,0,13,0,17,20,22,0,20,17,18,17,15,11,13,0,0,0},
 {13,13,8,13,16,0,15,11,13,13,8,13,18,16,15,0,11,11,6,11,15,0,13,8,11,13,15,16,15,11,8,0}
};
static uint8_t previous_track=255,previous_note=255;
static OmniPresentation audio_clock;
static volatile uint8_t requested_track=1;
static volatile uint16_t pending_keys;
static uint16_t sampled_keys;
/* BIOS calls this ARM callback in IRQ mode and handles the exception return.
 * Do not use the compiler's bare-metal interrupt attribute here. */
static void __attribute__((target("arm"))) music_irq(void){
 uint16_t flags=REG(0x04000202);
 if(flags&0x20){
  uint16_t keys=(uint16_t)(~REG(0x04000130)&1023);
  pending_keys|=keys&~sampled_keys;sampled_keys=keys;
  omni_presentation_track(&audio_clock,requested_track);
  omni_presentation_advance(&audio_clock,omni_gba_clock(),0);
  omni_gba_music_tick(&audio_clock);
 }
 REG(0x03007ff8)|=flags;REG(0x04000202)=flags;
}
void omni_gba_music_request(uint8_t track){requested_track=track;}
uint32_t omni_gba_music_steps(void){return *(volatile uint32_t*)&audio_clock.music_steps;}
uint16_t omni_gba_input_pressed(void){uint16_t value;REG(0x04000208)=0;value=pending_keys;pending_keys=0;REG(0x04000208)=1;return value;}
void omni_gba_input_clear(void){REG(0x04000208)=0;pending_keys=0;sampled_keys=(uint16_t)(~REG(0x04000130)&1023);REG(0x04000208)=1;}
void omni_gba_music_init(void){
 REG(0x04000084)=0x80;REG(0x04000080)=0x7777;REG(0x04000082)=2;
 REG(0x04000060)=0;REG(0x04000070)=0;
 /* Write inactive wave bank, then use it. A mellow triangle bass. */
 REG(0x04000070)=0x40;
 {static const uint16_t wave[8]={0x3210,0x7654,0xba98,0xfedc,0xcdef,0x89ab,0x4567,0x0123};unsigned i;for(i=0;i<8;++i)REG(0x04000090+i*2)=wave[i];}
 REG(0x04000070)=0x80;REG(0x04000072)=0x4000;
 REG(0x0400010a)=0;REG(0x0400010e)=0;REG(0x0400010c)=0;
 omni_presentation_init(&audio_clock,0);
 *(void (*volatile *)(void))0x03007ffc=music_irq;
 REG(0x04000202)=0xffff;REG(0x04000200)=0x20;
 REG(0x04000108)=0xff00;REG(0x0400010e)=0x84;REG(0x0400010a)=0xc3;
 REG(0x04000208)=1;
}
uint16_t omni_gba_clock(void){return REG(0x0400010c);}
void omni_gba_music_tick(const OmniPresentation *p){
 uint8_t n;if(previous_track==p->track&&previous_note==p->note)return;
 previous_track=p->track;previous_note=p->note;n=themes[p->track%3][p->note];
 REG(0x04000062)=n?0x6840:0;REG(0x04000064)=0x8000|frequency[n];
 if(!(p->note%8)){static const uint8_t bass[]={1,4,6,8};uint8_t b=bass[p->note/8];REG(0x04000074)=0x8000|frequency[b];}
}
