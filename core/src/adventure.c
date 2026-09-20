#include "omni/adventure.h"
#include "omni/memory.h"

const OmniStarter omni_starters[7]={
 {1,{45,49,49,65,65,45},{33,45},{35,40},"妙蛙种子","茂盛"},
 {4,{39,52,43,60,50,65},{10,45},{35,40},"小火龙","猛火"},
 {7,{44,48,65,50,64,43},{33,39},{35,30},"杰尼龟","激流"},
 {25,{35,55,40,50,50,90},{84,45},{30,40},"皮卡丘","静电"},
 {16,{40,45,40,35,35,56},{33,0},{35,0},"波波","锐利目光"},
 {19,{30,56,35,25,35,72},{33,39},{35,30},"小拉达","逃跑"},
 {109,{40,65,95,60,45,35},{33,0},{35,0},"瓦斯弹","飘浮"}
};
const OmniStarter *omni_partner_species(uint16_t species){unsigned i;for(i=0;i<7;++i)if(omni_starters[i].species==species)return &omni_starters[i];return 0;}
uint16_t omni_partner_stat(const OmniPartner *m,uint8_t stat){const OmniStarter *s;if(!m||stat>5||!(s=omni_partner_species(m->species)))return 0;return (uint16_t)(((2u*s->base[stat]+31u)*m->level)/100u+(stat?5u:m->level+10u));}
static void create_mon(OmniPartner *m,unsigned choice){const OmniStarter *s=&omni_starters[choice-1];memset(m,0,sizeof(*m));m->species=s->species;m->level=5;m->experience=125;m->hp=omni_partner_stat(m,0);m->pp[0]=s->pp[0];m->pp[1]=s->pp[1];}
void omni_adventure_new(OmniAdventure *s){if(!s)return;memset(s,0,sizeof(*s));s->rng=0x50414c4cu;s->location=OMNI_BEDROOM;s->money=3000;}
int omni_adventure_enter(OmniAdventure *s,uint16_t location){if(!s||location<1||location>9)return OMNI_ADVENTURE_ARGUMENT;if(location>=6&&!s->starter)return OMNI_ADVENTURE_LOCKED;s->location=location;return OMNI_ADVENTURE_OK;}
void omni_adventure_heal(OmniAdventure *s){unsigned i;if(!s)return;for(i=0;i<s->party_count;++i){const OmniStarter *spec=omni_partner_species(s->party[i].species);s->party[i].hp=omni_partner_stat(&s->party[i],0);s->party[i].status=0;s->party[i].pp[0]=spec->pp[0];s->party[i].pp[1]=spec->pp[1];}}
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
 "大木：小智，你来迟了。\n三只宝可梦已经被领走。\n还有皮卡丘愿意认识你。\n和我身旁的它打个招呼吧。",
 "大木：带着图鉴和精灵球，\n沿北边的一号道路去常青市吧。\n先和皮卡丘慢慢熟悉起来。",
 "大木：旅程从相互理解开始。\n去看看常青市的宝可梦中心吧。",
 "妈妈：大木博士在研究所等你。\n出门向东走，就能看到研究所。\n要记得和大家打招呼哦。",
 "妈妈：你和伙伴都辛苦了。\n休息一会儿吧。\n体力和招式次数已经恢复。",
 "小茂：我已经等不及了！\n先听爷爷说明，再选伙伴吧。",
 "小茂：来试试伙伴的本领吧！\n是想再战斗一次吗？",
 "这里是真新镇。\n面对人物或告示牌按 A 交谈。\n镇子北面通往一号道路。",
 "我喜欢沿着镇子散步。\n按住 B 可以跑步。\n南边的水域暂时不能通行。",
 "奈奈美：小茂在研究所。\n愿你们能成为互相帮助的对手。\n累了就回家找妈妈休息吧。",
 "助手：START 可以打开菜单。\n获得图鉴后，捕获记录会自动登记。\n资料齐全不等于已经捕获。",
 "从自己的电脑取出了伤药！\n放进了背包。",
 "自己的电脑里已经没有物品了。\n旅行记录可以从菜单保存。"};
 return talk<sizeof(text)/sizeof(text[0])?text[talk]:text[0];
}
static int record_species(const OmniDex *dex,OmniDexState *state,uint16_t species,uint8_t flag){unsigned i;if(!dex||!state)return OMNI_ADVENTURE_ARGUMENT;for(i=0;i<dex->count;++i)if(dex->entries[i].national==species&&dex->entries[i].category==1)return omni_dex_record(dex,state,dex->entries[i].id,flag)?OMNI_ADVENTURE_ARGUMENT:OMNI_ADVENTURE_OK;return OMNI_ADVENTURE_ARGUMENT;}
int omni_adventure_choose(OmniAdventure *s,uint8_t choice,const OmniDex *dex,OmniDexState *state){if(!s||choice<1||choice>4)return OMNI_ADVENTURE_ARGUMENT;if(s->starter)return OMNI_ADVENTURE_ALREADY;if(s->location!=OMNI_LAB||s->chapter!=1)return OMNI_ADVENTURE_LOCKED;if(record_species(dex,state,omni_starters[choice-1].species,OMNI_DEX_REGISTERED))return OMNI_ADVENTURE_ARGUMENT;create_mon(&s->party[0],choice);s->starter=choice;s->party_count=1;s->chapter=2;s->potions+=3;if(choice==4)s->balls+=5;return OMNI_ADVENTURE_OK;}
int omni_adventure_potion(OmniAdventure *s,uint8_t slot){unsigned max;if(!s||slot>=s->party_count)return OMNI_ADVENTURE_ARGUMENT;max=omni_partner_stat(&s->party[slot],0);if(!s->potions||!s->party[slot].hp||s->party[slot].hp>=max)return OMNI_ADVENTURE_LOCKED;--s->potions;s->party[slot].hp=(uint16_t)(s->party[slot].hp+20>max?max:s->party[slot].hp+20);return OMNI_ADVENTURE_OK;}
static uint32_t random32(uint32_t *rng){*rng=*rng*1664525u+1013904223u;return *rng;}
static unsigned scaled(unsigned value,int stage){return stage>=0?value*(unsigned)(2+stage)/2:value*2/(unsigned)(2-stage);}
const char *omni_practice_move_name(uint16_t id){switch(id){case 84:return "电击";case 33:return "撞击";case 10:return "抓";case 45:return "叫声";case 39:return "摇尾巴";case 165:return "挣扎";default:return "—";}}
int omni_practice_begin(OmniAdventure *s,OmniPractice *b,const OmniDex *dex,OmniDexState *state){unsigned rival;if(!s||!b)return OMNI_ADVENTURE_ARGUMENT;if(s->location!=OMNI_LAB||!s->starter||!s->party[0].hp)return OMNI_ADVENTURE_LOCKED;rival=s->starter%3+1;if(record_species(dex,state,omni_starters[rival-1].species,OMNI_DEX_SEEN))return OMNI_ADVENTURE_ARGUMENT;memset(b,0,sizeof(*b));b->mons[0]=s->party[0];create_mon(&b->mons[1],rival);b->rng=s->rng;b->active=1;return OMNI_ADVENTURE_OK;}
static void action(OmniPractice *b,unsigned who,unsigned slot,OmniPracticeAction *log){
 OmniPartner *m=&b->mons[who],*target=&b->mons[who^1];const OmniStarter *spec=omni_partner_species(m->species);unsigned move=165,damage,atk,def,critical;
 memset(log,0,sizeof(*log));log->actor=(uint8_t)who;if(slot<2&&m->pp[slot]){move=spec->moves[slot];}log->move=(uint16_t)move;if(m->status&&((random32(&b->rng)>>16)%4)==0){log->miss=1;log->hp[0]=b->mons[0].hp;log->hp[1]=b->mons[1].hp;return;}
 if(slot<2&&m->pp[slot])--m->pp[slot];
 if(move==45||move==39){int8_t *stage=move==45?&b->attack[who^1]:&b->defense[who^1];if(*stage>-6){--*stage;log->status=1;}else log->status=2;}
 else{
  critical=((random32(&b->rng)>>16)%24)==0;log->critical=(uint8_t)critical;
  atk=scaled(omni_partner_stat(m,move==84?3:1),move==84||(critical&&b->attack[who]<0)?0:b->attack[who]);def=scaled(omni_partner_stat(target,move==84?4:2),move==84||(critical&&b->defense[who^1]>0)?0:b->defense[who^1]);if(!def)def=1;
  damage=((2*m->level/5+2)*(move==165?50u:40u)*atk/def)/50+2;if((move==84&&m->species==25)||(move!=84&&move!=165&&(m->species==16||m->species==19)))damage=damage*3/2;if(move==84){if(target->species==7||target->species==16)damage*=2;if(target->species==1||target->species==25)damage/=2;}if(critical)damage=damage*3/2;damage=damage*(85+(random32(&b->rng)>>16)%16)/100;if(!damage)damage=1;
  log->damage=(uint16_t)(damage>target->hp?target->hp:damage);target->hp-=log->damage;if(move==84&&target->species!=25&&!target->status&&target->hp&&((random32(&b->rng)>>16)%10)==0){target->status=1;log->status=3;}
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
 slots[0]=slot;slots[1]=enemy;speed0=omni_partner_stat(&b->mons[0],5);speed1=omni_partner_stat(&b->mons[1],5);if(b->mons[0].status)speed0/=2;if(b->mons[1].status)speed1/=2;first=speed0==speed1?(random32(&b->rng)>>16)&1u:speed0>speed1?0:1;
 memset(out,0,sizeof(*out));for(i=0;i<2;++i){unsigned who=first^i;action(b,who,slots[who],&out->actions[out->count++]);if(!b->mons[0].hp||!b->mons[1].hp){b->outcome=b->mons[0].hp?1:b->mons[1].hp?2:3;break;}}
 ++b->turns;out->outcome=b->outcome;return OMNI_ADVENTURE_OK;
}
int omni_practice_finish(OmniAdventure *s,OmniPractice *b){
 unsigned i,oldhp;if(!s||!b||!b->active||!b->outcome||!s->starter)return OMNI_ADVENTURE_LOCKED;
 if(b->kind==OMNI_BATTLE_PRACTICE&&s->location!=OMNI_LAB)return OMNI_ADVENTURE_LOCKED;
 s->party[b->party_slot]=b->mons[0];s->rng=b->rng;
 if(b->outcome<=3){if(s->battles_played<65535)++s->battles_played;if(b->outcome==1&&s->battles_won<65535)++s->battles_won;}
 if(b->kind==OMNI_BATTLE_PRACTICE){if(s->chapter==2){s->chapter=3;s->money+=100;}omni_adventure_heal(s);}
 else if(b->outcome==1){OmniPartner *m=&s->party[b->party_slot];oldhp=omni_partner_stat(m,0);m->experience+=b->mons[1].level*12;if(m->experience>1000)m->experience=1000;while(m->level<10&&m->experience>=(unsigned)(m->level+1)*(m->level+1)*(m->level+1))++m->level;m->hp+=(uint16_t)(omni_partner_stat(m,0)-oldhp);if(b->kind==OMNI_BATTLE_ROCKET&&!(s->events&OMNI_EVENT_ROCKET)){s->events|=OMNI_EVENT_ROCKET;s->money=s->money>999599?999999:s->money+400;}}
 if(b->outcome==2||b->outcome==3){for(i=0;i<s->party_count&&!s->party[i].hp;++i){}if(i==s->party_count){omni_adventure_heal(s);s->money-=s->money/10;s->location=OMNI_HOME;}}
 b->active=0;return 0;
}
static void put16(uint8_t *p,unsigned v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void put32(uint8_t *p,uint32_t v){put16(p,v);put16(p+2,v>>16);}
static unsigned get16(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static uint32_t get32(const uint8_t *p){return get16(p)|((uint32_t)get16(p+2)<<16);}
static uint32_t checksum(const uint8_t *p,unsigned n){uint32_t h=2166136261u;while(n--)h=(h^*p++)*16777619u;return h;}
static int valid(const OmniAdventure *s){
 unsigned i;if(!s||s->location<1||s->location>9||s->chapter>3||s->starter>4||s->party_count>6||s->pc_claimed>1||s->events>15||s->potions>999||s->balls>999||s->money>999999||s->battles_won>s->battles_played)return 0;
 if(!!s->starter!=(s->chapter>=2)||!!s->starter!=!!s->party_count||(!s->starter&&s->location>=6))return 0;
 if((s->events&OMNI_EVENT_ROCKET)&&!(s->events&OMNI_EVENT_CENTER))return 0;
 if((s->events&OMNI_EVENT_DELIVERED)&&!(s->events&OMNI_EVENT_PARCEL))return 0;
 for(i=0;i<s->party_count;++i){const OmniPartner *m=&s->party[i];const OmniStarter *spec=omni_partner_species(m->species);if(!spec||m->level<2||m->level>10||m->experience>1000||m->status>1||m->hp>omni_partner_stat(m,0)||m->pp[0]>spec->pp[0]||m->pp[1]>spec->pp[1]||m->pp[2]||m->pp[3])return 0;}
 return 1;
}
int omni_adventure_save(const OmniAdventure *s,uint8_t *out,size_t cap,size_t *written){unsigned i;if(!out||!written||cap<132||!valid(s))return OMNI_ADVENTURE_ARGUMENT;memset(out,0,132);memcpy(out,"OADV",4);put32(out+4,2);put32(out+8,s->rng);put16(out+12,s->location);out[14]=s->chapter;out[15]=s->starter;out[16]=s->party_count;out[17]=s->pc_claimed;put16(out+18,s->potions);put16(out+20,s->balls);put16(out+22,s->events);put32(out+24,s->money);put16(out+28,s->battles_won);put16(out+30,s->battles_played);for(i=0;i<s->party_count;++i){uint8_t *p=out+32+i*16;const OmniPartner *m=&s->party[i];put16(p,m->species);p[2]=m->level;p[3]=m->status;put16(p+4,m->hp);memcpy(p+6,m->pp,4);put32(p+10,m->experience);}put32(out+128,checksum(out,128));*written=132;return OMNI_ADVENTURE_OK;}
int omni_adventure_load(OmniAdventure *s,const uint8_t *in,size_t n){OmniAdventure copy;unsigned i,version;if(!s||!in||n!=132||memcmp(in,"OADV",4)||((version=get32(in+4))!=1&&version!=2)||get32(in+128)!=checksum(in,128))return OMNI_ADVENTURE_BAD_SAVE;memset(&copy,0,sizeof(copy));copy.rng=get32(in+8);copy.location=(uint16_t)get16(in+12);copy.chapter=in[14];copy.starter=in[15];copy.party_count=in[16];copy.pc_claimed=in[17];copy.potions=(uint16_t)get16(in+18);copy.balls=(uint16_t)get16(in+20);copy.events=version==2?(uint16_t)get16(in+22):0;copy.money=get32(in+24);copy.battles_won=(uint16_t)get16(in+28);copy.battles_played=(uint16_t)get16(in+30);for(i=0;i<copy.party_count&&i<6;++i){const uint8_t *p=in+32+i*16;copy.party[i].species=(uint16_t)get16(p);copy.party[i].level=p[2];copy.party[i].hp=(uint16_t)get16(p+4);memcpy(copy.party[i].pp,p+6,4);copy.party[i].status=version==2?p[3]:0;copy.party[i].experience=version==2?get32(p+10):125;}if(version==1&&(copy.location>5||copy.starter>3||copy.party_count>1||(copy.party_count&&(copy.party[0].level!=5||copy.party[0].species!=omni_starters[copy.starter?copy.starter-1:0].species))))return OMNI_ADVENTURE_BAD_SAVE;if(!valid(&copy))return OMNI_ADVENTURE_BAD_SAVE;*s=copy;return OMNI_ADVENTURE_OK;}

const char *omni_adventure_objective(const OmniAdventure *s){
 if(!s->starter)return "前往研究所，认识皮卡丘";
 if(!(s->events&OMNI_EVENT_CENTER))return "沿一号道路前往常青中心";
 if(!(s->events&OMNI_EVENT_ROCKET))return "保护中心，阻止火箭队";
 if(!(s->events&OMNI_EVENT_PARCEL))return "去常青商店领取博士包裹";
 if(!(s->events&OMNI_EVENT_DELIVERED))return "把包裹送回大木研究所";
 return "开场完成；常青森林待开放";
}
const char *omni_adventure_visit(OmniAdventure *s,uint8_t person){
 if(!s)return 0;
 if(person==OMNI_NURSE&&s->location==OMNI_CENTER){omni_adventure_heal(s);s->events|=OMNI_EVENT_CENTER;return (s->events&OMNI_EVENT_ROCKET)?"乔伊：伙伴都恢复精神了。\n祝你们一路平安！":"乔伊：欢迎来到宝可梦中心。\n伙伴的体力和 PP 已恢复。\n那边的人似乎盯着大家的球。";}
 if(person==OMNI_CLERK&&s->location==OMNI_MART){if(!(s->events&OMNI_EVENT_PARCEL)){s->events|=OMNI_EVENT_PARCEL;return "店员：你是真新镇的小智吧？\n请把这份包裹交给大木博士。\n包裹已经放进背包。";}return "店员：欢迎！\n精灵球 200 元，伤药 300 元。";}
 if(person==OMNI_OAK&&s->location==OMNI_LAB&&(s->events&OMNI_EVENT_PARCEL)&&!(s->events&OMNI_EVENT_DELIVERED)){s->events|=OMNI_EVENT_DELIVERED;s->balls=(uint16_t)(s->balls>994?999:s->balls+5);return "大木：谢谢你送来包裹！\n这五个精灵球送给你。\n好好记录旅途中遇见的伙伴。\n接下来查看训练家卡片，\n继续完成旅途中的目标吧。";}
 if(person==OMNI_ROUTE_GUIDE&&s->location==OMNI_ROUTE1)return "草丛里会遇见野生宝可梦。\n战斗时按 L 投出精灵球，\n按 B 尝试离开。\n队伍最多六只，请留好位置。";
 return 0;
}
int omni_adventure_buy(OmniAdventure *s,uint8_t item){uint16_t *count;unsigned cost;if(!s||item>1)return OMNI_ADVENTURE_ARGUMENT;if(s->location!=OMNI_MART)return OMNI_ADVENTURE_LOCKED;count=item?&s->potions:&s->balls;cost=item?300:200;if(*count>=999||s->money<cost)return OMNI_ADVENTURE_LOCKED;s->money-=cost;++*count;return 0;}
int omni_adventure_lead(OmniAdventure *s,uint8_t slot){OmniPartner temp;if(!s||slot>=s->party_count)return OMNI_ADVENTURE_ARGUMENT;if(!s->party[slot].hp)return OMNI_ADVENTURE_LOCKED;temp=s->party[0];s->party[0]=s->party[slot];s->party[slot]=temp;return 0;}
int omni_adventure_battle(OmniAdventure *s,OmniPractice *b,uint8_t kind,const OmniDex *dex,OmniDexState *state){
 unsigned i,enemy,level;if(!s||!b||!s->starter||kind<1||kind>2)return OMNI_ADVENTURE_ARGUMENT;
 if((kind==OMNI_BATTLE_WILD&&s->location!=OMNI_ROUTE1)||(kind==OMNI_BATTLE_ROCKET&&(s->location!=OMNI_CENTER||!(s->events&OMNI_EVENT_CENTER))))return OMNI_ADVENTURE_LOCKED;
 for(i=0;i<s->party_count&&!s->party[i].hp;++i){}if(i==s->party_count)return OMNI_ADVENTURE_LOCKED;
 enemy=kind==OMNI_BATTLE_ROCKET?7:5+((random32(&s->rng)>>16)&1);level=kind==OMNI_BATTLE_ROCKET?6:2+(random32(&s->rng)>>16)%3;
 if(record_species(dex,state,omni_starters[enemy-1].species,OMNI_DEX_SEEN))return OMNI_ADVENTURE_ARGUMENT;
 memset(b,0,sizeof(*b));b->kind=kind;b->party_slot=(uint8_t)i;b->mons[0]=s->party[i];create_mon(&b->mons[1],enemy);b->mons[1].level=(uint8_t)level;b->mons[1].experience=level*level*level;b->mons[1].hp=omni_partner_stat(&b->mons[1],0);b->rng=s->rng;b->active=1;return 0;
}
/* Early-route capture rule: transparent HP-dependent prototype, not a claim of
 * the complete cartridge capture formula. No capture of trainer-owned Pokemon. */
int omni_adventure_capture(OmniAdventure *s,OmniPractice *b,const OmniDex *dex,OmniDexState *state){
 unsigned max,chance;if(!s||!b||!b->active||b->outcome||b->kind!=OMNI_BATTLE_WILD)return OMNI_ADVENTURE_LOCKED;
 if(!s->balls||s->party_count>=6)return OMNI_ADVENTURE_LOCKED;
 --s->balls;max=omni_partner_stat(&b->mons[1],0);chance=35+(max-b->mons[1].hp)*60/max;
 if((random32(&b->rng)>>16)%100>=chance)return OMNI_ADVENTURE_ALREADY;
 if(record_species(dex,state,b->mons[1].species,OMNI_DEX_REGISTERED))return OMNI_ADVENTURE_ARGUMENT;
 s->party[s->party_count++]=b->mons[1];b->outcome=4;return 0;
}
int omni_adventure_escape(OmniAdventure *s,OmniPractice *b){(void)s;if(!b||!b->active||b->outcome||b->kind!=OMNI_BATTLE_WILD)return OMNI_ADVENTURE_LOCKED;b->outcome=5;return 0;}
int omni_adventure_switch(OmniAdventure *s,OmniPractice *b,uint8_t slot){if(!s||!b||!b->active||slot>=s->party_count||!s->party[slot].hp||slot==b->party_slot)return OMNI_ADVENTURE_LOCKED;s->party[b->party_slot]=b->mons[0];b->party_slot=slot;b->mons[0]=s->party[slot];b->attack[0]=b->defense[0]=0;b->outcome=0;return 0;}
int omni_adventure_step(OmniAdventure *s,uint8_t grass){if(!s||!s->starter||s->location!=OMNI_ROUTE1||!grass)return 0;return ((random32(&s->rng)>>16)%16)==0;}
int omni_practice_wait(OmniPractice *b,OmniPracticeTurn *out){if(!b||!out||!b->active||b->outcome)return OMNI_ADVENTURE_LOCKED;memset(out,0,sizeof(*out));action(b,1,b->mons[1].pp[0]?0:1,&out->actions[0]);out->count=1;if(!b->mons[0].hp||!b->mons[1].hp)b->outcome=b->mons[0].hp?1:b->mons[1].hp?2:3;++b->turns;out->outcome=b->outcome;return 0;}
