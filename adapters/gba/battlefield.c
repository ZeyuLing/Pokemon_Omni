#include "battlefield.h"
#include "war_data.h"
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))
/* Read-only test probe. It exposes no game mutation or cheating commands. */
volatile uint32_t omni_war_probe[8+OMNI_WAR_COUNT*4]={0x57494d4f,0x315241};
static volatile uint16_t *dst;
static void dot(int x,int y,uint16_t c){if((unsigned)x<240&&(unsigned)y<160)dst[y*240+x]=c;}
static void disc(int x,int y,int radius,uint16_t c){int xx,yy;for(yy=-radius;yy<=radius;++yy)for(xx=-radius;xx<=radius;++xx)if(xx*xx+yy*yy<=radius*radius)dot(x+xx,y+yy,c);}
static void line(int x,int y,int tx,int ty,uint16_t c){int dx=tx-x,dy=ty-y,n=dx<0?-dx:dx,i,m=dy<0?-dy:dy;if(m>n)n=m;if(!n){dot(x,y,c);return;}for(i=0;i<=n;++i)dot(x+dx*i/n,y+dy*i/n,c);}
static const uint16_t colors[]={0,RGB(7,22,31),RGB(31,28,5),RGB(31,23,14),RGB(24,9,27),RGB(24,29,31)};
void omni_gba_war_draw(volatile uint16_t *surface,int cx,int cy,uint32_t ticks){
 OmniWarPose p[OMNI_WAR_COUNT];unsigned order[OMNI_WAR_COUNT],i,j,active=0,hits=0;int x,y;
 dst=surface;
 /* Animated water ripples are drawn on the river, never over the bridges. */
 for(y=32;y<304;y+=17)if(y/16!=5&&y/16!=13)for(x=232;x<278;x+=21){int v=(int)(ticks/5+y)%12;line(x-cx+v,y-cy,x-cx+v+5,y-cy,RGB(16,25,31));}
 for(i=0;i<OMNI_WAR_COUNT;++i){omni_war_sample(omni_war_actors,OMNI_WAR_COUNT,i,ticks,&p[i]);order[i]=i;}
 for(i=0;i<OMNI_WAR_COUNT;++i)for(j=i+1;j<OMNI_WAR_COUNT;++j){unsigned a=order[i],b=order[j];int ka=p[a].y+(omni_war_actors[a].layer==2?1024:0),kb=p[b].y+(omni_war_actors[b].layer==2?1024:0);if(ka>kb){order[i]=b;order[j]=a;}}
 for(j=0;j<OMNI_WAR_COUNT;++j){
  unsigned frame;int row,col,bob=0;const uint16_t *pixels;const OmniWarActor *a;const OmniWarSprite *s;
  i=order[j];a=&omni_war_actors[i];s=&omni_war_sprites[a->sprite];
  x=p[i].x-cx;y=p[i].y-cy;
  if(a->layer==2)bob=-8-(int)((ticks/8+i)%4);
  else if(a->layer==1)bob=(int)((ticks/16+i)&1);
  else if(p[i].action==OMNI_WAR_ADVANCE&&!s->human)bob=-(int)p[i].step;
  frame=p[i].face==0?0:p[i].face==1?1:2;
  if(s->human&&p[i].action==OMNI_WAR_ADVANCE&&p[i].step)frame=(p[i].face==0?3:p[i].face==1?5:7)+(ticks/16&1);
  frame%=s->frames;pixels=(const uint16_t*)(omni_war_art+s->offset)+frame*s->w*s->h;
  if(x>-32&&x<240&&y>0&&y<192){
   for(col=3;col<13;++col)dot(x+col,y-1,RGB(8,15,12));
   if(p[i].action==OMNI_WAR_CHARGE)for(col=0;col<4;++col)disc(x+3+col*3,y-s->h-2-(int)((ticks+col*7)%9),1,colors[a->attack]);
   for(row=0;row<s->h;++row)for(col=0;col<s->w;++col){uint16_t c=pixels[row*s->w+(p[i].face==3?s->w-1-col:col)];if(c&0x8000)continue;if(p[i].hit&&(ticks/3&1))c=RGB(31,31,28);dot(x+col,y-s->h+row+bob,c);}
   if(s->human&&a->sprite==7&&(ticks/32&1)){line(x+16,y-25,x+20,y-29,RGB(31,31,23));dot(x+19,y-31,RGB(31,31,23));}
   if(a->sprite==6&&ticks>=1408&&ticks<1792){for(col=0;col<3;++col){int yy=y-20-(int)((ticks+col*15)%24);line(x+col*6,yy,x+col*6+4,yy,RGB(23,31,22));line(x+col*6+2,yy-2,x+col*6+2,yy+2,RGB(23,31,22));}}
  }
  if(p[i].hit)++hits;
  if(p[i].hit){int r=(int)(ticks%7);disc(x+3-r,y-3-r,2,RGB(22,23,20));disc(x+12+r,y-2-r,2,RGB(26,26,23));}
  omni_war_probe[8+i*4]=(uint32_t)p[i].x;omni_war_probe[9+i*4]=(uint32_t)p[i].y;omni_war_probe[10+i*4]=p[i].action;omni_war_probe[11+i*4]=p[i].hit;
 }
 for(i=0;i<OMNI_WAR_COUNT;++i){
  const OmniWarActor *a=&omni_war_actors[i];unsigned k,q=p[i].phase;int sx,sy,tx,ty;
  if(!a->attack||p[i].action!=OMNI_WAR_FIRE)continue;
  ++active;sx=p[i].x+8-cx;sy=p[i].y-10-cy;tx=p[a->target].x+8-cx;ty=p[a->target].y-10-cy;
  if(a->layer==2)sy-=10;if(omni_war_actors[a->target].layer==2)ty-=10;
  for(k=0;k<7;++k){int u=(int)q-48-(int)k*2;if(u<0)continue;x=sx+(tx-sx)*u/48;y=sy+(ty-sy)*u/48;
   if(a->attack==2){int bend=((u/3)&1)?3:-3;line(x,y,x+bend,y+4,colors[2]);}
   else if(a->attack==5){line(x-3,y+(int)(k%3)-1,x+3,y+(int)(k%3)-1,colors[5]);}
   else disc(x,y+(int)(k%3)-1,a->attack==1?2:1,colors[a->attack]);
  }
  if(q>=88){int r=2+(q-88);for(k=0;k<8;++k){int dx=(k%3)-1,dy=(k/3)-1;line(tx+dx*2,ty+dy*2,tx+dx*r,ty+dy*r,RGB(31,31,27));}disc(tx,ty,2,colors[a->attack]);}
 }
 omni_war_probe[2]=ticks;omni_war_probe[3]=OMNI_WAR_COUNT;omni_war_probe[4]=active;omni_war_probe[5]=hits;omni_war_probe[6]=(uint32_t)cx;omni_war_probe[7]=(uint32_t)cy;
}
