#include "omni/presentation.h"
void omni_presentation_init(OmniPresentation *p,uint16_t clock){
 p->clock=clock;p->scene_ticks=p->music_ticks=0;p->speed=1;p->scene=0;
 p->scene_count=p->playing=p->skip_prompt=p->track=p->note=0;p->music_steps=0;
}
void omni_presentation_speed(OmniPresentation *p){p->speed=p->speed==1?2:p->speed==2?4:1;}
unsigned omni_presentation_steps(const OmniPresentation *p,int allow){return allow?p->speed:1;}
void omni_presentation_begin(OmniPresentation *p,uint8_t count){p->scene=0;p->scene_count=count;p->scene_ticks=0;p->skip_prompt=0;p->playing=count!=0;}
void omni_presentation_next(OmniPresentation *p){
 if(!p->playing||p->skip_prompt)return;
 p->scene_ticks=0;if(++p->scene>=p->scene_count)p->playing=0;
}
void omni_presentation_skip(OmniPresentation *p,int confirm){
 if(!p->playing)return;
 if(confirm){p->playing=0;p->skip_prompt=0;}else p->skip_prompt^=1;
}
void omni_presentation_track(OmniPresentation *p,uint8_t track){
 if(p->track==track)return;p->track=track;p->music_ticks=0;p->note=0;
}
void omni_presentation_advance(OmniPresentation *p,uint16_t clock,uint16_t duration){
 uint16_t elapsed=(uint16_t)(clock-p->clock);p->clock=clock;
 /* A long suspension never catches up minutes of scene changes or notes. */
 if(elapsed>128)elapsed=128;
 if(p->playing&&!p->skip_prompt){
  p->scene_ticks=(uint16_t)(p->scene_ticks+elapsed);
  if(duration&&p->scene_ticks>=duration)omni_presentation_next(p);
 }
 p->music_ticks=(uint16_t)(p->music_ticks+elapsed);
 /* Thirty-two 1/8-note steps at 96 BPM: 20 hardware ticks per eighth. */
 while(p->music_ticks>=20){p->music_ticks-=20;p->note=(uint8_t)((p->note+1)%32);++p->music_steps;}
}
