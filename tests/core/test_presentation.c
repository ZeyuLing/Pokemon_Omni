#include "omni/presentation.h"
static unsigned failed_line;
#define CHECK(x) do{if(!(x)){failed_line=__LINE__;return 0;}}while(0)
unsigned presentation_failure_line(void){return failed_line;}
unsigned presentation_test(void){
 OmniPresentation a,b;unsigned i;
 omni_presentation_init(&a,65520);omni_presentation_begin(&a,2);
 omni_presentation_advance(&a,16,64);CHECK(a.scene_ticks==32);
 omni_presentation_skip(&a,0);omni_presentation_advance(&a,48,64);
 CHECK(a.scene_ticks==32);
 omni_presentation_skip(&a,0);omni_presentation_advance(&a,80,64);
 CHECK(a.scene==1&&a.playing);
 omni_presentation_next(&a);CHECK(!a.playing);
 omni_presentation_begin(&a,2);omni_presentation_skip(&a,1);CHECK(!a.playing);
 omni_presentation_begin(&a,0);CHECK(!a.playing);
 omni_presentation_init(&a,0);omni_presentation_init(&b,0);
 omni_presentation_speed(&b);omni_presentation_speed(&b);
 CHECK(omni_presentation_steps(&b,1)==4&&omni_presentation_steps(&b,0)==1);
 for(i=1;i<=640;++i){omni_presentation_advance(&a,(uint16_t)i,0);omni_presentation_advance(&b,(uint16_t)i,0);}
 CHECK(a.clock==b.clock);
 omni_presentation_begin(&b,2);omni_presentation_track(&b,2);CHECK(b.track==2);
 omni_presentation_advance(&b,2000,0);CHECK(b.scene_ticks==128); /* bounded resume */
 omni_presentation_speed(&b);CHECK(b.speed==1);
 omni_presentation_begin(&b,3);b.scene_ticks=8;
 CHECK(omni_presentation_letters(&b,20)==4);
 omni_presentation_confirm_text(&b,20);CHECK(b.scene==0&&omni_presentation_letters(&b,20)==20);
 omni_presentation_skip(&b,0);omni_presentation_confirm_text(&b,20);CHECK(b.scene==0);
 omni_presentation_skip(&b,0);omni_presentation_confirm_text(&b,20);CHECK(b.scene==1&&!b.text_revealed);
 CHECK(omni_presentation_lerp(16,48,8,32)==24);
 CHECK(omni_presentation_lerp(48,16,8,32)==40);
 CHECK(omni_presentation_lerp(16,48,40,32)==48);
 CHECK(omni_presentation_lerp(16,48,0,0)==48);
 return 1;
}
