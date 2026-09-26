#include "omni/battlefield.h"
static int lerp(int a,int b,unsigned n,unsigned d){return !d||n>=d?b:a+(b-a)*(int)n/(int)d;}
unsigned omni_war_target(const OmniWarActor *a,unsigned count,unsigned i,uint32_t t){
 unsigned j,best=count;int distance=0x7fffffff;
 if(i>=count)return count;
 if(a[i].target<count&&t<a[a[i].target].stop)return a[i].target;
 /* Survivors engage combatants, never the wounded. */
 for(j=0;j<count;++j)if(a[j].team!=a[i].team&&a[j].attack&&t<a[j].stop){
  int x=a[j].tx-a[i].tx,y=a[j].ty-a[i].ty,d=x*x+y*y;
  if(d<distance){distance=d;best=j;}
 }
 return best;
}
void omni_war_sample_all(const OmniWarActor *a,unsigned count,uint32_t t,OmniWarPose *p){
 unsigned i;
 for(i=0;i<count;++i){
  const OmniWarActor *u=&a[i];unsigned n=t>u->start?(unsigned)(t-u->start):0,q;
  p[i].x=(int16_t)lerp(u->x,u->tx,n,u->duration);p[i].y=(int16_t)lerp(u->y,u->ty,n,u->duration);
  p[i].face=(u->team&1)?2:3;p[i].step=(uint8_t)((t/8)&1);p[i].hit=0;p[i].phase=0;p[i].action=OMNI_WAR_IDLE;
  if(t>=u->stop){p[i].action=OMNI_WAR_DOWN;continue;}
  if(n<u->duration&&t>=u->start){p[i].action=OMNI_WAR_ADVANCE;if(u->y!=u->ty)p[i].face=u->ty>u->y?0:1;}
  if(u->attack&&t>=u->start+u->duration&&omni_war_target(a,count,i,t)<count){q=(unsigned)(t-u->start-u->duration+u->phase)%320;p[i].phase=(uint16_t)q;p[i].action=q<64?OMNI_WAR_CHARGE:q<112?OMNI_WAR_FIRE:OMNI_WAR_RECOVER;}
 }
 for(i=0;i<count;++i)if(a[i].attack&&t<a[i].stop&&t>=a[i].start+a[i].duration&&p[i].phase>=104&&p[i].phase<128){
  unsigned target=omni_war_target(a,count,i,t);
  if(target<count){p[target].hit=1;p[target].x+=(int16_t)(((a[target].team&1)?1:-1)*(p[i].phase<116?3:1));}
 }
}
