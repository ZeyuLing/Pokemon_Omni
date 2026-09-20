#include <stdint.h>
#include <stddef.h>
#include "omni/adventure.h"
#include "catalog.h"
#include "world_data.h"
#include "pokedex_game.h"
#include "draw.h"

#define REG16(a) (*(volatile uint16_t*)(a))
#define REG32(a) (*(volatile uint32_t*)(a))
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))
#define INK RGB(5,7,10)
#define PAPER RGB(31,31,29)
#define BLUE RGB(7,14,24)
#define MUTED RGB(14,16,18)
#define GOLD RGB(30,24,9)
#define box(...) omni_gba_box(__VA_ARGS__)
#define text(...) omni_gba_text(__VA_ARGS__)
#define num(...) omni_gba_num(__VA_ARGS__)
enum {A=1,B=2,SELECT=4,START=8,RIGHT=16,LEFT=32,UP=64,DOWN=128,R=256,L=512};
enum {TITLE,WORLD,MENU,TEAM,BAG,TRAINER,DEX,DIALOG,CHALLENGE,STARTER,BATTLE,BATTLE_LOG,NEW_CONFIRM};
enum {AFTER_WORLD,AFTER_CHALLENGE,AFTER_MENU,AFTER_BAG};
static OmniAdventure game;
static OmniPractice battle;
static OmniPracticeTurn turn;
static uint8_t dex_flags[OMNI_CATALOG_ENTRY_COUNT],scratch_flags[OMNI_CATALOG_ENTRY_COUNT];
static OmniDexState dex_state={dex_flags,OMNI_CATALOG_ENTRY_COUNT};
static uint8_t px=6,py=6,direction,screen,menu_cursor,choice,after_dialog,has_save,dirty=1;
static uint8_t dex_wait_release;
static uint8_t moving,move_dx,move_dy,walk_phase,menu_return,log_index,practice_result;
static int anim_x,anim_y,camera_x,camera_y,origin_x,origin_y;
static uint16_t old_keys,frame_count;
static uint32_t save_seq;static int save_slot=-1;
static uint8_t save_bytes[12500];
static const char *dialogue,*next_page;
static char buffer[512];
static const char save_signature[] __attribute__((used))="SRAM_V113";
/* Passive emulator observability. No write/cheat commands are exposed. */
volatile uint32_t omni_pallet_probe[16];

void *memset(void *d,int v,size_t n){uint8_t *p=d;while(n--)*p++=(uint8_t)v;return d;}
void *memcpy(void *d,const void *s,size_t n){uint8_t *p=d;const uint8_t *q=s;while(n--)*p++=*q++;return d;}
int memcmp(const void *a,const void *b,size_t n){const uint8_t *p=a,*q=b;while(n--){if(*p!=*q)return *p-*q;++p;++q;}return 0;}
static unsigned length(const char *s){unsigned n=0;while(s[n])++n;return n;}
static void copy(char *out,const char *in){while((*out++=*in++)){};}
static void append(const char *s){unsigned n=length(buffer);while(*s&&n<sizeof(buffer)-1)buffer[n++]=*s++;buffer[n]=0;}
static uint32_t hash(const uint8_t *p,unsigned n){uint32_t h=2166136261u;while(n--)h=(h^*p++)*16777619u;return h;}
static uint32_t get32(const uint8_t *p){return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v){unsigned i;for(i=0;i<4;++i)p[i]=(uint8_t)(v>>(i*8));}
static const PalletMap *map(void){return &pallet_maps[game.location-1];}
static int actor_visible(const PalletActor *a){return !a->starter||!game.starter||(a->starter!=game.starter&&a->starter!=game.starter%3+1);}
static int actor_at(int x,int y){unsigned i;const PalletMap *m=map();for(i=m->actors;i<m->actors+m->actor_count;++i)if(pallet_actors[i].x==x&&pallet_actors[i].y==y&&actor_visible(&pallet_actors[i]))return (int)i;return -1;}
static const PalletWarp *warp_at(int x,int y){unsigned i;const PalletMap *m=map();for(i=m->warps;i<m->warps+m->warp_count;++i)if(pallet_warps[i].x==x&&pallet_warps[i].y==y)return &pallet_warps[i];return 0;}
static int position_valid(unsigned location,unsigned x,unsigned y){const PalletMap *m;if(location<1||location>5)return 0;m=&pallet_maps[location-1];return x<m->w&&y<m->h&&!pallet_world_blob[m->collision+y*m->w+x];}
static void message(const char *s,unsigned after){dialogue=s;next_page=s;after_dialog=(uint8_t)after;screen=DIALOG;dirty=1;}
static void panel(int x,int y,int w,int h){box(x,y,w,h,INK);box(x+2,y+2,w-4,h-4,RGB(20,23,27));box(x+4,y+4,w-8,h-8,PAPER);}
static void heading(const char *s){box(0,0,240,23,BLUE);text(7,3,s,PAPER,237);}
static const char *paragraph(const char *s,int x,int y,unsigned rows){unsigned row=0,w=0;char line[96];unsigned n=0;while(*s&&row<rows){unsigned bytes=1,width=8;const unsigned char c=(unsigned char)*s;if(c>=0xe0){bytes=3;width=16;}else if(c>=0xc0){bytes=2;width=16;}if(*s=='\n'||w+width>216){line[n]=0;text(x,y+(int)row*17,line,INK,234);++row;n=w=0;if(*s=='\n')++s;if(row==rows)break;continue;}while(bytes--)line[n++]=*s++;w+=width;}if(n&&row<rows){line[n]=0;text(x,y+(int)row*17,line,INK,234);}return s;}
static void text_box(const char *s){panel(2,94,236,66);next_page=paragraph(s,11,100,3);text(220,141,"A",BLUE,236);}
static void dma_row(const uint16_t *source,volatile uint16_t *dest,unsigned count){REG32(0x040000d4)=(uint32_t)(uintptr_t)source;REG32(0x040000d8)=(uint32_t)(uintptr_t)dest;REG32(0x040000dc)=0x80000000u|count;}
static void sprite(unsigned id,unsigned frame,int wx,int wy,unsigned flip){const PalletMap *m=map();const PalletSprite *s=&pallet_sprites[id];const uint16_t *pixels=(const uint16_t*)(pallet_world_blob+s->offset)+(frame%s->frames)*512;unsigned row,col;for(row=0;row<32;++row){int y=wy-16+(int)row,dy=y-camera_y+origin_y;if(dy<0||dy>=160)continue;for(col=0;col<16;++col){int x=wx+(int)col,dx=x-camera_x+origin_x;uint16_t c=pixels[row*16+(flip?15-col:col)];if(dx<0||dx>=240||(c&0x8000))continue;if(x>=0&&x<m->w*16&&y>=0&&y<m->h*16&&pallet_world_blob[m->mask+y*m->w*16+x])continue;((volatile uint16_t*)0x06000000)[dy*240+dx]=c;}}}
static unsigned face_frame(unsigned dir){return dir==0?0:dir==1?1:2;}
static void draw_world(void){
 const PalletMap *m=map();int width=m->w*16,height=m->h*16,wx=px*16+anim_x,wy=py*16+anim_y;unsigned row,i,j,ordered[20],count=0;int player_order=-1;
 camera_x=wx+8-120;camera_y=wy+8-80;if(camera_x<0)camera_x=0;if(camera_y<0)camera_y=0;if(camera_x>width-240)camera_x=width>240?width-240:0;if(camera_y>height-160)camera_y=height>160?height-160:0;
 origin_x=width<240?(240-width)/2:0;origin_y=height<160?(160-height)/2:0;
 if(origin_x||origin_y)box(0,0,240,160,RGB(3,6,8));
 for(row=0;row<(unsigned)(height<160?height:160);++row)dma_row((const uint16_t*)(pallet_world_blob+m->art)+(row+camera_y)*width+camera_x,(volatile uint16_t*)0x06000000+(row+origin_y)*240+origin_x,(unsigned)(width<240?width:240));
 for(i=m->actors;i<m->actors+m->actor_count;++i)if(actor_visible(&pallet_actors[i]))ordered[count++]=i;
 for(i=0;i<count;++i)for(j=i+1;j<count;++j)if(pallet_actors[ordered[j]].y<pallet_actors[ordered[i]].y){unsigned temp=ordered[i];ordered[i]=ordered[j];ordered[j]=temp;}
 for(i=0;i<=count;++i){if(player_order<0&&(i==count||wy<pallet_actors[ordered[i]].y*16)){unsigned frame=face_frame(direction);if(moving&&((frame_count/4)&1))frame=(direction==0?3:direction==1?5:7)+(walk_phase&1);sprite(0,frame,wx,wy,direction==3);player_order=1;}if(i<count){const PalletActor *a=&pallet_actors[ordered[i]];sprite(a->sprite,face_frame(a->direction),a->x*16,a->y*16,a->direction==3);}}
}
static unsigned dex_index(uint16_t species){unsigned i;for(i=0;i<omni_pokedex_catalog.count;++i)if(omni_pokedex_catalog.entries[i].national==species&&omni_pokedex_catalog.entries[i].category==1)return i;return 0;}
static void draw_title(void){box(0,0,240,160,RGB(5,12,17));box(0,115,240,45,RGB(7,17,17));text(34,18,"POKEMON OMNI",PAPER,237);text(53,45,"真新镇 · 启程",GOLD,237);omni_gba_picture(dex_index(1),4,62);omni_gba_picture(dex_index(4),87,62);omni_gba_picture(dex_index(7),170,62);text(72,120,has_save?(menu_cursor?"  继续冒险":"> 继续冒险"):"",PAPER,236);text(72,139,has_save?(menu_cursor?"> 新的冒险":"  新的冒险"):"> 新的冒险",PAPER,237);}
static void draw_menu(void){static const char *items[]={"图鉴","宝可梦","背包","训练家","保存","返回"};unsigned i;draw_world();panel(118,3,120,151);for(i=0;i<6;++i){if(menu_cursor==i)box(125,10+(int)i*22,105,21,RGB(25,28,29));text(129,12+(int)i*22,items[i],(i<2&&!game.starter)?MUTED:INK,234);}text(8,139,map()->name,PAPER,115);}
static void draw_team(void){unsigned i;static const char *stats[]={"HP","攻击","防御","特攻","特防","速度"};const OmniPartner *mon=&game.party[0];const OmniStarter *spec=omni_partner_species(mon->species);box(0,0,240,160,PAPER);heading("同行的伙伴");if(!spec){text(12,50,"还没有宝可梦伙伴。",INK,237);return;}omni_gba_picture(dex_index(mon->species),8,29);text(84,28,spec->name,INK,237);text(84,48,"Lv.",MUTED,124);num(112,48,mon->level,INK);text(153,48,spec->ability,BLUE,236);num(84,68,mon->hp,INK);text(111,68,"/",MUTED,128);num(123,68,omni_partner_stat(mon,0),INK);for(i=0;i<6;++i){int x=(i%3)*80,y=91+(int)(i/3)*17;text(x+4,y,stats[i],MUTED,x+40);num(x+42,y,omni_partner_stat(mon,(uint8_t)i),INK);}for(i=0;i<2;++i){text(6+(int)i*120,126,omni_practice_move_name(spec->moves[i]),INK,110+(int)i*120);num(80+(int)i*120,126,mon->pp[i],BLUE);}text(7,144,"A查看图鉴  B返回",BLUE,237);}
static void draw_bag(void){box(0,0,240,160,PAPER);heading("背包 · 道具");text(12,39,"伤药",INK,130);num(193,39,game.potions,INK);text(12,62,"恢复一只宝可梦 20 HP。",MUTED,237);text(12,91,"精灵球",INK,145);num(193,91,game.balls,INK);text(12,114,"钱：",MUTED,70);num(64,114,game.money,INK);text(12,140,"A使用伤药  B返回",BLUE,237);}
static void draw_trainer(void){box(0,0,240,160,PAPER);heading("训练家卡片");text(12,34,"赤红",INK,238);text(12,55,map()->name,BLUE,237);text(12,79,"练习战胜场",MUTED,183);num(194,79,game.battles_won,INK);text(12,101,"图鉴已捕获",MUTED,183);num(194,101,omni_dex_count(&omni_pokedex_catalog,&dex_state,OMNI_DEX_REGISTERED,0),INK);text(12,126,game.chapter<2?"目标：领取第一位伙伴":game.chapter<3?"目标：和小茂完成练习战":"真新镇开场已完成",BLUE,237);text(12,144,"B返回",MUTED,237);}
static void draw_starter(void){const OmniStarter *s=&omni_starters[choice-1];box(0,0,240,160,PAPER);heading("选择你的第一位伙伴");omni_gba_picture(dex_index(s->species),12,39);text(95,39,s->name,INK,237);text(95,62,choice==1?"草 / 毒":choice==2?"火":"水",BLUE,237);text(95,84,s->ability,MUTED,237);text(12,116,"要和这位伙伴一起出发吗？",INK,237);text(12,140,"A确认选择  B再想想",BLUE,237);}
static void hp_bar(int x,int y,const OmniPartner *m){unsigned max=omni_partner_stat(m,0),width=max?m->hp*70/max:0;box(x,y,74,7,INK);box(x+2,y+2,70,3,RGB(23,24,24));box(x+2,y+2,(int)width,3,m->hp*3<max?RGB(27,7,7):RGB(5,23,10));}
static void battle_sprite(unsigned species,int back,int x,int y){unsigned index=species==1?0:species==4?1:2,row,col;const uint16_t *p=(const uint16_t*)(pallet_world_blob+pallet_battle_sprites[index*2+back]);for(row=0;row<64;++row)for(col=0;col<64;++col)if(!(p[row*64+col]&0x8000))box(x+(int)col,y+(int)row,1,1,p[row*64+col]);}
static void draw_battle(void){unsigned i;const OmniStarter *p=omni_partner_species(battle.mons[0].species),*e=omni_partner_species(battle.mons[1].species);box(0,0,240,160,RGB(27,30,25));box(141,69,86,8,RGB(20,25,18));box(10,132,91,9,RGB(20,25,18));battle_sprite(e->species,0,159,8);battle_sprite(p->species,1,17,73);text(9,7,e->name,INK,151);text(9,27,"小茂  Lv.5",MUTED,151);hp_bar(12,49,&battle.mons[1]);text(121,78,p->name,INK,239);text(121,98,"Lv.5",MUTED,239);hp_bar(124,119,&battle.mons[0]);num(201,115,battle.mons[0].hp,INK);
 if(screen==BATTLE_LOG)text_box(dialogue);else{panel(2,132,236,28);for(i=0;i<2;++i){text(9+(int)i*118,137,omni_practice_move_name(p->moves[i]),menu_cursor==i?BLUE:MUTED,91+(int)i*118);num(84+(int)i*118,137,battle.mons[0].pp[i],menu_cursor==i?BLUE:MUTED);}if(!battle.mons[0].pp[0]&&!battle.mons[0].pp[1])text(9,137,"A：挣扎",BLUE,236);}}
static void draw(void){switch(screen){case TITLE:draw_title();break;case WORLD:draw_world();break;case MENU:draw_menu();break;case TEAM:draw_team();break;case BAG:draw_bag();break;case TRAINER:draw_trainer();break;case STARTER:draw_starter();break;case BATTLE:case BATTLE_LOG:draw_battle();break;case DIALOG:draw_world();text_box(dialogue);break;case CHALLENGE:draw_world();panel(14,93,212,66);text(26,102,"和小茂进行练习战？",INK,233);text(30,128,menu_cursor?"  是的":"> 是的",INK,118);text(140,128,menu_cursor?"> 下次":"  下次",INK,237);break;case NEW_CONFIRM:draw_title();panel(4,69,232,72);text(12,77,"新冒险会替换游戏存档。",INK,236);text(12,99,"A确认  B保留并返回",INK,236);break;default:break;}dirty=0;}

static int save_game(void){
 unsigned i,target=save_slot==0?1:0;size_t n=0,dex_n=0;uint8_t head[20];volatile uint8_t *s=(volatile uint8_t*)(uintptr_t)(0x0e000000u+target*16384u);
 memcpy(save_bytes,"OPAL",4);put32(save_bytes+4,1);save_bytes[8]=(uint8_t)game.location;save_bytes[9]=px;save_bytes[10]=py;save_bytes[11]=direction;
 if(omni_adventure_save(&game,save_bytes+16,132,&n)||omni_dex_save(&omni_pokedex_catalog,&dex_state,save_bytes+148,sizeof(save_bytes)-148,&dex_n))return 0;put32(save_bytes+12,(uint32_t)dex_n);n=148+dex_n;
 memcpy(head,"OMG1",4);put32(head+4,save_seq+1);put32(head+8,(uint32_t)n);put32(head+12,hash(save_bytes,(unsigned)n));put32(head+16,hash(head,16));s[0]=0;for(i=0;i<n;++i)s[20+i]=save_bytes[i];for(i=1;i<20;++i)s[i]=head[i];s[0]=head[0];for(i=0;i<n;++i)if(s[20+i]!=save_bytes[i])return 0;for(i=0;i<20;++i)if(s[i]!=head[i])return 0;save_slot=(int)target;++save_seq;has_save=1;return 1;
}
static int host_save(const uint8_t *bytes,size_t n,void *context){(void)bytes;(void)n;(void)context;return save_game();}
static int read_slot(unsigned slot,uint32_t *sequence,int apply){
 volatile uint8_t *s=(volatile uint8_t*)(uintptr_t)(0x0e000000u+slot*16384u);uint8_t header[20];unsigned i,n;OmniAdventure temp;OmniDexState temp_dex={scratch_flags,OMNI_CATALOG_ENTRY_COUNT};
 for(i=0;i<20;++i)header[i]=s[i];if(memcmp(header,"OMG1",4)||get32(header+16)!=hash(header,16))return 0;n=get32(header+8);if(n<164||n>sizeof(save_bytes))return 0;for(i=0;i<n;++i)save_bytes[i]=s[20+i];if(get32(header+12)!=hash(save_bytes,n)||memcmp(save_bytes,"OPAL",4)||get32(save_bytes+4)!=1||get32(save_bytes+12)!=n-148||save_bytes[11]>3)return 0;
 if(omni_adventure_load(&temp,save_bytes+16,132)||temp.location!=save_bytes[8]||!position_valid(temp.location,save_bytes[9],save_bytes[10])||omni_dex_load(&omni_pokedex_catalog,&temp_dex,save_bytes+148,n-148))return 0;
 *sequence=get32(header+4);if(apply){game=temp;memcpy(dex_flags,scratch_flags,sizeof(dex_flags));px=save_bytes[9];py=save_bytes[10];direction=save_bytes[11];}return 1;
}
static int load_game(void){uint32_t a=0,b=0;int va=read_slot(0,&a,0),vb=read_slot(1,&b,0);unsigned first=(vb&&(!va||(int32_t)(b-a)>0))?1:0;uint32_t seq;if(!va&&!vb)return 0;if(read_slot(first,&seq,1)){save_slot=(int)first;save_seq=seq;return 1;}return 0;}
static void begin_new(void){omni_adventure_new(&game);memset(dex_flags,0,sizeof(dex_flags));px=6;py=6;direction=0;moving=0;anim_x=anim_y=0;save_game();message("今天，是旅程开始的日子。\n先下楼和妈妈打个招呼，\n再去东边的大木研究所吧。",AFTER_WORLD);}
static void interact(void){
 static const int dx[]={0,0,-1,1},dy[]={1,-1,0,0};int x=px+dx[direction],y=py+dy[direction],index=actor_at(x,y);unsigned i;uint8_t talk;const PalletMap *m=map();
 if(index>=0){const PalletActor *a=&pallet_actors[index];if(a->starter){if(game.starter)message("已经拥有自己的伙伴了。\n好好照顾它吧。",AFTER_WORLD);else if(!game.chapter)message("先和大木博士打个招呼吧。",AFTER_WORLD);else{choice=a->starter;screen=STARTER;dirty=1;}return;}talk=omni_adventure_interact(&game,a->person);message(omni_adventure_dialogue(talk),talk==OMNI_TALK_RIVAL_BATTLE?AFTER_CHALLENGE:AFTER_WORLD);if(talk==OMNI_TALK_HEALED)save_game();return;}
 for(i=m->signs;i<m->signs+m->sign_count;++i)if(pallet_signs[i].x==x&&pallet_signs[i].y==y){const PalletSign *s=&pallet_signs[i];if(s->person){talk=omni_adventure_interact(&game,s->person);message(omni_adventure_dialogue(talk),AFTER_WORLD);if(talk==OMNI_TALK_PC_POTION)save_game();}else message(s->text,AFTER_WORLD);return;}
}
static void finish_step(void){const PalletWarp *w=warp_at(px,py);moving=0;anim_x=anim_y=0;++walk_phase;if(w){uint8_t from=(uint8_t)game.location;omni_adventure_enter(&game,w->dest_map);px=w->dest_x;py=w->dest_y;if(w->dest_map==OMNI_PALLET){++py;direction=0;}else if(from==OMNI_PALLET){--py;direction=1;}else{++py;direction=0;}if(!position_valid(game.location,px,py)){px=w->dest_x;py=w->dest_y;}dirty=1;}}
static void start_step(unsigned dir,unsigned run){static const int dx[]={0,0,-1,1},dy[]={1,-1,0,0};int x=px+dx[dir],y=py+dy[dir];const PalletMap *m=map();direction=(uint8_t)dir;dirty=1;if(x<0||y<0||x>=m->w||y>=m->h){message(game.starter?"通往其他地区的道路还在准备。\n现在可以在真新镇继续探索。":"独自离开镇子太危险了。\n先去研究所领取宝可梦伙伴吧。",AFTER_WORLD);return;}if(actor_at(x,y)>=0)return;if(!warp_at(x,y)&&pallet_world_blob[m->collision+y*m->w+x])return;px=(uint8_t)x;py=(uint8_t)y;anim_x=-dx[dir]*16;anim_y=-dy[dir]*16;move_dx=(uint8_t)(dx[dir]+1);move_dy=(uint8_t)(dy[dir]+1);moving=(uint8_t)(run?2:1);}
static void battle_log(unsigned index){const OmniPracticeAction *a=&turn.actions[index];buffer[0]=0;append(a->actor?"小茂的":"你的");append(omni_partner_species(battle.mons[a->actor].species)->name);append("\n使用了");append(omni_practice_move_name(a->move));append("！");if(a->critical)append("\n击中了要害！");else if(a->status==1)append(a->move==45?"\n对手的攻击降低了。":"\n对手的防御降低了。");else if(a->status==2)append("\n能力已经不能再降低了。");dialogue=buffer;screen=BATTLE_LOG;dirty=1;}
static void probe(void){omni_pallet_probe[0]=0x50414c54u;omni_pallet_probe[1]=0x4f4d4e49u;omni_pallet_probe[2]=screen;omni_pallet_probe[3]=game.location;omni_pallet_probe[4]=px;omni_pallet_probe[5]=py;omni_pallet_probe[6]=direction;omni_pallet_probe[7]=game.chapter;omni_pallet_probe[8]=game.starter;omni_pallet_probe[9]=menu_cursor;omni_pallet_probe[10]=moving;omni_pallet_probe[11]=battle.mons[0].hp;omni_pallet_probe[12]=battle.mons[1].hp;omni_pallet_probe[13]=battle.turns;omni_pallet_probe[14]=game.potions;omni_pallet_probe[15]=game.battles_played;}
static void tick(uint16_t keys){
 uint16_t pressed=keys&~old_keys;old_keys=keys;++frame_count;if(pressed&A){REG16(0x04000068)=0xa0b4;REG16(0x0400006c)=0xc6b8;}
 if(screen==DEX){if(dex_wait_release){if(keys&A)return;dex_wait_release=0;}omni_game_dex_tick(keys);if(!omni_game_dex_is_open()){screen=menu_return;dirty=1;}return;}
 if(screen==WORLD&&moving){int speed=moving==2?4:2;anim_x+=((int)move_dx-1)*speed;anim_y+=((int)move_dy-1)*speed;dirty=1;if(!anim_x&&!anim_y)finish_step();return;}
 if(screen==WORLD){if(pressed&START){screen=MENU;menu_cursor=0;dirty=1;}else if(pressed&A)interact();else if(keys&UP)start_step(1,keys&B);else if(keys&DOWN)start_step(0,keys&B);else if(keys&LEFT)start_step(2,keys&B);else if(keys&RIGHT)start_step(3,keys&B);return;}
 if(!pressed)return;dirty=1;
 switch(screen){
 case TITLE:if(has_save&&(pressed&(UP|DOWN)))menu_cursor^=1;if(pressed&(A|START)){if(has_save&&!menu_cursor){load_game();screen=WORLD;}else if(has_save)screen=NEW_CONFIRM;else begin_new();}break;
 case NEW_CONFIRM:if(pressed&A)begin_new();if(pressed&B)screen=TITLE;break;
 case DIALOG:if(pressed&(A|B)){if(*next_page)dialogue=next_page;else{screen=after_dialog==AFTER_CHALLENGE?CHALLENGE:after_dialog==AFTER_MENU?MENU:after_dialog==AFTER_BAG?BAG:WORLD;if(screen==CHALLENGE)menu_cursor=0;}}break;
 case MENU:if(pressed&UP)menu_cursor=(menu_cursor+5)%6;if(pressed&DOWN)menu_cursor=(menu_cursor+1)%6;if(pressed&(B|START))screen=WORLD;if(pressed&A){switch(menu_cursor){case 0:if(game.starter){omni_game_dex_open();omni_game_dex_tick(0);menu_return=MENU;screen=DEX;dex_wait_release=1;}else message("先在研究所领取伙伴和图鉴。",AFTER_MENU);break;case 1:screen=TEAM;break;case 2:screen=BAG;break;case 3:screen=TRAINER;break;case 4:message(save_game()?"冒险记录已保存。\n下次可以从这里继续。":"保存失败，请重试。",AFTER_MENU);break;default:screen=WORLD;break;}}break;
 case TEAM:if(pressed&B)screen=MENU;if((pressed&A)&&game.starter){unsigned i=dex_index(game.party[0].species);omni_game_dex_open_entry(omni_pokedex_catalog.entries[i].id);omni_game_dex_tick(0);menu_return=TEAM;screen=DEX;dex_wait_release=1;}break;
 case BAG:if(pressed&B)screen=MENU;if(pressed&A){int result=omni_adventure_potion(&game,0);message(!result?"使用了伤药。\n伙伴的体力恢复了。":!game.starter?"还没有可以使用道具的伙伴。":!game.potions?"背包里没有伤药了。":"现在不需要使用伤药。",AFTER_BAG);if(!result)save_game();}break;
 case TRAINER:if(pressed&B)screen=MENU;break;
 case STARTER:if(pressed&B)screen=WORLD;if(pressed&A){if(!omni_adventure_choose(&game,choice,&omni_pokedex_catalog,&dex_state)){buffer[0]=0;append("你选择了");append(omni_starters[choice-1].name);append("！\n获得图鉴和三瓶伤药。\n和小茂聊聊，试一次练习战吧。");save_game();message(buffer,AFTER_WORLD);}else message("暂时不能领取这只宝可梦。",AFTER_WORLD);}break;
 case CHALLENGE:if(pressed&(LEFT|RIGHT|UP|DOWN))menu_cursor^=1;if(pressed&B)screen=WORLD;if(pressed&A){if(menu_cursor)screen=WORLD;else if(!omni_practice_begin(&game,&battle,&omni_pokedex_catalog,&dex_state)){menu_cursor=0;screen=BATTLE;practice_result=0;}else message("伙伴需要休息。\n先回家找妈妈恢复体力吧。",AFTER_WORLD);}break;
 case BATTLE:if(pressed&(LEFT|RIGHT|UP|DOWN))menu_cursor^=1;if(pressed&A){if(!omni_practice_turn(&battle,menu_cursor,&turn)){log_index=0;battle_log(0);}else{dialogue="这个招式的 PP 用完了。\n请选择另一个招式。";screen=BATTLE_LOG;log_index=255;}}break;
 case BATTLE_LOG:if(pressed&(A|B)){if(*next_page){dialogue=next_page;break;}if(log_index==255){screen=BATTLE;break;}if(++log_index<turn.count)battle_log(log_index);else if(battle.outcome){unsigned first=game.chapter==2;practice_result=battle.outcome;omni_practice_finish(&game,&battle);save_game();buffer[0]=0;append(practice_result==1?"你赢得了练习战！":"这次没能获胜，没关系。");append("\n博士恢复了双方体力和 PP。");if(first)append("\n首次练习获得了100元。");append("\n之后可以主动找小茂再战。");message(buffer,AFTER_WORLD);}else screen=BATTLE;}break;
 default:break;
 }
}
int main(void){REG16(0x04000000)=0x0403;REG16(0x04000204)=0x4317;REG16(0x04000084)=0x80;REG16(0x04000080)=0x2277;REG16(0x04000082)=2;(void)save_signature;omni_adventure_new(&game);omni_game_dex_bind(dex_state,host_save,0);has_save=(uint8_t)load_game();screen=TITLE;for(;;){while(REG16(0x04000006)>=160){}while(REG16(0x04000006)<160){}tick((uint16_t)(~REG16(0x04000130)&1023));if(dirty&&screen!=DEX)draw();probe();}}
