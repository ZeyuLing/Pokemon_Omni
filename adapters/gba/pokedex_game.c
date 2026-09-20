#include <stdint.h>
#include <stddef.h>
#ifndef OMNI_GBA_STANDALONE
#include "omni/memory.h"
#endif
#include "omni/pokedex.h"
#include "omni/training.h"
#include "catalog.h"
#include "plans.h"
#include "gba_data.h"
#include "pokedex_game.h"

#define REG16(a) (*(volatile uint16_t *)(a))
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))
#define INK RGB(3,9,8)
#define PAPER RGB(30,30,27)
#define TEAL RGB(3,17,15)
#define MUTED RGB(13,16,14)
#define WHITE 32767
enum {A=1,B=2,SELECT=4,START=8,RIGHT=16,LEFT=32,UP=64,DOWN=128,R=256,L=512};
enum {LIST,DETAIL,FILTER,SEARCH,HELP,EVENTS};
static uint8_t flags[OMNI_CATALOG_ENTRY_COUNT];
static OmniDexState state={flags,OMNI_CATALOG_ENTRY_COUNT};
static OmniDexFilter filter={0,0,0,0,0,0,1};
static uint16_t results[OMNI_CATALOG_ENTRY_COUNT],total,cursor,entry,page,scroll,plan_cursor;
static uint16_t old_keys,held_frames;
static uint8_t screen,filter_cursor,search_cursor,move_detail,opened,dirty=1;
static unsigned source_offset;
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
static void box(int x,int y,int w,int h,uint16_t color){int i,j;volatile uint16_t *v=(volatile uint16_t*)0x06000000;for(j=y;j<y+h&&j<160;++j)for(i=x;i<x+w&&i<240;++i)if(i>=0&&j>=0)v[j*240+i]=color;}
static uint32_t utf8(const char **p){const unsigned char *s=(const unsigned char*)*p;uint32_t c=*s++;if(c>=0xe0){c=((c&15)<<12)|((s[0]&63)<<6)|(s[1]&63);s+=2;}else if(c>=0xc0){c=((c&31)<<6)|(s[0]&63);++s;}*p=(const char*)s;return c;}
static unsigned glyph(int x,int y,uint32_t code,uint16_t color){unsigned lo=0,hi=gba_glyph_count,row,col;const GbaGlyph *g;const unsigned char *bits;while(lo<hi){unsigned mid=(lo+hi)/2;if(gba_glyphs[mid].code<code)lo=mid+1;else hi=mid;}if(lo>=gba_glyph_count||gba_glyphs[lo].code!=code)return 8;g=&gba_glyphs[lo];bits=gba_font+g->offset;for(row=0;row<16;++row)for(col=0;col<g->width;++col)if(bits[row*(g->width/8)+col/8]&(128>>(col&7)))box(x+(int)col,y+(int)row,1,1,color);return g->width;}
static void text(int x,int y,const char *s,uint16_t color,int end){while(*s){const char *p=s;uint32_t c=utf8(&s);int w=c<128?8:16;if(x+w>end)break;x+=(int)glyph(x,y,c,color);if(s==p)break;}}
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
static void title(const char *s){box(0,0,240,21,TEAL);text(5,2,s,WHITE,237);}
static void footer(const char *s){box(0,142,240,18,TEAL);text(4,143,s,WHITE,239);}
static void picture(unsigned index,int x,int y){unsigned row,col;uint32_t offset=gba_info[index].art;const uint16_t *pixels;if(offset==0xffffffffu){text(x,y,"缺图",MUTED,240);return;}pixels=(const uint16_t*)(gba_art+offset);for(row=0;row<64;++row)for(col=0;col<64;++col){uint16_t color=pixels[row*64+col];if(!(color&0x8000))box(x+(int)col,y+(int)row,1,1,color);}}
static void draw_list(void){unsigned start=cursor/6*6,i;title("OMNI 全国图鉴");num(182,2,total,WHITE);for(i=start;i<total&&i<start+6;++i){const OmniDexEntry *e=&omni_pokedex_catalog.entries[results[i]];int y=24+(int)(i-start)*18;uint16_t color=INK;if(i==cursor){box(2,y-1,236,18,TEAL);color=WHITE;}num(5,y,e->national,color);text(39,y,e->name_zh,color,217);if(state.flags[results[i]]&2)text(220,y,"捕",color,240);else if(state.flags[results[i]]&1)text(220,y,"见",color,240);}if(!total)text(16,57,"没有匹配的条目",INK,235);footer("A详情 SELECT筛选 START帮助");}
static void draw_profile(void){const OmniDexEntry *e=&omni_pokedex_catalog.entries[entry];const OmniDexProfile *p=&omni_pokedex_profiles[entry];static const char *labels[]={"HP","攻击","防御","特攻","特防","速度"};unsigned i;title(e->name_zh);text(4,24,gba_info[entry].types,TEAL,160);text(4,43,gba_info[entry].abilities,INK,160);text(4,62,gba_info[entry].category,MUTED,160);picture(entry,171,26);for(i=0;i<6;++i){int x=(i%2)*120,y=91+(int)(i/2)*16;text(x+5,y,labels[i],MUTED,x+47);num(x+52,y,p->stats[i],INK);}footer("左右翻页  L/R前后条目  B返回");}
static void draw_moves(void){unsigned i;const GbaInfo *info=&gba_info[entry];title("招式来源参考");num(172,2,info->move_count,WHITE);if(!info->move_count)text(4,43,"此形态招式尚待核实",INK,240);if(move_detail&&info->move_count){const GbaMove *m=&gba_moves[gba_learnsets[info->move_start+scroll]];text(4,25,m->name,INK,237);text(4,45,m->kind,TEAL,237);text(4,66,"威力",MUTED,68);num(68,66,m->power,INK);text(122,66,"命中",MUTED,185);if(m->accuracy)num(187,66,m->accuracy,INK);else text(187,66,"必中",INK,238);text(4,86,"PP",MUTED,70);num(68,86,m->pp,INK);{const char *sources=gba_move_sources[info->move_start+scroll];char line[29];unsigned j,n=length(sources);if(source_offset>=n)source_offset=0;for(i=0;i<2;++i){unsigned start=source_offset+i*28;for(j=0;j<28&&start+j<n;++j)line[j]=sources[start+j];line[j]=0;text(4,107+(int)i*16,line,MUTED,239);}}}else for(i=scroll/5*5;i<info->move_count&&i<scroll/5*5+5;++i){const GbaMove *m=&gba_moves[gba_learnsets[info->move_start+i]];int y=23+(int)(i%5)*22;if(i==scroll)box(2,y-1,236,20,TEAL);text(4,y,m->name,i==scroll?WHITE:INK,132);text(137,y,m->kind,i==scroll?WHITE:MUTED,240);}footer(move_detail?"SELECT更多来源 B回列表":"上下选择 A资料 左右翻页 B返回");}
static void draw_plan(void){const GbaInfo *info=&gba_info[entry];unsigned index,i;const GbaPlanText *t;title("培养与携带道具");if(!info->plan_count){text(4,35,"暂无已核验参考方案",INK,237);text(4,59,"未自动套用普通形态",MUTED,237);footer("左右翻页  B返回");return;}if(plan_cursor>=info->plan_count)plan_cursor=0;index=gba_plan_indexes[info->plan_start+plan_cursor];t=&gba_plan_text[index];text(4,23,t->item,TEAL,180);num(189,23,plan_cursor+1,INK);text(4,41,t->ability,INK,149);text(153,41,t->nature,INK,239);for(i=0;i<4;++i)text(4,59+(int)i*16,t->moves[i],INK,237);text(4,124,t->format,MUTED,160);text(166,124,"参考方案",MUTED,239);footer("上下换方案 右看数值 B返回");}
static void draw_plan_stats(void){const GbaInfo *info=&gba_info[entry];unsigned index,i;const OmniTrainingPlan *p;static const char *labels[]={"HP","攻击","防御","特攻","特防","速度"};title("培养数值  EV / IV");if(!info->plan_count){text(4,40,"暂无参考方案",INK,237);footer("左右翻页  B返回");return;}index=gba_plan_indexes[info->plan_start+plan_cursor];p=&omni_training_plans[index];text(4,23,gba_plan_text[index].format,TEAL,154);num(170,23,plan_cursor+1,INK);text(4,42,"努力值 / 个体值",MUTED,237);for(i=0;i<6;++i){int x=(i%2)*120,y=63+(int)(i/2)*20;text(x+4,y,labels[i],INK,x+42);num(x+45,y,p->evs[i],INK);text(x+72,y,"/",MUTED,x+84);num(x+84,y,p->ivs[i],INK);}text(4,124,"剧情获取尚未配置",MUTED,237);footer("上下换方案 左右翻页 B返回");}
static void draw_identity(void){const OmniDexEntry *e=&omni_pokedex_catalog.entries[entry];const char *s=e->name_zh;int x=4,y=24;title("完整名称与记录");while(*s&&y<80){uint32_t c=utf8(&s);int w=c<128?8:16;if(x+w>235){x=4;y+=18;}x+=(int)glyph(x,y,c,INK);}text(4,82,"全国编号",MUTED,145);num(151,82,e->national,INK);text(4,101,e->research_only?"资料核验中：不可登记":state.flags[entry]&2?"已捕捉登记":state.flags[entry]&1?"已见过":"尚未见过",TEAL,238);if(EVENT_TEST_ENABLED)text(4,123,"START进入事件联调",MUTED,238);footer("左右翻页  B返回");}
static unsigned form_count(void){unsigned i,n=0;uint16_t national=omni_pokedex_catalog.entries[entry].national;for(i=0;i<OMNI_CATALOG_ENTRY_COUNT;++i)if((national&&omni_pokedex_catalog.entries[i].national==national)||i==entry)++n;return n;}
static uint16_t form_at(unsigned wanted){unsigned i,n=0;uint16_t national=omni_pokedex_catalog.entries[entry].national;for(i=0;i<OMNI_CATALOG_ENTRY_COUNT;++i)if((national&&omni_pokedex_catalog.entries[i].national==national)||i==entry){if(n++==wanted)return (uint16_t)i;}return entry;}
static void draw_forms(void){unsigned i,n=form_count();title("同物种形态");for(i=scroll/6*6;i<n&&i<scroll/6*6+6;++i){int y=24+(int)(i%6)*18;uint16_t idx=form_at(i);if(i==scroll)box(2,y-1,236,18,TEAL);text(5,y,omni_pokedex_catalog.entries[idx].name_zh,i==scroll?WHITE:INK,235);}footer("上下选择 A切换 左右翻页 B返回");}
static void draw_filter(void){static const char *names[]={"编号","分类","世代","属性","进度","研究"};static const char *categories[]={"全部","普通","Mega","超极巨化","地区","原始回归","究极爆发","太晶","其他","羁绊","外观","极巨化","战斗状态","合体","性别","体型","属性形态","特殊形态"};static const char *types[]={"全部","一般","火","水","电","草","冰","格斗","毒","地面","飞行","超能力","虫","岩石","幽灵","龙","恶","钢","妖精"};static const char *progress[]={"全部","未发现","已见过","已登记","已解锁"};unsigned i;title("筛选  START清空");for(i=0;i<6;++i){int y=24+(int)i*18;uint16_t color=i==filter_cursor?WHITE:INK;if(i==filter_cursor)box(2,y-1,236,18,TEAL);text(5,y,names[i],color,80);if(i==0){if(filter.national)num(105,y,filter.national,color);else text(105,y,"全部",color,235);}else if(i==1)text(105,y,categories[filter.category],color,235);else if(i==2){if(filter.generation)num(105,y,filter.generation,color);else text(105,y,"全部",color,235);}else if(i==3)text(105,y,types[filter.type],color,235);else if(i==4)text(105,y,progress[filter.progress],color,235);else text(105,y,filter.include_research?"包含":"隐藏",color,235);}footer("左右调整 A应用 SELECT名称");}
static void draw_search(void){unsigned i;static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ -<";title("英文名称搜索");text(5,25,search,INK,236);for(i=0;i<29;++i){int x=8+(int)(i%10)*23,y=48+(int)(i/10)*25;char s[2]={alphabet[i],0};if(i==search_cursor)box(x-3,y-2,21,23,TEAL);text(x,y,s,i==search_cursor?WHITE:INK,240);}footer("A输入 <退格 START查询 B返回");}
static void draw_help(void){title("图鉴操作与范围");text(4,24,"方向键浏览  A查看  B返回",INK,237);text(4,42,"SELECT筛选  L/R快速翻页",INK,237);text(4,60,"详情左右：数值 招式 培养",INK,237);text(4,78,"形态独立记录；数据供参考",INK,237);if(EVENT_TEST_ENABLED){text(4,96,"当前为独立图鉴联调程序",MUTED,237);text(4,114,"SELECT：事件联调菜单",MUTED,237);}footer("B返回图鉴");}
static void draw_events(void){title("事件联调  非剧情奖励");text(4,25,omni_pokedex_catalog.entries[entry].name_zh,INK,238);text(4,47,"A模拟见过 R模拟捕捉",INK,238);text(4,68,"L模拟形态解锁",INK,238);text(4,89,"只读羁绊拒绝登记",MUTED,238);text(4,114,message,TEAL,238);footer("B返回；自动双槽保存");}
static void draw(void){box(0,0,240,160,PAPER);switch(screen){case LIST:draw_list();break;case DETAIL:if(page==0)draw_profile();else if(page==1)draw_moves();else if(page==2)draw_plan();else if(page==3)draw_plan_stats();else if(page==4)draw_forms();else draw_identity();break;case FILTER:draw_filter();break;case SEARCH:draw_search();break;case HELP:draw_help();break;case EVENTS:draw_events();break;}dirty=0;}
uint8_t omni_game_dex_is_open(void){return opened;}
void omni_gba_box(int x,int y,int w,int h,uint16_t c){box(x,y,w,h,c);}
void omni_gba_text(int x,int y,const char *s,uint16_t c,int end){text(x,y,s,c,end);}
void omni_gba_num(int x,int y,unsigned n,uint16_t c){num(x,y,n,c);}
void omni_gba_picture(unsigned index,int x,int y){picture(index,x,y);}
void omni_game_dex_open_entry(uint32_t id){int32_t found=omni_dex_find(&omni_pokedex_catalog,id);omni_game_dex_open();if(found>=0){entry=(uint16_t)found;screen=DETAIL;page=scroll=plan_cursor=0;move_detail=0;}}
void omni_game_dex_open(void){opened=1;screen=LIST;query();dirty=1;}
void omni_game_dex_tick(uint16_t keys){uint16_t pressed=keys&~old_keys;unsigned max;old_keys=keys;if(!opened)return;if(keys){++held_frames;if(held_frames>20&&(held_frames%5)==0)pressed|=keys&(UP|DOWN|LEFT|RIGHT);}else held_frames=0;
 if(pressed){dirty=1;
  if(screen==LIST){if(pressed&B){opened=0;return;}if((pressed&UP)&&total)cursor=cursor?cursor-1:total-1;if((pressed&DOWN)&&total)cursor=(cursor+1)%total;if((pressed&L)&&total)cursor=cursor>=36?cursor-36:0;if((pressed&R)&&total)cursor=cursor+36<total?cursor+36:total-1;if((pressed&A)&&total){entry=results[cursor];page=scroll=plan_cursor=0;screen=DETAIL;}if(pressed&SELECT)screen=FILTER;if(pressed&START)screen=HELP;}
  else if(screen==DETAIL){if(pressed&B){if(move_detail)move_detail=0;else screen=LIST;}if(pressed&RIGHT){page=(page+1)%6;scroll=0;move_detail=0;source_offset=0;}if(pressed&LEFT){page=(page+5)%6;scroll=0;move_detail=0;source_offset=0;}if(pressed&(L|R)){entry=(uint16_t)((entry+OMNI_CATALOG_ENTRY_COUNT+((pressed&R)?1:-1))%OMNI_CATALOG_ENTRY_COUNT);scroll=plan_cursor=0;}if(page==1){max=gba_info[entry].move_count;if((pressed&DOWN)&&max)scroll=(scroll+1)%max;if((pressed&UP)&&max)scroll=(scroll+max-1)%max;if((pressed&A)&&max){move_detail=!move_detail;source_offset=0;}if((pressed&SELECT)&&move_detail&&max){source_offset+=56;if(source_offset>=length(gba_move_sources[gba_info[entry].move_start+scroll]))source_offset=0;}}if(page==2||page==3){max=gba_info[entry].plan_count;if(max){if(pressed&DOWN)plan_cursor=(plan_cursor+1)%max;if(pressed&UP)plan_cursor=(plan_cursor+max-1)%max;}}if(page==4){max=form_count();if(pressed&DOWN)scroll=(scroll+1)%max;if(pressed&UP)scroll=(scroll+max-1)%max;if(pressed&A){entry=form_at(scroll);page=scroll=plan_cursor=0;}}if(EVENT_TEST_ENABLED&&(pressed&START))screen=EVENTS;}
  else if(screen==FILTER){unsigned value=0,limit=0,step=1;if(pressed&UP)filter_cursor=(filter_cursor+5)%6;if(pressed&DOWN)filter_cursor=(filter_cursor+1)%6;switch(filter_cursor){case 0:value=filter.national;limit=1025;break;case 1:value=filter.category;limit=17;break;case 2:value=filter.generation;limit=9;break;case 3:value=filter.type;limit=18;break;case 4:value=filter.progress;limit=4;break;default:value=filter.include_research;limit=1;break;}if(filter_cursor==0&&(pressed&(L|R)))step=100;if(pressed&(RIGHT|R))value=(value+step)%(limit+1);if(pressed&(LEFT|L))value=(value+limit+1-step)%(limit+1);switch(filter_cursor){case 0:filter.national=(uint16_t)value;break;case 1:filter.category=(uint8_t)value;break;case 2:filter.generation=(uint8_t)value;break;case 3:filter.type=(uint8_t)value;break;case 4:filter.progress=(uint8_t)value;break;default:filter.include_research=(uint8_t)value;break;}if(pressed&(A|B)){cursor=0;query();screen=LIST;}if(pressed&SELECT)screen=SEARCH;if(pressed&START){memset(&filter,0,sizeof(filter));filter.include_research=1;search[0]=0;}}
  else if(screen==SEARCH){static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ -<";unsigned n=length(search);if(pressed&RIGHT)search_cursor=(search_cursor+1)%29;if(pressed&LEFT)search_cursor=(search_cursor+28)%29;if(pressed&DOWN)search_cursor=(search_cursor+10)%29;if(pressed&UP)search_cursor=(search_cursor+19)%29;if(pressed&A){if(search_cursor==28){if(n)search[n-1]=0;}else if(n<24){search[n]=alphabet[search_cursor];search[n+1]=0;}}if(pressed&START){cursor=0;query();screen=LIST;}if(pressed&B)screen=FILTER;}
  else if(screen==HELP){if(pressed&B)screen=LIST;if(EVENT_TEST_ENABLED&&(pressed&SELECT)){if(total)entry=results[cursor];screen=EVENTS;}}
  else if(screen==EVENTS){int code=0;if(pressed&A)code=omni_game_dex_event(omni_pokedex_catalog.entries[entry].id,1);if(pressed&R)code=omni_game_dex_event(omni_pokedex_catalog.entries[entry].id,2);if(pressed&L)code=omni_game_dex_event(omni_pokedex_catalog.entries[entry].id,4);if(code)message=code==OMNI_GAME_DEX_SAVE_FAILED?"保存失败，请重试":"未登记：资料尚未审定";if(pressed&B){screen=LIST;query();}}
 }
 if(dirty)draw();
}
#ifdef OMNI_GBA_STANDALONE
int main(void){REG16(0x04000000)=0x0403;REG16(0x04000204)=0x4317;(void)save_signature;load_progress();omni_game_dex_open();for(;;){while(REG16(0x04000006)>=160){}while(REG16(0x04000006)<160){}if(!omni_game_dex_is_open()){box(0,0,240,160,PAPER);title("OMNI 图鉴联调");text(8,60,"按 A 打开图鉴",INK,236);footer("独立程序；游戏世界尚未接入");if((~REG16(0x04000130))&A){omni_game_dex_open();old_keys=A;}}else omni_game_dex_tick((uint16_t)(~REG16(0x04000130)&1023));}}

#endif
