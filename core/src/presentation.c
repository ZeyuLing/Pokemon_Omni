#include "omni/presentation.h"
void omni_presentation_init(OmniPresentation *p,uint16_t clock){
 p->clock=clock;p->scene_ticks=0;p->speed=1;p->scene=0;
 p->scene_count=p->playing=p->skip_prompt=p->track=p->text_revealed=0;
}
void omni_presentation_speed(OmniPresentation *p){p->speed=p->speed==1?2:p->speed==2?4:1;}
unsigned omni_presentation_steps(const OmniPresentation *p,int allow){return allow?p->speed:1;}
void omni_presentation_begin(OmniPresentation *p,uint8_t count){p->scene=0;p->scene_count=count;p->scene_ticks=0;p->skip_prompt=0;p->text_revealed=0;p->playing=count!=0;}
void omni_presentation_next(OmniPresentation *p){
 if(!p->playing||p->skip_prompt)return;
 p->scene_ticks=0;p->text_revealed=0;if(++p->scene>=p->scene_count)p->playing=0;
}
unsigned omni_presentation_letters(const OmniPresentation *p,unsigned total){
 unsigned n=p->text_revealed?total:p->scene_ticks/2;
 return n<total?n:total;
}
void omni_presentation_confirm_text(OmniPresentation *p,unsigned total){
 if(p->skip_prompt||!p->playing)return;
 if(omni_presentation_letters(p,total)<total)p->text_revealed=1;
 else omni_presentation_next(p);
}
int omni_presentation_lerp(int start,int end,uint16_t ticks,uint16_t duration){
 if(!duration||ticks>=duration)return end;
 return start+(end-start)*(int)ticks/(int)duration;
}
void omni_presentation_skip(OmniPresentation *p,int confirm){
 if(!p->playing)return;
 if(confirm){p->playing=0;p->skip_prompt=0;}else p->skip_prompt^=1;
}
void omni_presentation_track(OmniPresentation *p,uint8_t track){
 p->track=track;
}
void omni_presentation_advance(OmniPresentation *p,uint16_t clock,uint16_t duration){
 uint16_t elapsed=(uint16_t)(clock-p->clock);p->clock=clock;
 /* A long suspension never catches up minutes of scene changes. */
 if(elapsed>128)elapsed=128;
 if(p->playing&&!p->skip_prompt){
  p->scene_ticks=(uint16_t)(p->scene_ticks+elapsed);
  if(duration&&p->scene_ticks>=duration)omni_presentation_next(p);
 }
}
