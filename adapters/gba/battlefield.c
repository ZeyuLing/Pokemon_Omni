#include "battlefield.h"
#include "war_data.h"
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))
#define WAR_FAST __attribute__((section(".iwram"),target("arm"),noinline))
volatile uint32_t omni_war_probe[8+OMNI_WAR_COUNT*4]={0x57494d4f,0x315241};
static volatile uint16_t *dst;
static inline __attribute__((always_inline,target("arm"))) void dot(int x,int y,uint16_t c){if((unsigned)x<240&&(unsigned)y<160)dst[y*240+x]=c;}
static WAR_FAST void disc(int x,int y,int radius,uint16_t c){int xx,yy;for(yy=-radius;yy<=radius;++yy)for(xx=-radius;xx<=radius;++xx)if(xx*xx+yy*yy<=radius*radius)dot(x+xx,y+yy,c);}
static WAR_FAST void line(int x,int y,int tx,int ty,uint16_t c){int dx=tx>x?tx-x:x-tx,dy=ty>y?y-ty:ty-y,sx=x<tx?1:-1,sy=y<ty?1:-1,e=dx+dy;for(;;){int e2;dot(x,y,c);if(x==tx&&y==ty)break;e2=2*e;if(e2>=dy){e+=dy;x+=sx;}if(e2<=dx){e+=dx;y+=sy;}}}
static const uint16_t colors[]={0,RGB(31,12,2),RGB(31,28,5),RGB(24,19,15),RGB(24,9,27),RGB(24,29,31),RGB(31,26,12),RGB(24,12,31)};
static const uint16_t uniforms[]={RGB(27,5,7),RGB(5,25,24),RGB(31,21,4),RGB(22,13,29)};
WAR_FAST void omni_gba_war_draw(volatile uint16_t *surface,int cx,int cy,uint32_t ticks){
 OmniWarPose p[OMNI_WAR_COUNT];unsigned order[OMNI_WAR_COUNT],i,j,active=0,hits=0;int x,y;
 dst=surface;
 /* Environmental danger belongs to terrain, not a red full-screen filter. */
 for(y=0;y<20;++y)for(x=0;x<32;++x)if(omni_war_terrain[y*32+x]==2){
  int xx=x*16-cx,yy=y*16-cy,n=(int)((ticks/6+x*7+y*13)%13);
  line(xx+1,yy+n,xx+9,yy+n-2,RGB(31,18,2));dot(xx+12,yy+15-n,RGB(31,27,9));
 }
 if(ticks>=1600)for(i=0;i<OMNI_WAR_COUNT;++i)if(omni_war_actors[i].stop==1600){
  int xx=omni_war_actors[i].tx+8-cx,yy=omni_war_actors[i].ty-cy;
  for(j=0;j<13;++j)line(xx-13+(int)j,yy-3,xx+12-(int)j,yy+2,RGB(7,5,6));
 }
 omni_war_sample_all(omni_war_actors,OMNI_WAR_COUNT,ticks,p);
 for(i=0;i<OMNI_WAR_COUNT;++i)order[i]=i;
 for(i=0;i<OMNI_WAR_COUNT;++i)for(j=i+1;j<OMNI_WAR_COUNT;++j){unsigned a=order[i],b=order[j];int ka=p[a].y+(omni_war_actors[a].layer==2&&p[a].action!=OMNI_WAR_DOWN?1024:0),kb=p[b].y+(omni_war_actors[b].layer==2&&p[b].action!=OMNI_WAR_DOWN?1024:0);if(ka>kb){order[i]=b;order[j]=a;}}
 for(j=0;j<OMNI_WAR_COUNT;++j){
  unsigned frame,stride;int row,col,bob=0,left,down;uint16_t palette[16];const unsigned char *pixels;const OmniWarActor *a;const OmniWarSprite *s;
  i=order[j];a=&omni_war_actors[i];s=&omni_war_sprites[a->sprite];x=p[i].x-cx;y=p[i].y-cy;down=p[i].action==OMNI_WAR_DOWN;
  if(a->layer==2&&!down)bob=-5-(int)((ticks/14+i)%3);
  if(s->pmd){frame=(p[i].face==3?6:0)+(down?5:p[i].hit?4:p[i].action==OMNI_WAR_FIRE?3:p[i].action==OMNI_WAR_CHARGE?2:(ticks/12)&1);}
  else if(a->sprite>=12&&a->sprite<16)frame=p[i].face;
  else {frame=p[i].face==0?0:p[i].face==1?1:2;if(p[i].action==OMNI_WAR_ADVANCE&&p[i].step)frame=(p[i].face==0?3:p[i].face==1?5:7)+(ticks/16&1);}
  frame%=s->frames;stride=(s->w*s->h+1)/2;pixels=omni_war_art+s->offset+frame*stride;left=x+8-s->w/2;
  if(x+8+s->w/2>0&&left<240&&y>0&&y-s->h<160){
   for(col=0;col<16;++col)palette[col]=s->palette[col];
   if(a->role==2&&s->human){int fx=x-6;line(fx,y,fx,y-36,RGB(14,12,12));for(row=0;row<9;++row)line(fx,y-36+row,fx+7-(row%3==0?2:0),y-36+row,uniforms[a->team]);}
   if(p[i].action==OMNI_WAR_CHARGE)for(col=0;col<4;++col)disc(x+2+col*4,y-s->h-2-(int)((ticks+col*7)%9),1,colors[a->attack]);
   for(row=0;row<s->h;++row)for(col=0;col<s->w;++col){
    unsigned ix=row*s->w+((!s->pmd&&a->sprite>=16&&p[i].face==3)?s->w-1-col:col);uint16_t c=palette[(pixels[ix/2]>>((ix&1)*4))&15];int dx=left+col,dy=y-s->h+row+bob;
    if(c&0x8000)continue;
    if(down){if(!s->pmd){dx=x+8-s->h/2+row;dy=y-s->w/2+col/2;}c=(uint16_t)(((c&31)*4/5)|((((c>>5)&31)*4/5)<<5)|((((c>>10)&31)*4/5)<<10));}
    else if(p[i].hit&&(ticks/3&1))c=RGB(31,31,28);
    if(a->role==4&&ticks>=1600)dy=y-(s->h-row)*3/4; /* kneel beside partner */
    dot(dx,dy,c);
   }
   if(s->human&&a->sprite>=16&&!down)line(x+1,y-17,x+4,y-17,uniforms[a->team]);
   if(a->role==3&&ticks>=1856){line(x+6,y-28,x+10,y-28,RGB(23,26,22));line(x+8,y-30,x+8,y-26,RGB(23,26,22));}
  }
  if(p[i].hit)++hits;
  if(p[i].hit){int r=(int)(ticks%7);disc(x+3-r,y-3-r,2,RGB(18,15,13));disc(x+12+r,y-2-r,2,RGB(21,17,14));}
  omni_war_probe[8+i*4]=(uint32_t)p[i].x;omni_war_probe[9+i*4]=(uint32_t)p[i].y;omni_war_probe[10+i*4]=p[i].action;omni_war_probe[11+i*4]=p[i].hit;
 }
 for(i=0;i<OMNI_WAR_COUNT;++i){
  const OmniWarActor *a=&omni_war_actors[i];unsigned k,q=p[i].phase,target;int sx,sy,tx,ty;
  if(!a->attack||p[i].action!=OMNI_WAR_FIRE)continue;
  target=omni_war_target(omni_war_actors,OMNI_WAR_COUNT,i,ticks);if(target>=OMNI_WAR_COUNT)continue;
  ++active;sx=p[i].x+8-cx;sy=p[i].y-16-cy;tx=p[target].x+8-cx;ty=p[target].y-16-cy;
  if(a->layer==2)sy-=8;if(omni_war_actors[target].layer==2)ty-=8;
  if(a->attack==6&&q>82){line(sx,sy,tx,ty,colors[6]);line(sx,sy+1,tx,ty+1,RGB(31,31,27));line(sx,sy-1,tx,ty-1,RGB(31,14,3));}
  for(k=0;k<9;++k){int u=(int)q-64-(int)k*2;if(u<0)continue;x=sx+(tx-sx)*u/48;y=sy+(ty-sy)*u/48;
   if(a->attack==2){int bend=((u/3)&1)?5:-5;line(x,y,x+bend,y+5,colors[2]);}
   else if(a->attack==7){disc(x,y,3,colors[7]);disc(x,y,1,RGB(31,25,31));}
   else {disc(x,y+(int)(k%3)-1,a->attack==1?3:2,colors[a->attack]);if(a->attack==1)dot(x,y,RGB(31,28,8));}
  }
  if(q>=104){int r=2+(q-104)*2;for(k=0;k<8;++k){int dx=(k%3)-1,dy=(k/3)-1;line(tx+dx*2,ty+dy*2,tx+dx*r,ty+dy*r,RGB(31,23,15));}disc(tx,ty,3,colors[a->attack]);}
 }
 /* Sparse drifting ash and ember trails; smoke covers fragments, not the whole scene. */
 for(i=0;i<24;++i){int xx=(int)((i*73+ticks/5)%560)-cx,yy=(int)((i*37+ticks/7)%336)-cy;dot(xx,yy,i%4?RGB(15,12,12):RGB(31,19,3));}
 if(ticks>=1600)for(i=0;i<8;++i){int xx=(int)(i*57+32)-cx,yy=250-(int)((ticks/4+i*29)%220)-cy;line(xx,yy,xx+7,yy,RGB(10,8,9));line(xx+3,yy-3,xx+10,yy-3,RGB(13,10,11));}
 if(ticks>=1536&&ticks<1600)for(i=0;i<240*160;++i)dst[i]=RGB(1,0,0);
 omni_war_probe[2]=ticks;omni_war_probe[3]=OMNI_WAR_COUNT;omni_war_probe[4]=active;omni_war_probe[5]=hits;omni_war_probe[6]=(uint32_t)cx;omni_war_probe[7]=(uint32_t)cy;
}
