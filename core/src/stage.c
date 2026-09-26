#include "omni/stage.h"
static unsigned magnitude(int n){return (unsigned)(n<0?-n:n);}
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
