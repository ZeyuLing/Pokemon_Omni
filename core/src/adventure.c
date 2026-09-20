#include "omni/adventure.h"
#include "omni/memory.h"

const OmniStarter omni_starters[3]={
 {1,{45,49,49,65,65,45},{33,45},{35,40},"妙蛙种子","茂盛"},
 {4,{39,52,43,60,50,65},{10,45},{35,40},"小火龙","猛火"},
 {7,{44,48,65,50,64,43},{33,39},{35,30},"杰尼龟","激流"}
};
const OmniStarter *omni_partner_species(uint16_t species){unsigned i;for(i=0;i<3;++i)if(omni_starters[i].species==species)return &omni_starters[i];return 0;}
uint16_t omni_partner_stat(const OmniPartner *m,uint8_t stat){const OmniStarter *s;if(!m||stat>5||!(s=omni_partner_species(m->species)))return 0;return (uint16_t)(((2u*s->base[stat]+31u)*m->level)/100u+(stat?5u:m->level+10u));}
static void create_mon(OmniPartner *m,unsigned choice){const OmniStarter *s=&omni_starters[choice-1];memset(m,0,sizeof(*m));m->species=s->species;m->level=5;m->hp=omni_partner_stat(m,0);m->pp[0]=s->pp[0];m->pp[1]=s->pp[1];}
void omni_adventure_new(OmniAdventure *s){if(!s)return;memset(s,0,sizeof(*s));s->rng=0x50414c4cu;s->location=OMNI_BEDROOM;s->money=3000;}
int omni_adventure_enter(OmniAdventure *s,uint16_t location){if(!s||location<1||location>5)return OMNI_ADVENTURE_ARGUMENT;s->location=location;return OMNI_ADVENTURE_OK;}
void omni_adventure_heal(OmniAdventure *s){unsigned i;if(!s)return;for(i=0;i<s->party_count;++i){const OmniStarter *spec=omni_partner_species(s->party[i].species);s->party[i].hp=omni_partner_stat(&s->party[i],0);s->party[i].pp[0]=spec->pp[0];s->party[i].pp[1]=spec->pp[1];}}
uint8_t omni_adventure_interact(OmniAdventure *s,uint8_t person){
 static const uint8_t places[]={0,5,2,5,1,1,4,5,3};
 if(!s||person<1||person>8||s->location!=places[person])return OMNI_TALK_INVALID;
 switch(person){
 case OMNI_OAK:if(!s->chapter)s->chapter=1;return s->chapter==1?OMNI_TALK_OAK_OFFER:s->chapter==2?OMNI_TALK_OAK_PARTNER:OMNI_TALK_OAK_DONE;
 case OMNI_MOM:if(!s->party_count)return OMNI_TALK_MOM_START;omni_adventure_heal(s);return OMNI_TALK_HEALED;
 case OMNI_RIVAL:return s->starter?OMNI_TALK_RIVAL_BATTLE:OMNI_TALK_RIVAL_WAIT;
 case OMNI_NEIGHBOR:return OMNI_TALK_NEIGHBOR;
 case OMNI_WALKER:return OMNI_TALK_WALKER;
 case OMNI_DAISY:return OMNI_TALK_DAISY;
 case OMNI_AIDE:return OMNI_TALK_AIDE;
 case OMNI_PC:if(s->pc_claimed)return OMNI_TALK_PC_EMPTY;s->pc_claimed=1;++s->potions;return OMNI_TALK_PC_POTION;
 }return OMNI_TALK_INVALID;
}
const char *omni_adventure_dialogue(uint8_t talk){
 static const char *text[]={"现在无法交谈。",
 "大木：终于来了！\n桌上有三只宝可梦。\n选一位成为你的伙伴吧。",
 "大木：图鉴已经交给你了。\n和小茂进行一场练习战，\n试着了解伙伴的招式吧。",
 "大木：旅程从相互理解开始。\n真新镇的朋友会一直支持你。\n下一段旅程还在准备中。",
 "妈妈：大木博士在研究所等你。\n出门向东走，就能看到研究所。\n要记得和大家打招呼哦。",
 "妈妈：你和伙伴都辛苦了。\n休息一会儿吧。\n体力和招式次数已经恢复。",
 "小茂：我已经等不及了！\n先听爷爷说明，再选伙伴吧。",
 "小茂：来试试伙伴的本领吧！\n是想再战斗一次吗？",
 "这里是真新镇。\n面对人物或告示牌按 A，\n就能交谈或阅读。",
 "我喜欢沿着镇子散步。\n按住 B 可以跑步。\n南边的水域暂时不能通行。",
 "奈奈美：小茂在研究所。\n愿你们能成为互相帮助的对手。\n累了就回家找妈妈休息吧。",
 "助手：START 可以打开菜单。\n获得图鉴后，捕获记录会自动登记。\n资料齐全不等于已经捕获。",
 "从自己的电脑取出了伤药！\n放进了背包。",
 "自己的电脑里已经没有物品了。\n旅行记录可以从菜单保存。"};
 return talk<sizeof(text)/sizeof(text[0])?text[talk]:text[0];
}
static int record_species(const OmniDex *dex,OmniDexState *state,uint16_t species,uint8_t flag){unsigned i;if(!dex||!state)return OMNI_ADVENTURE_ARGUMENT;for(i=0;i<dex->count;++i)if(dex->entries[i].national==species&&dex->entries[i].category==1)return omni_dex_record(dex,state,dex->entries[i].id,flag)?OMNI_ADVENTURE_ARGUMENT:OMNI_ADVENTURE_OK;return OMNI_ADVENTURE_ARGUMENT;}
int omni_adventure_choose(OmniAdventure *s,uint8_t choice,const OmniDex *dex,OmniDexState *state){if(!s||choice<1||choice>3)return OMNI_ADVENTURE_ARGUMENT;if(s->starter)return OMNI_ADVENTURE_ALREADY;if(s->location!=OMNI_LAB||s->chapter!=1)return OMNI_ADVENTURE_LOCKED;if(record_species(dex,state,omni_starters[choice-1].species,OMNI_DEX_REGISTERED))return OMNI_ADVENTURE_ARGUMENT;create_mon(&s->party[0],choice);s->starter=choice;s->party_count=1;s->chapter=2;s->potions+=3;return OMNI_ADVENTURE_OK;}
int omni_adventure_potion(OmniAdventure *s,uint8_t slot){unsigned max;if(!s||slot>=s->party_count)return OMNI_ADVENTURE_ARGUMENT;max=omni_partner_stat(&s->party[slot],0);if(!s->potions||!s->party[slot].hp||s->party[slot].hp>=max)return OMNI_ADVENTURE_LOCKED;--s->potions;s->party[slot].hp=(uint16_t)(s->party[slot].hp+20>max?max:s->party[slot].hp+20);return OMNI_ADVENTURE_OK;}
static uint32_t random32(uint32_t *rng){*rng=*rng*1664525u+1013904223u;return *rng;}
static unsigned scaled(unsigned value,int stage){return stage>=0?value*(unsigned)(2+stage)/2:value*2/(unsigned)(2-stage);}
const char *omni_practice_move_name(uint16_t id){switch(id){case 33:return "撞击";case 10:return "抓";case 45:return "叫声";case 39:return "摇尾巴";case 165:return "挣扎";default:return "—";}}
int omni_practice_begin(OmniAdventure *s,OmniPractice *b,const OmniDex *dex,OmniDexState *state){unsigned rival;if(!s||!b)return OMNI_ADVENTURE_ARGUMENT;if(s->location!=OMNI_LAB||!s->starter||!s->party[0].hp)return OMNI_ADVENTURE_LOCKED;rival=s->starter%3+1;if(record_species(dex,state,omni_starters[rival-1].species,OMNI_DEX_SEEN))return OMNI_ADVENTURE_ARGUMENT;memset(b,0,sizeof(*b));b->mons[0]=s->party[0];create_mon(&b->mons[1],rival);b->rng=s->rng;b->active=1;return OMNI_ADVENTURE_OK;}
static void action(OmniPractice *b,unsigned who,unsigned slot,OmniPracticeAction *log){
 OmniPartner *m=&b->mons[who],*target=&b->mons[who^1];const OmniStarter *spec=omni_partner_species(m->species);unsigned move=165,damage,atk,def,critical;
 memset(log,0,sizeof(*log));log->actor=(uint8_t)who;if(slot<2&&m->pp[slot]){move=spec->moves[slot];--m->pp[slot];}log->move=(uint16_t)move;
 if(move==45||move==39){int8_t *stage=move==45?&b->attack[who^1]:&b->defense[who^1];if(*stage>-6){--*stage;log->status=1;}else log->status=2;}
 else{
  critical=((random32(&b->rng)>>16)%24)==0;log->critical=(uint8_t)critical;
  atk=scaled(omni_partner_stat(m,1),critical&&b->attack[who]<0?0:b->attack[who]);def=scaled(omni_partner_stat(target,2),critical&&b->defense[who^1]>0?0:b->defense[who^1]);if(!def)def=1;
  damage=((2*m->level/5+2)*(move==165?50u:40u)*atk/def)/50+2;if(critical)damage=damage*3/2;damage=damage*(85+(random32(&b->rng)>>16)%16)/100;if(!damage)damage=1;
  log->damage=(uint16_t)(damage>target->hp?target->hp:damage);target->hp-=log->damage;
  if(move==165){unsigned recoil=omni_partner_stat(m,0)/4;if(!recoil)recoil=1;m->hp=(uint16_t)(m->hp>recoil?m->hp-recoil:0);}
 }
 log->hp[0]=b->mons[0].hp;log->hp[1]=b->mons[1].hp;
}
int omni_practice_turn(OmniPractice *b,uint8_t slot,OmniPracticeTurn *out){
 unsigned enemy,first,i,slots[2],speed0,speed1;
 if(!b||!out||!b->active||b->outcome)return OMNI_ADVENTURE_ARGUMENT;
 if(slot>1)return OMNI_ADVENTURE_ARGUMENT;if(!b->mons[0].pp[slot]&&(b->mons[0].pp[0]||b->mons[0].pp[1]))return OMNI_ADVENTURE_LOCKED;
 /* Only public stages/HP and the rival's own PP inform this small policy. */
 enemy=(b->turns<2&&b->mons[1].pp[1]&&b->attack[0]>-2&&((random32(&b->rng)>>16)%3==0))?1:0;if(!b->mons[1].pp[enemy])enemy^=1;
 slots[0]=slot;slots[1]=enemy;speed0=omni_partner_stat(&b->mons[0],5);speed1=omni_partner_stat(&b->mons[1],5);first=speed0==speed1?(random32(&b->rng)>>16)&1u:speed0>speed1?0:1;
 memset(out,0,sizeof(*out));for(i=0;i<2;++i){unsigned who=first^i;action(b,who,slots[who],&out->actions[out->count++]);if(!b->mons[0].hp||!b->mons[1].hp){b->outcome=b->mons[0].hp?1:b->mons[1].hp?2:3;break;}}
 ++b->turns;out->outcome=b->outcome;return OMNI_ADVENTURE_OK;
}
int omni_practice_finish(OmniAdventure *s,OmniPractice *b){if(!s||!b||!b->active||!b->outcome||s->location!=OMNI_LAB||!s->starter)return OMNI_ADVENTURE_LOCKED;s->party[0]=b->mons[0];s->rng=b->rng;if(s->battles_played<65535)++s->battles_played;if(b->outcome==1&&s->battles_won<65535)++s->battles_won;if(s->chapter==2){s->chapter=3;s->money+=100;}b->active=0;omni_adventure_heal(s);return OMNI_ADVENTURE_OK;}
static void put16(uint8_t *p,unsigned v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void put32(uint8_t *p,uint32_t v){put16(p,v);put16(p+2,v>>16);}
static unsigned get16(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static uint32_t get32(const uint8_t *p){return get16(p)|((uint32_t)get16(p+2)<<16);}
static uint32_t checksum(const uint8_t *p,unsigned n){uint32_t h=2166136261u;while(n--)h=(h^*p++)*16777619u;return h;}
static int valid(const OmniAdventure *s){unsigned i;if(!s||s->location<1||s->location>5||s->chapter>3||s->starter>3||s->party_count>1||s->pc_claimed>1||s->potions>999||s->balls>999||s->money>999999||s->battles_won>s->battles_played)return 0;if(!!s->starter!=(s->chapter>=2)||!!s->starter!=!!s->party_count)return 0;for(i=0;i<s->party_count;++i){const OmniPartner *m=&s->party[i];const OmniStarter *spec=omni_partner_species(m->species);if(!spec||m->species!=omni_starters[s->starter-1].species||m->level!=5||m->hp>omni_partner_stat(m,0)||m->pp[0]>spec->pp[0]||m->pp[1]>spec->pp[1]||m->pp[2]||m->pp[3])return 0;}return 1;}
int omni_adventure_save(const OmniAdventure *s,uint8_t *out,size_t cap,size_t *written){unsigned i;if(!out||!written||cap<132||!valid(s))return OMNI_ADVENTURE_ARGUMENT;memset(out,0,132);memcpy(out,"OADV",4);put32(out+4,1);put32(out+8,s->rng);put16(out+12,s->location);out[14]=s->chapter;out[15]=s->starter;out[16]=s->party_count;out[17]=s->pc_claimed;put16(out+18,s->potions);put16(out+20,s->balls);put32(out+24,s->money);put16(out+28,s->battles_won);put16(out+30,s->battles_played);for(i=0;i<s->party_count;++i){uint8_t *p=out+32+i*16;const OmniPartner *m=&s->party[i];put16(p,m->species);p[2]=m->level;put16(p+4,m->hp);memcpy(p+6,m->pp,4);}put32(out+128,checksum(out,128));*written=132;return OMNI_ADVENTURE_OK;}
int omni_adventure_load(OmniAdventure *s,const uint8_t *in,size_t n){OmniAdventure copy;unsigned i;if(!s||!in||n!=132||memcmp(in,"OADV",4)||get32(in+4)!=1||get32(in+128)!=checksum(in,128))return OMNI_ADVENTURE_BAD_SAVE;memset(&copy,0,sizeof(copy));copy.rng=get32(in+8);copy.location=(uint16_t)get16(in+12);copy.chapter=in[14];copy.starter=in[15];copy.party_count=in[16];copy.pc_claimed=in[17];copy.potions=(uint16_t)get16(in+18);copy.balls=(uint16_t)get16(in+20);copy.money=get32(in+24);copy.battles_won=(uint16_t)get16(in+28);copy.battles_played=(uint16_t)get16(in+30);for(i=0;i<6;++i){const uint8_t *p=in+32+i*16;copy.party[i].species=(uint16_t)get16(p);copy.party[i].level=p[2];copy.party[i].hp=(uint16_t)get16(p+4);memcpy(copy.party[i].pp,p+6,4);}if(!valid(&copy))return OMNI_ADVENTURE_BAD_SAVE;*s=copy;return OMNI_ADVENTURE_OK;}
