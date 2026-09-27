#include "omni/battlefield.h"
#ifndef OMNI_WAR_FAST
#define OMNI_WAR_FAST
#endif
static int lerp(int a,int b,unsigned n,unsigned d){return !d||n>=d?b:a+(b-a)*(int)n/(int)d;}
static unsigned facing(int dx,int dy,int diagonal){
 int ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
 if(diagonal&&ax*2>=ay&&ay*2>=ax&&ax&&ay)return dy>0?(dx<0?4:5):(dx<0?6:7);
 return ax>=ay?(dx>0?3:2):(dy>0?0:1);
}
OMNI_WAR_FAST void omni_war_constrain_terrain(const OmniWarActor *a,unsigned count,uint32_t t,OmniWarPose *p,const unsigned char *cells,unsigned w,unsigned h){
 unsigned i,k;
 for(i=0;i<count;++i)if(a[i].layer!=2&&p[i].hit){
  for(k=0;k<4;++k){int x=p[i].x+(k&1?13:2),y=p[i].y+(k&2?-1:-12);
   if(x<0||y<0||(unsigned)x>=w*16||(unsigned)y>=h*16||cells[(unsigned)y/16*w+(unsigned)x/16]!=(a[i].layer==1?2:0)){
    unsigned n=t>a[i].start?(unsigned)(t-a[i].start):0;
    p[i].x=(int16_t)lerp(a[i].x,a[i].tx,n,a[i].duration);
    p[i].y=(int16_t)lerp(a[i].y,a[i].ty,n,a[i].duration);break;
   }
  }
 }
}
OMNI_WAR_FAST unsigned omni_war_target(const OmniWarActor *a,unsigned count,unsigned i,uint32_t t){
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
OMNI_WAR_FAST void omni_war_sample_all(const OmniWarActor *a,unsigned count,uint32_t t,OmniWarPose *p){
 unsigned i;
 for(i=0;i<count;++i){
  const OmniWarActor *u=&a[i];unsigned n=t>u->start?(unsigned)(t-u->start):0,q;
  p[i].x=(int16_t)lerp(u->x,u->tx,n,u->duration);p[i].y=(int16_t)lerp(u->y,u->ty,n,u->duration);
  p[i].face=u->team==0?0:u->team==1?3:u->team==2?1:2;p[i].step=(uint8_t)((t/8)&1);p[i].hit=0;p[i].phase=0;p[i].action=OMNI_WAR_IDLE;
  if(t>=u->stop){p[i].action=OMNI_WAR_DOWN;continue;}
  if(n<u->duration&&t>=u->start){p[i].action=OMNI_WAR_ADVANCE;p[i].face=u->tx>u->x?3:u->tx<u->x?2:u->ty>u->y?0:1;}
  if(u->attack&&t>=u->start+u->duration&&omni_war_target(a,count,i,t)<count){q=(unsigned)(t-u->start-u->duration+u->phase)%320;p[i].phase=(uint16_t)q;p[i].action=q<64?OMNI_WAR_CHARGE:q<112?OMNI_WAR_FIRE:OMNI_WAR_RECOVER;}
 }
 /* Fighters face their firing lane in eight directions; support personnel
  * face their assigned partner/front, never an arbitrary team orientation. */
 for(i=0;i<count;++i)if(p[i].action!=OMNI_WAR_ADVANCE){
  unsigned target=a[i].attack?omni_war_target(a,count,i,t<a[i].stop?t:a[i].stop-1):a[i].target;
  if(target<count){int dx=p[target].x-p[i].x,dy=p[target].y-p[i].y;
   if(dx||dy)p[i].face=(uint8_t)facing(dx,dy,a[i].attack!=0);
  }
 }
 for(i=0;i<count;++i)if(a[i].attack&&t<a[i].stop&&t>=a[i].start+a[i].duration&&p[i].phase>=104&&p[i].phase<128){
  unsigned target=omni_war_target(a,count,i,t);
  if(target<count){int dx=p[target].x-p[i].x,dy=p[target].y-p[i].y,force=p[i].phase<116?3:1;p[target].hit=1;
   if((dx<0?-dx:dx)>=(dy<0?-dy:dy))p[target].x+=(int16_t)(dx<0?-force:force);
   else p[target].y+=(int16_t)(dy<0?-force:force);
  }
 }
}
