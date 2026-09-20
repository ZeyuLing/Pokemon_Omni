#include <stdint.h>
#include <stddef.h>
#ifndef OMNI_GBA_STANDALONE
#include "omni/memory.h"
#endif
#include "omni/pokedex.h"
#include "omni/training.h"
#include "omni/battle_stats.h"
#include "catalog.h"
#include "plans.h"
#include "gba_data.h"
#include "pokedex_game.h"

#define REG16(a) (*(volatile uint16_t *)(a))
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))
#define INK RGB(7,8,9)
#define PAPER RGB(31,31,30)
#define TEAL RGB(9,14,17)
#define MUTED RGB(13,14,14)
#define WHITE 32767
enum {A=1,B=2,SELECT=4,START=8,RIGHT=16,LEFT=32,UP=64,DOWN=128,R=256,L=512};
enum {LIST,DETAIL,FILTER,SEARCH,HELP,EVENTS,CONTENTS};
#define PAGE_COUNT 15
static const char *page_names[PAGE_COUNT]={"基础与种族值","招式与学习来源","推荐配装","努力值与个体值","同物种形态","名称与登记记录","特性详细效果","进化路线与条件","形态变化与机制","携带道具说明","配装思路与赛制","本项目获取与登记","资料详情与核验","图片与异色","实际 HP 计算"};
static uint8_t flags[OMNI_CATALOG_ENTRY_COUNT];
static OmniDexState state={flags,OMNI_CATALOG_ENTRY_COUNT};
static OmniDexFilter filter={0,0,0,0,0,0,1};
static uint16_t results[OMNI_CATALOG_ENTRY_COUNT],total,cursor,entry,page,scroll,plan_cursor;
static uint16_t old_keys,held_frames;
static uint8_t screen,filter_cursor,search_cursor,move_detail,opened,dirty=1;
static unsigned source_offset;
static uint16_t text_scroll,text_lines,contents_cursor;
static uint8_t image_variant,hp_field,hp_level=50,hp_iv=31,hp_dynamax=10;
static uint16_t hp_ev;
/* Passive emulator diagnostics: never an input or progress override. */
volatile uint32_t omni_dex_probe[12]={0x44455850,0x4f4d4e49};
static char search[25];
static uint8_t save_buffer[12288];
static uint32_t save_sequence;
static int save_slot=-1;
static OmniDexSaveCallback host_save;
static void *host_context;
static const char *message="";
/* Exported diagnostics are observed by emulator tests through battery RAM. */
static const char save_signature[] __attribute__((used))="SRAM_V113";

#ifdef OMNI_GBA_STANDALONE
#define EVENT_TEST_ENABLED 1
void *memset(void *d,int v,size_t n){uint8_t *p=d;while(n--)*p++=(uint8_t)v;return d;}
void *memcpy(void *d,const void *s,size_t n){uint8_t *p=d;const uint8_t *q=s;while(n--)*p++=*q++;return d;}
#else
#define EVENT_TEST_ENABLED 0
#endif
static unsigned length(const char *s){unsigned n=0;while(s[n])++n;return n;}
/* Large fills use synchronous DMA3; tiny glyph/sprite writes stay on CPU.
 * This keeps button sampling responsive even on the actual ARM7TDMI. */
static void box(int x,int y,int w,int h,uint16_t color){
 int row,col;volatile uint16_t *v=(volatile uint16_t*)0x06000000;
 if(x<0){w+=x;x=0;}if(y<0){h+=y;y=0;}if(x+w>240)w=240-x;if(y+h>160)h=160-y;if(w<=0||h<=0)return;
 if(w==1&&h==1){v[y*240+x]=color;return;}
 for(row=y;row<y+h;++row){volatile uint16_t *d=v+row*240+x;int n=w;if(n>=16){volatile uint32_t pair=(uint32_t)color|((uint32_t)color<<16);if(x&1){*d++=color;--n;}*(volatile uint32_t*)0x040000d4=(uint32_t)(uintptr_t)&pair;*(volatile uint32_t*)0x040000d8=(uint32_t)(uintptr_t)d;*(volatile uint32_t*)0x040000dc=0x85000000u|(unsigned)(n/2);if(n&1)d[n-1]=color;}else for(col=0;col<n;++col)d[col]=color;}
}
static uint32_t utf8(const char **p){const unsigned char *s=(const unsigned char*)*p;uint32_t c=*s++;if(c>=0xe0){c=((c&15)<<12)|((s[0]&63)<<6)|(s[1]&63);s+=2;}else if(c>=0xc0){c=((c&31)<<6)|(s[0]&63);++s;}*p=(const char*)s;return c;}
static unsigned glyph_large(int x,int y,uint32_t code,uint16_t color){unsigned lo=0,hi=gba_glyph_count,row,col;const GbaGlyph *g;const unsigned char *bits;while(lo<hi){unsigned mid=(lo+hi)/2;if(gba_glyphs[mid].code<code)lo=mid+1;else hi=mid;}if(lo>=gba_glyph_count||gba_glyphs[lo].code!=code)return 8;g=&gba_glyphs[lo];bits=gba_font+g->offset;for(row=0;row<16;++row)for(col=0;col<g->width;++col)if(bits[row*(g->width/8)+col/8]&(128>>(col&7)))box(x+(int)col,y+(int)row,1,1,color);return g->width;}
static void text_large(int x,int y,const char *s,uint16_t color,int end){while(*s){const char *p=s;uint32_t c=utf8(&s);int w=c<128?8:16;if(x+w>end)break;x+=(int)glyph_large(x,y,c,color);if(s==p)break;}}
static const GbaGlyph *small_glyph(uint32_t code){unsigned lo=0,hi=gba_small_glyph_count;while(lo<hi){unsigned mid=(lo+hi)/2;if(gba_small_glyphs[mid].code<code)lo=mid+1;else hi=mid;}return lo<gba_small_glyph_count&&gba_small_glyphs[lo].code==code?&gba_small_glyphs[lo]:0;}
static unsigned glyph(int x,int y,uint32_t code,uint16_t color){const GbaGlyph *g=small_glyph(code);unsigned row,col,stride;const uint8_t *bits;if(!g)return 6;stride=(g->width+7)/8;bits=gba_font+g->offset;for(row=0;row<12;++row)for(col=0;col<g->width;++col)if(bits[row*stride+col/8]&(128>>(col&7)))box(x+(int)col,y+(int)row,1,1,color);return g->width;}
static void text(int x,int y,const char *s,uint16_t color,int end){while(*s){uint32_t c=utf8(&s);const GbaGlyph *g=small_glyph(c);unsigned w=g?g->width:6;if(x+(int)w>end)break;x+=(int)glyph(x,y,c,color);}}
static void short_text(int x,int y,const char *s,uint16_t color,int end){const char *p=s;unsigned width=0;while(*p){const GbaGlyph *g=small_glyph(utf8(&p));width+=g?g->width:6;}if(width<=(unsigned)(end-x)){text(x,y,s,color,end);return;}while(*s){uint32_t c=utf8(&s);const GbaGlyph *g=small_glyph(c);unsigned w=g?g->width:6;if(x+(int)w>end-12)break;x+=(int)glyph(x,y,c,color);}text(x,y,"..",color,end);}
static void num(int x,int y,unsigned n,uint16_t color){char out[12],rev[12];unsigned i=0,j=0;do{rev[i++]=(char)('0'+n%10);n/=10;}while(n);while(i)out[j++]=rev[--i];out[j]=0;text(x,y,out,color,240);}
static uint32_t hash(const uint8_t *b,unsigned n){uint32_t h=2166136261u;while(n--)h=(h^*b++)*16777619u;return h;}
static void put32(uint8_t *p,uint32_t n){unsigned i;for(i=0;i<4;++i)p[i]=(uint8_t)(n>>(i*8));}
static uint32_t get32(const uint8_t *p){return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int read_slot(unsigned slot,uint32_t *sequence){volatile uint8_t *s=(volatile uint8_t*)(uintptr_t)(0x0e000000u+slot*16384u);unsigned i,n;uint8_t header[20];for(i=0;i<20;++i)header[i]=s[i];if(header[0]!='O'||header[1]!='D'||header[2]!='G'||header[3]!=1)return 0;n=get32(header+8);if(n<16||n>sizeof(save_buffer))return 0;for(i=0;i<n;++i)save_buffer[i]=s[20+i];if(get32(header+12)!=hash(save_buffer,n)||get32(header+16)!=hash(header,16))return 0;*sequence=get32(header+4);return (int)n;}
static void load_progress(void){uint32_t a=0,b=0;int na=read_slot(0,&a),nb=read_slot(1,&b),n,first=(nb&&(!na||(int32_t)(b-a)>0))?1:0;unsigned attempt;for(attempt=0;attempt<2;++attempt){unsigned slot=(unsigned)first^attempt;uint32_t sequence;n=read_slot(slot,&sequence);if(n&&omni_dex_load(&omni_pokedex_catalog,&state,save_buffer,(size_t)n)==OMNI_DEX_OK){save_slot=(int)slot;save_sequence=sequence;return;}}}
static int save_progress(void){unsigned i,target=(unsigned)(save_slot==0?1:0);size_t n=0;uint8_t header[20];volatile uint8_t *s=(volatile uint8_t*)(uintptr_t)(0x0e000000u+target*16384u);if(omni_dex_save(&omni_pokedex_catalog,&state,save_buffer,sizeof(save_buffer),&n))return 0;if(host_save)return host_save(save_buffer,n,host_context);
#ifndef OMNI_GBA_STANDALONE
return 0;
#endif
header[0]='O';header[1]='D';header[2]='G';header[3]=1;put32(header+4,save_sequence+1);put32(header+8,(uint32_t)n);put32(header+12,hash(save_buffer,(unsigned)n));put32(header+16,hash(header,16));s[0]=0;for(i=0;i<n;++i)s[20+i]=save_buffer[i];for(i=1;i<20;++i)s[i]=header[i];s[0]=header[0];{uint32_t sequence;int read=read_slot(target,&sequence);if(read!=(int)n||sequence!=save_sequence+1)return 0;}save_slot=(int)target;++save_sequence;return 1;}
const OmniDexState *omni_game_dex_state(void){return &state;}
int omni_game_dex_bind(OmniDexState supplied,OmniDexSaveCallback save,void *context){if(!supplied.flags||supplied.count!=OMNI_CATALOG_ENTRY_COUNT||!save)return OMNI_DEX_ARGUMENT;state=supplied;host_save=save;host_context=context;return OMNI_DEX_OK;}
int omni_game_dex_restore(const uint8_t *bytes,size_t n){return omni_dex_load(&omni_pokedex_catalog,&state,bytes,n);}
int omni_game_dex_event(uint32_t id,uint8_t event){int code=omni_dex_record(&omni_pokedex_catalog,&state,id,event);if(!code){int saved=save_progress();message=saved?"记录已保存":"保存失败";dirty=1;if(!saved)return OMNI_GAME_DEX_SAVE_FAILED;}return code;}
static void query(void){filter.text=search;total=omni_dex_query(&omni_pokedex_catalog,&state,&filter,0,results,OMNI_CATALOG_ENTRY_COUNT);if(cursor>=total)cursor=0;}
static void panel(int x,int y,int w,int h,uint16_t fill){box(x+1,y+1,w,h,RGB(9,12,12));box(x,y,w,h,RGB(13,15,14));box(x+1,y+1,w-2,h-2,WHITE);box(x+3,y+3,w-6,h-6,fill);}
static void backdrop(void){unsigned y;for(y=0;y<160;y+=4){box(0,(int)y,240,2,RGB(17,23,14));box(0,(int)y+2,240,2,RGB(21,26,18));}}
static void title(const char *s){backdrop();panel(3,1,233,19,RGB(25,27,26));text(8,4,s,INK,211);if(screen==DETAIL){num(213,4,page+1,INK);text(229,4,">",INK,239);}panel(2,22,235,118,PAPER);}

static void footer(const char *s){box(0,143,240,17,RGB(10,13,14));box(1,144,238,15,RGB(26,28,26));box(2,144,236,1,WHITE);text(5,146,s,INK,236);}
/* Run-length RGB555 images decode directly into VRAM; bounded to 64 x 64. */
static void picture_offset(uint32_t offset,int x,int y){unsigned pos=0;const uint16_t *p;uint16_t mode;if(offset==0xffffffffu){text(x,y,"无此图片",MUTED,240);return;}p=(const uint16_t*)(gba_art+offset);mode=*p++;while(pos<4096){unsigned count=mode?*p++:1;uint16_t color=*p++;if(!count||count>4096-pos)return;while(count--){if(!(color&0x8000))box(x+(int)(pos%64),y+(int)(pos/64),1,1,color);++pos;}}}
static void picture(unsigned index,int x,int y){picture_offset(gba_info[index].art,x,y);}
/* Wrapped text is scrollable without truncation, using the same glyph widths as
 * the renderer. Explicit newlines remain paragraph boundaries. */
static void paragraph(const char *s){unsigned line=0,x=9;while(*s){uint32_t c=utf8(&s);unsigned w=c<128?6:12;if(c=='\n'){++line;x=9;continue;}if(x+w>228){++line;x=9;}if(line>=text_scroll&&line<text_scroll+6)glyph((int)x,27+(int)(line-text_scroll)*18,c,INK);x+=w;}text_lines=(uint16_t)(line+1);if(text_scroll>=text_lines)text_scroll=text_lines-1;}
static const GbaPlanText *current_plan(void){const GbaInfo *i=&gba_info[entry];if(!i->plan_count)return 0;if(plan_cursor>=i->plan_count)plan_cursor=0;return &gba_plan_text[gba_plan_indexes[i->plan_start+plan_cursor]];}
static void draw_reading(void){const GbaExtra *e=&gba_extra[entry];const GbaPlanText *p=current_plan();const char *s="";title(page_names[page]);switch(page){case 6:s=e->abilities;break;case 7:s=e->evolution;break;case 8:s=e->transition;break;case 9:s=p?p->item_detail:"暂无已核验的携带道具方案。";break;case 10:s=p?p->strategy:"暂无已核验的培养方案。";break;case 11:s=e->acquisition;break;case 12:s=e->evidence;break;}paragraph(s);footer(page==9||page==10?"上下滚动 A换方案 SELECT目录":"上下滚动 SELECT目录 B返回");}
static void draw_contents(void){unsigned i;title("图鉴页面目录");for(i=contents_cursor/6*6;i<PAGE_COUNT&&i<contents_cursor/6*6+6;++i){int y=24+(int)(i%6)*18;uint16_t c=i==contents_cursor?WHITE:INK;if(i==contents_cursor)box(2,y-1,236,18,TEAL);num(5,y,i+1,c);text(32,y,page_names[i],c,238);}footer("上下选择 A打开 B返回");}
static void draw_images(void){static const char *names[]={"正面","背面","异色正面","异色背面","雌性正面","雌性背面","异色雌性正面","异色雌性背面"};title("图像与异色");text(10,27,names[image_variant],INK,225);picture_offset(gba_variants[entry][image_variant],88,44);text(10,117,"上下：切换外观",MUTED,232);footer("SELECT目录 B返回");}
static void draw_hp(void){const OmniDexEntry *e=&omni_pokedex_catalog.entries[entry];unsigned i;uint16_t hp=omni_hp_stat(omni_pokedex_profiles[entry].stats[0],hp_level,hp_iv,hp_ev,e->national==292),dmax=omni_dynamax_max_hp(hp,hp_dynamax,e->national==292);static const char *labels[]={"等级","HP 个体值","HP 努力值","极巨等级"};unsigned values[]={hp_level,hp_iv,hp_ev,hp_dynamax};title("实际 HP 计算（示例）");for(i=0;i<4;++i){int y=23+(int)i*18;uint16_t c=i==hp_field?WHITE:INK;if(i==hp_field)box(2,y-1,236,18,TEAL);text(4,y,labels[i],c,165);num(180,y,values[i],c);}text(4,97,"通常 HP",INK,115);num(132,97,hp,INK);text(4,116,"极巨后",INK,115);if(e->category==11||e->category==3)num(132,116,dmax,INK);else text(116,116,"不作资格判定",MUTED,239);footer("A加 START减 B返回");}
static void draw_list(void){
 unsigned start=cursor>2?cursor-2:0,i,y,idx=total?results[cursor]:0;
 const OmniDexEntry *selected=&omni_pokedex_catalog.entries[idx];
 if(total>6&&start>total-6)start=total-6;
 backdrop();panel(3,2,101,18,WHITE);text_large(10,3,"POKEDEX",INK,103);
 text(116,5,"全国图鉴",INK,174);num(204,5,total,INK);
 /* Collector column and a portrait viewport, as in the reference cartridge. */
 for(y=25;y<125;++y)for(i=0;i<39;++i){int dx=(int)i-2,dy=(int)y-73,d=dx*dx+dy*dy;if(d<43*43&&d>31*31)box((int)i,(int)y,1,1,RGB(8,12,13));}
 box(0,29,38,31,RGB(8,12,13));box(0,67,38,31,RGB(8,12,13));text(4,31,"已见",WHITE,39);num(4,45,omni_dex_count(&omni_pokedex_catalog,&state,1,0),WHITE);
 text(4,69,"捕获",WHITE,39);num(4,83,omni_dex_count(&omni_pokedex_catalog,&state,2,0),WHITE);
 panel(40,24,65,101,WHITE);
 for(y=29;y<46;y+=4)box(44,(int)y,57,2,RGB(27,28,27));
 for(y=101;y<116;y+=4)box(44,(int)y,57,2,RGB(27,28,27));
 if(total){picture(idx,41,43);box(44,111,57,11,WHITE);text(45,110,gba_info[idx].category,INK,101);}
 panel(108,23,129,102,RGB(30,30,12));
 for(i=start;i<total&&i<start+6;++i){const OmniDexEntry *e=&omni_pokedex_catalog.entries[results[i]];int yy=28+(int)(i-start)*15;char no[5];unsigned n=e->national;no[0]=(char)('0'+n/1000);no[1]=(char)('0'+n/100%10);no[2]=(char)('0'+n/10%10);no[3]=(char)('0'+n%10);no[4]=0;
  if(i==cursor){box(112,yy-1,117,14,WHITE);box(110,yy+3,2,5,INK);}
  text(114,yy,n>=1000?no:no+1,INK,139);short_text(144,yy,gba_info[results[i]].list_name,INK,228);
  if(state.flags[results[i]]&2){box(136,yy+3,5,5,INK);box(137,yy+4,3,3,RGB(29,8,8));}else if(state.flags[results[i]]&1)box(138,yy+5,2,2,INK);
 }
 box(231,28,2,89,RGB(23,23,7));box(230,28+(total>1?cursor*81/(total-1):0),4,8,RGB(10,10,3));
 panel(3,128,233,14,PAPER);if(total)text(8,129,selected->name_zh,INK,231);else text(9,65,"没有匹配条目",INK,237);
 footer("A详情 SELECT筛选 START帮助");
}
static void draw_profile(void){
 const OmniDexEntry *e=&omni_pokedex_catalog.entries[entry];const OmniDexProfile *p=&omni_pokedex_profiles[entry];
 static const char *labels[]={"HP","攻击","防御","特攻","特防","速度"};static const char *tabs[]={"资料","招式","培养","更多"};unsigned i;const char *s=e->name_zh;int xx=87,yy=27;
 backdrop();for(i=0;i<4;++i){panel(3+(int)i*59,1,56,18,i==0?RGB(22,27,31):RGB(18,23,26));text(18+(int)i*59,4,tabs[i],INK,58+(int)i*59);}
 panel(3,23,233,118,PAPER);box(7,27,72,58,RGB(27,28,27));picture(entry,10,24);
 while(*s&&yy<53){uint32_t c=utf8(&s);int w=c<128?6:12;if(xx+w>231){xx=87;yy+=13;}xx+=(int)glyph(xx,yy,c,INK);}
 text(86,57,gba_info[entry].types,TEAL,231);text(86,71,"No.",MUTED,113);num(110,71,e->national,INK);text(145,71,gba_info[entry].category,MUTED,231);
 box(8,85,223,1,RGB(23,25,24));
 for(i=0;i<6;++i){int x=(i%2)*113+9,y=91+(int)(i/2)*15;unsigned value=p->stats[i];text(x,y,labels[i],MUTED,x+25);num(x+28,y,value,INK);box(x+49,y+3,52,7,RGB(24,26,25));box(x+50,y+4,(int)(value>255?50:value*50/255),5,i==0?RGB(16,23,9):i==5?RGB(17,15,25):RGB(11,20,23));}
 footer("左右翻页 L/R换精灵 SELECT目录");
}
static void draw_moves(void){unsigned i;const GbaInfo *info=&gba_info[entry];title("招式来源参考");num(172,2,info->move_count,WHITE);if(!info->move_count)text(4,43,"此形态招式尚待核实",INK,240);if(move_detail>=2&&info->move_count){const GbaMove *m=&gba_moves[gba_learnsets[info->move_start+scroll]];paragraph(move_detail==2?m->effect:gba_move_sources_readable[info->move_start+scroll]);}else if(move_detail&&info->move_count){const GbaMove *m=&gba_moves[gba_learnsets[info->move_start+scroll]];text(4,25,m->name,INK,237);text(4,45,m->kind,TEAL,237);text(4,66,"威力",MUTED,68);num(68,66,m->power,INK);text(122,66,"命中",MUTED,185);if(m->accuracy)num(187,66,m->accuracy,INK);else text(187,66,"必中",INK,238);text(4,86,"PP",MUTED,70);num(68,86,m->pp,INK);{const char *sources=gba_move_sources[info->move_start+scroll];char line[29];unsigned j,n=length(sources);if(source_offset>=n)source_offset=0;for(i=0;i<2;++i){unsigned start=source_offset+i*28;for(j=0;j<28&&start+j<n;++j)line[j]=sources[start+j];line[j]=0;text(4,107+(int)i*16,line,MUTED,239);}}}else for(i=scroll/5*5;i<info->move_count&&i<scroll/5*5+5;++i){const GbaMove *m=&gba_moves[gba_learnsets[info->move_start+i]];int y=23+(int)(i%5)*22;if(i==scroll)box(2,y-1,236,20,TEAL);text(4,y,m->name,i==scroll?WHITE:INK,132);text(137,y,m->kind,i==scroll?WHITE:MUTED,240);}footer(move_detail?"A效果/来源 上下浏览 B列表":"上下选择 A资料 SELECT目录");}
static void draw_plan(void){const GbaInfo *info=&gba_info[entry];unsigned index,i;const GbaPlanText *t;title("培养与携带道具");if(!info->plan_count){text(4,35,"暂无已核验参考方案",INK,237);text(4,59,"未自动套用普通形态",MUTED,237);footer("左右翻页  B返回");return;}if(plan_cursor>=info->plan_count)plan_cursor=0;index=gba_plan_indexes[info->plan_start+plan_cursor];t=&gba_plan_text[index];text(4,23,t->item,TEAL,180);num(189,23,plan_cursor+1,INK);text(4,41,t->ability,INK,149);text(153,41,t->nature,INK,239);for(i=0;i<4;++i)text(4,59+(int)i*16,t->moves[i],INK,237);text(4,124,t->format,MUTED,160);text(166,124,"参考方案",MUTED,239);footer("上下换方案 右看数值 B返回");}
static void draw_plan_stats(void){const GbaInfo *info=&gba_info[entry];unsigned index,i;const OmniTrainingPlan *p;static const char *labels[]={"HP","攻击","防御","特攻","特防","速度"};title("培养数值  EV / IV");if(!info->plan_count){text(4,40,"暂无参考方案",INK,237);footer("左右翻页  B返回");return;}index=gba_plan_indexes[info->plan_start+plan_cursor];p=&omni_training_plans[index];text(4,23,gba_plan_text[index].format,TEAL,154);num(170,23,plan_cursor+1,INK);text(4,42,"努力值 / 个体值",MUTED,237);for(i=0;i<6;++i){int x=(i%2)*120,y=63+(int)(i/2)*20;text(x+4,y,labels[i],INK,x+42);num(x+45,y,p->evs[i],INK);text(x+72,y,"/",MUTED,x+84);num(x+84,y,p->ivs[i],INK);}text(4,124,"剧情获取尚未配置",MUTED,237);footer("上下换方案 左右翻页 B返回");}
static void draw_identity(void){const OmniDexEntry *e=&omni_pokedex_catalog.entries[entry];const char *s=e->name_zh;int x=4,y=24;title("完整名称与记录");while(*s&&y<80){uint32_t c=utf8(&s);int w=c<128?6:12;if(x+w>235){x=4;y+=18;}x+=(int)glyph(x,y,c,INK);}text(4,82,"全国编号",MUTED,145);num(151,82,e->national,INK);text(4,101,e->research_only?"资料核验中：不可登记":state.flags[entry]&2?"已捕捉登记":state.flags[entry]&1?"已见过":"尚未见过",TEAL,238);if(EVENT_TEST_ENABLED)text(4,123,"START进入事件联调",MUTED,238);footer("左右翻页  B返回");}
static unsigned form_count(void){unsigned i,n=0;uint16_t national=omni_pokedex_catalog.entries[entry].national;for(i=0;i<OMNI_CATALOG_ENTRY_COUNT;++i)if(omni_dex_visible(&omni_pokedex_catalog.entries[i])&&((national&&omni_pokedex_catalog.entries[i].national==national)||i==entry))++n;return n;}
static uint16_t form_at(unsigned wanted){unsigned i,n=0;uint16_t national=omni_pokedex_catalog.entries[entry].national;for(i=0;i<OMNI_CATALOG_ENTRY_COUNT;++i)if(omni_dex_visible(&omni_pokedex_catalog.entries[i])&&((national&&omni_pokedex_catalog.entries[i].national==national)||i==entry)){if(n++==wanted)return (uint16_t)i;}return entry;}
static void draw_forms(void){unsigned i,n=form_count();title("同物种形态");for(i=scroll/6*6;i<n&&i<scroll/6*6+6;++i){int y=24+(int)(i%6)*18;uint16_t idx=form_at(i);if(i==scroll)box(2,y-1,236,18,TEAL);text(5,y,omni_pokedex_catalog.entries[idx].name_zh,i==scroll?WHITE:INK,235);}footer("上下选择 A切换 左右翻页 B返回");}
static void draw_filter(void){static const char *names[]={"编号","分类","世代","属性","进度","研究"};static const char *categories[]={"全部","普通","Mega","超极巨化","地区","原始回归","究极爆发","太晶","其他","羁绊","外观","极巨化","战斗状态","合体","性别","体型","属性形态","特殊形态","改版形态"};static const char *types[]={"全部","一般","火","水","电","草","冰","格斗","毒","地面","飞行","超能力","虫","岩石","幽灵","龙","恶","钢","妖精"};static const char *progress[]={"全部","未发现","已见过","已登记","已解锁"};unsigned i;title("筛选  START清空");for(i=0;i<6;++i){int y=24+(int)i*18;uint16_t color=i==filter_cursor?WHITE:INK;if(i==filter_cursor)box(2,y-1,236,18,TEAL);text(5,y,names[i],color,80);if(i==0){if(filter.national)num(105,y,filter.national,color);else text(105,y,"全部",color,235);}else if(i==1)text(105,y,categories[filter.category],color,235);else if(i==2){if(filter.generation)num(105,y,filter.generation,color);else text(105,y,"全部",color,235);}else if(i==3)text(105,y,types[filter.type],color,235);else if(i==4)text(105,y,progress[filter.progress],color,235);else text(105,y,filter.include_research?"包含":"隐藏",color,235);}footer("左右调整 A应用 SELECT名称");}
static void draw_search(void){unsigned i;static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ -<";title("英文名称搜索");text(5,25,search,INK,236);for(i=0;i<29;++i){int x=8+(int)(i%10)*23,y=48+(int)(i/10)*25;char s[2]={alphabet[i],0};if(i==search_cursor)box(x-3,y-2,21,23,TEAL);text(x,y,s,i==search_cursor?WHITE:INK,240);}footer("A输入 <退格 START查询 B返回");}
static void draw_help(void){title("图鉴操作与范围");text(4,24,"方向键浏览  A查看  B返回",INK,237);text(4,42,"SELECT筛选  L/R快速翻页",INK,237);text(4,60,"详情 SELECT 打开页面目录",INK,237);text(4,78,"招式效果为第九世代参考原文",INK,237);if(EVENT_TEST_ENABLED){text(4,96,"当前为独立图鉴联调程序",MUTED,237);text(4,114,"SELECT：事件联调菜单",MUTED,237);}footer("B返回图鉴");}
static void draw_events(void){title("事件联调  非剧情奖励");text(4,25,omni_pokedex_catalog.entries[entry].name_zh,INK,238);text(4,47,"A模拟见过 R模拟捕捉",INK,238);text(4,68,"L模拟形态解锁",INK,238);text(4,89,"只读羁绊拒绝登记",MUTED,238);text(4,114,message,TEAL,238);footer("B返回；自动双槽保存");}
static void draw(void){box(0,0,240,160,PAPER);switch(screen){case LIST:draw_list();break;case DETAIL:if(page==0)draw_profile();else if(page==1)draw_moves();else if(page==2)draw_plan();else if(page==3)draw_plan_stats();else if(page==4)draw_forms();else if(page==5)draw_identity();else if(page<=12)draw_reading();else if(page==13)draw_images();else draw_hp();break;case CONTENTS:draw_contents();break;case FILTER:draw_filter();break;case SEARCH:draw_search();break;case HELP:draw_help();break;case EVENTS:draw_events();break;}dirty=0;}
uint8_t omni_game_dex_is_open(void){return opened;}
void omni_gba_box(int x,int y,int w,int h,uint16_t c){box(x,y,w,h,c);}
void omni_gba_text(int x,int y,const char *s,uint16_t c,int end){text_large(x,y,s,c,end);}
void omni_gba_num(int x,int y,unsigned n,uint16_t c){char out[12],rev[12];unsigned i=0,j=0;do{rev[i++]=(char)(48+n%10);n/=10;}while(n);while(i)out[j++]=rev[--i];out[j]=0;text_large(x,y,out,c,240);}
void omni_gba_picture(unsigned index,int x,int y){picture(index,x,y);}
void omni_game_dex_open_entry(uint32_t id){int32_t found=omni_dex_find(&omni_pokedex_catalog,id);if(found>=0&&!omni_dex_visible(&omni_pokedex_catalog.entries[found]))found=omni_dex_find(&omni_pokedex_catalog,omni_pokedex_profiles[found].parent_id);omni_game_dex_open();if(found>=0){entry=(uint16_t)found;screen=DETAIL;page=scroll=plan_cursor=text_scroll=0;move_detail=image_variant=0;}}
void omni_game_dex_open(void){opened=1;screen=LIST;query();dirty=1;}
void omni_game_dex_tick(uint16_t keys){uint16_t pressed=keys&~old_keys;unsigned max;old_keys=keys;if(!opened)return;if(keys){++held_frames;if(held_frames>20&&(held_frames%5)==0)pressed|=keys&(UP|DOWN|LEFT|RIGHT);}else held_frames=0;
 if(pressed){dirty=1;
  if(screen==LIST){if(pressed&B){opened=0;return;}if((pressed&UP)&&total)cursor=cursor?cursor-1:total-1;if((pressed&DOWN)&&total)cursor=(cursor+1)%total;if((pressed&L)&&total)cursor=cursor>=36?cursor-36:0;if((pressed&R)&&total)cursor=cursor+36<total?cursor+36:total-1;if((pressed&A)&&total){entry=results[cursor];page=scroll=plan_cursor=text_scroll=0;move_detail=image_variant=0;screen=DETAIL;}if(pressed&SELECT)screen=FILTER;if(pressed&START)screen=HELP;}
  else if(screen==DETAIL){if(pressed&B){if(move_detail){move_detail=0;text_scroll=0;}else screen=LIST;}if(pressed&RIGHT){page=(page+1)%PAGE_COUNT;scroll=text_scroll=0;move_detail=0;source_offset=0;}if(pressed&LEFT){page=(page+PAGE_COUNT-1)%PAGE_COUNT;scroll=text_scroll=0;move_detail=0;source_offset=0;}if(pressed&(L|R)){unsigned pos;for(pos=0;pos<total&&results[pos]!=entry;++pos){}if(total){cursor=pos<total?(uint16_t)((pos+total+((pressed&R)?1:-1))%total):0;entry=results[cursor];}scroll=plan_cursor=text_scroll=0;move_detail=image_variant=0;}if(page==1){max=gba_info[entry].move_count;if(move_detail<2){if((pressed&DOWN)&&max){scroll=(scroll+1)%max;source_offset=0;}if((pressed&UP)&&max){scroll=(scroll+max-1)%max;source_offset=0;}}else {if((pressed&DOWN)&&text_scroll+6<text_lines)++text_scroll;if((pressed&UP)&&text_scroll)--text_scroll;}if((pressed&A)&&max){move_detail=(move_detail+1)%4;text_scroll=source_offset=0;}}if(page==2||page==3){max=gba_info[entry].plan_count;if(max){if(pressed&DOWN)plan_cursor=(plan_cursor+1)%max;if(pressed&UP)plan_cursor=(plan_cursor+max-1)%max;}}if(page==4){max=form_count();if(pressed&DOWN)scroll=(scroll+1)%max;if(pressed&UP)scroll=(scroll+max-1)%max;if(pressed&A){entry=form_at(scroll);page=scroll=plan_cursor=text_scroll=0;image_variant=0;}}if(page>=6&&page<=12){if((pressed&DOWN)&&text_scroll+6<text_lines)++text_scroll;if((pressed&UP)&&text_scroll)--text_scroll;if((page==9||page==10)&&(pressed&A)&&gba_info[entry].plan_count){plan_cursor=(plan_cursor+1)%gba_info[entry].plan_count;text_scroll=0;}}
if(page==13){if(pressed&DOWN)image_variant=(image_variant+1)%8;if(pressed&UP)image_variant=(image_variant+7)%8;}
if(page==14){unsigned v,limit,min;if(pressed&DOWN)hp_field=(hp_field+1)%4;if(pressed&UP)hp_field=(hp_field+3)%4;v=hp_field==0?hp_level:hp_field==1?hp_iv:hp_field==2?hp_ev:hp_dynamax;limit=hp_field==0?100:hp_field==1?31:hp_field==2?252:10;min=hp_field==0?1:0;if(pressed&A)v=v<limit?v+1:min;if(pressed&START)v=v>min?v-1:limit;if(hp_field==0)hp_level=(uint8_t)v;else if(hp_field==1)hp_iv=(uint8_t)v;else if(hp_field==2)hp_ev=(uint16_t)v;else hp_dynamax=(uint8_t)v;}
if(pressed&SELECT){contents_cursor=page;screen=CONTENTS;}
if(EVENT_TEST_ENABLED&&page!=14&&(pressed&START))screen=EVENTS;}
  else if(screen==CONTENTS){if(pressed&UP)contents_cursor=(contents_cursor+PAGE_COUNT-1)%PAGE_COUNT;if(pressed&DOWN)contents_cursor=(contents_cursor+1)%PAGE_COUNT;if(pressed&A){page=contents_cursor;scroll=text_scroll=0;move_detail=0;screen=DETAIL;}if(pressed&B)screen=DETAIL;}
  else if(screen==FILTER){unsigned value=0,limit=0,step=1;if(pressed&UP)filter_cursor=(filter_cursor+5)%6;if(pressed&DOWN)filter_cursor=(filter_cursor+1)%6;switch(filter_cursor){case 0:value=filter.national;limit=1025;break;case 1:value=filter.category;limit=18;break;case 2:value=filter.generation;limit=9;break;case 3:value=filter.type;limit=18;break;case 4:value=filter.progress;limit=4;break;default:value=filter.include_research;limit=1;break;}if(filter_cursor==0&&(pressed&(L|R)))step=100;if(pressed&(RIGHT|R))value=(value+step)%(limit+1);if(pressed&(LEFT|L))value=(value+limit+1-step)%(limit+1);switch(filter_cursor){case 0:filter.national=(uint16_t)value;break;case 1:if(value==11)value=(pressed&(LEFT|L))?10:12;filter.category=(uint8_t)value;break;case 2:filter.generation=(uint8_t)value;break;case 3:filter.type=(uint8_t)value;break;case 4:filter.progress=(uint8_t)value;break;default:filter.include_research=(uint8_t)value;break;}if(pressed&(A|B)){cursor=0;query();screen=LIST;}if(pressed&SELECT)screen=SEARCH;if(pressed&START){memset(&filter,0,sizeof(filter));filter.include_research=1;search[0]=0;}}
  else if(screen==SEARCH){static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ -<";unsigned n=length(search);if(pressed&RIGHT)search_cursor=(search_cursor+1)%29;if(pressed&LEFT)search_cursor=(search_cursor+28)%29;if(pressed&DOWN)search_cursor=(search_cursor+10)%29;if(pressed&UP)search_cursor=(search_cursor+19)%29;if(pressed&A){if(search_cursor==28){if(n)search[n-1]=0;}else if(n<24){search[n]=alphabet[search_cursor];search[n+1]=0;}}if(pressed&START){cursor=0;query();screen=LIST;}if(pressed&B)screen=FILTER;}
  else if(screen==HELP){if(pressed&B)screen=LIST;if(EVENT_TEST_ENABLED&&(pressed&SELECT)){if(total)entry=results[cursor];screen=EVENTS;}}
  else if(screen==EVENTS){int code=0;if(pressed&A)code=omni_game_dex_event(omni_pokedex_catalog.entries[entry].id,1);if(pressed&R)code=omni_game_dex_event(omni_pokedex_catalog.entries[entry].id,2);if(pressed&L)code=omni_game_dex_event(omni_pokedex_catalog.entries[entry].id,4);if(code)message=code==OMNI_GAME_DEX_SAVE_FAILED?"保存失败，请重试":"未登记：资料尚未审定";if(pressed&B){screen=LIST;query();}}
 }
 if(dirty)draw();
 omni_dex_probe[2]=screen;omni_dex_probe[3]=page;omni_dex_probe[4]=entry;omni_dex_probe[5]=text_scroll;omni_dex_probe[6]=text_lines;omni_dex_probe[7]=move_detail;omni_dex_probe[8]=image_variant;omni_dex_probe[9]=plan_cursor;omni_dex_probe[10]=scroll;omni_dex_probe[11]=opened;
}
#ifdef OMNI_GBA_STANDALONE
int main(void){REG16(0x04000000)=0x0403;REG16(0x04000204)=0x4317;(void)save_signature;load_progress();omni_game_dex_open();for(;;){while(REG16(0x04000006)>=160){}while(REG16(0x04000006)<160){}if(!omni_game_dex_is_open()){box(0,0,240,160,PAPER);title("OMNI 图鉴联调");text(8,60,"按 A 打开图鉴",INK,236);footer("独立程序；游戏世界尚未接入");if((~REG16(0x04000130))&A){omni_game_dex_open();old_keys=A;}}else omni_game_dex_tick((uint16_t)(~REG16(0x04000130)&1023));}}

#endif
