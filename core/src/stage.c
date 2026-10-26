#include "omni/stage.h"
static unsigned magnitude(int n){return (unsigned)(n<0?-n:n);}
unsigned omni_walk_plan(const OmniWalkGrid *g,unsigned fx,unsigned fy,unsigned tx,unsigned ty,
                       OmniWalkPoint *out,unsigned capacity,uint16_t *scratch,unsigned entries){
 unsigned n,start,goal,head=0,tail=0,i,count=1,current;uint16_t *parent,*queue;
 if(!g||!g->cells||!out||!scratch||!g->w||!g->h)return 0;
 n=(unsigned)g->w*g->h;if(n>=65535||entries/2<n||fx>=g->w||fy>=g->h||tx>=g->w||ty>=g->h)return 0;
 start=fy*g->w+fx;goal=ty*g->w+tx;if(g->cells[start]||g->cells[goal])return 0;
 parent=scratch;queue=scratch+n;for(i=0;i<n;++i)parent[i]=65535;
 parent[start]=(uint16_t)start;queue[tail++]=(uint16_t)start;
 while(head<tail&&parent[goal]==65535){
  unsigned at=queue[head++],x=at%g->w,y=at/g->w,neighbors[4],k=0;
  if(y)neighbors[k++]=at-g->w;if(x)neighbors[k++]=at-1;
  if(x+1<g->w)neighbors[k++]=at+1;if(y+1<g->h)neighbors[k++]=at+g->w;
  for(i=0;i<k;++i){unsigned next=neighbors[i];if(!g->cells[next]&&parent[next]==65535){parent[next]=(uint16_t)at;queue[tail++]=(uint16_t)next;}}
 }
 if(parent[goal]==65535)return 0;
 for(current=goal;current!=start;current=parent[current])++count;
 if(count>capacity)return 0;
 current=goal;for(i=count;i>0;--i){out[i-1].x=(int16_t)((current%g->w)*16);out[i-1].y=(int16_t)((current/g->w+1)*16);current=parent[current];}
 return count;
}
int omni_walk_clear(const OmniWalkGrid *g,int x,int y){
 int left=x+2,right=x+13,top=y-12,bottom=y-1;
 if(!g||!g->cells||left<0||top<0||right>=g->w*16||bottom>=g->h*16)return 0;
 return !g->cells[(top/16)*g->w+left/16]&&!g->cells[(top/16)*g->w+right/16]
     &&!g->cells[(bottom/16)*g->w+left/16]&&!g->cells[(bottom/16)*g->w+right/16];
}
int omni_walk_sample(const OmniWalkGrid *g,const OmniWalkPoint *p,unsigned count,
                    unsigned ticks,unsigned duration,OmniWalkPoint *out,uint8_t *face){
 unsigned i,total=0,travel;
 if(!p||!count||!out||!face)return 0;
 *out=p[0];if(!omni_walk_clear(g,out->x,out->y))return 0;
 for(i=1;i<count;++i){
  if(p[i].x!=p[i-1].x&&p[i].y!=p[i-1].y)return 0;
  total+=magnitude(p[i].x-p[i-1].x)+magnitude(p[i].y-p[i-1].y);
 }
 travel=!duration||ticks>=duration?total:total*ticks/duration;
 for(i=1;i<count&&travel;++i){
  int dx=p[i].x>out->x?1:p[i].x<out->x?-1:0;
  int dy=p[i].y>out->y?1:p[i].y<out->y?-1:0;
  *face=(uint8_t)(dx>0?3:dx<0?2:dy>0?0:1);
  while(travel&&(out->x!=p[i].x||out->y!=p[i].y)){
   if(!omni_walk_clear(g,out->x+dx,out->y+dy))return 0;
   out->x=(int16_t)(out->x+dx);out->y=(int16_t)(out->y+dy);--travel;
  }
 }
 return 1;
}
