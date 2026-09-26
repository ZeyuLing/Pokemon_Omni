#include "omni/battlefield.h"
static int lerp(int a,int b,unsigned n,unsigned d){return !d||n>=d?b:a+(b-a)*(int)n/(int)d;}
void omni_war_sample(const OmniWarActor *a,unsigned count,unsigned i,uint32_t t,OmniWarPose *p){
 const OmniWarActor *u;unsigned n,j,q;
 if(!a||!p||i>=count)return;
 u=&a[i];n=t>u->start?(unsigned)(t-u->start):0;
 p->x=(int16_t)lerp(u->x,u->tx,n,u->duration);p->y=(int16_t)lerp(u->y,u->ty,n,u->duration);
 p->face=u->team?2:3;p->step=(uint8_t)((t/8)&1);p->hit=0;p->phase=0;p->action=OMNI_WAR_IDLE;
 if(n<u->duration&&t>=u->start){p->action=OMNI_WAR_ADVANCE;if(u->y!=u->ty)p->face=u->ty>u->y?0:1;}
 if(u->attack&&t>=u->start+u->duration){
  q=(unsigned)(t-u->start-u->duration+u->phase)%240;p->phase=(uint16_t)q;
  p->action=q<48?OMNI_WAR_CHARGE:q<96?OMNI_WAR_FIRE:OMNI_WAR_RECOVER;
  if(u->attack==3&&q>=48&&q<96){int lunge=(q<72?(int)q-48:96-(int)q)/4;p->x+=(int16_t)(u->team?-lunge:lunge);}
 }
 for(j=0;j<count;++j)if(a[j].attack&&a[j].target==i&&t>=a[j].start+a[j].duration&&!(a[j].role==1&&t>=1408&&t<1792)){
  q=(unsigned)(t-a[j].start-a[j].duration+a[j].phase)%240;
  if(q>=88&&q<112){p->hit=1;/* Recoil remains inside the reserved foot tile. */
   p->x+=(int16_t)((u->team?1:-1)*(q<100?3:1));}
 }
 /* A temporary withdrawal toward the already traversed safe endpoint, then
  * return. This signifies disengagement, never a scripted death. */
 if(u->role==1&&t>=1408&&t<1792){unsigned retreat=t<1600?(unsigned)t-1408:1792-(unsigned)t;p->x=(int16_t)lerp(u->tx,u->x,retreat,192);p->y=(int16_t)lerp(u->ty,u->y,retreat,192);p->action=OMNI_WAR_ADVANCE;}
}
