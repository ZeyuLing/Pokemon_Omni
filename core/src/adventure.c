#include "omni/adventure.h"
#include "omni/memory.h"

const OmniStarter omni_starters[OMNI_PARTNER_SPECIES_COUNT]={
 {1,{45,49,49,65,65,45},{33,45},{35,40},"妙蛙种子","茂盛"},
 {4,{39,52,43,60,50,65},{10,45},{35,40},"小火龙","猛火"},
 {7,{44,48,65,50,64,43},{33,39},{35,30},"杰尼龟","激流"},
 {25,{35,55,40,50,50,90},{84,45},{30,40},"皮卡丘","静电"},
 {16,{40,45,40,35,35,56},{33,0},{35,0},"波波","锐利目光"},
 {19,{30,56,35,25,35,72},{33,39},{35,30},"小拉达","逃跑"},
 {109,{40,65,95,60,45,35},{33,0},{35,0},"瓦斯弹","飘浮"},
 {13,{40,35,30,20,20,50},{40,81},{35,40},"独角虫","鳞粉"},
 {111,{80,85,95,30,30,25},{33,39},{35,30},"独角犀牛","坚硬脑袋"},
 {59,{90,110,80,100,80,95},{33,45},{35,40},"风速狗","威吓"},
 {128,{75,100,95,40,70,110},{33,39},{35,30},"肯泰罗","威吓"},
 {131,{130,85,80,85,95,60},{33,45},{35,40},"拉普拉斯","储水"}
};
static const OmniStarter travel_reference_partners[]={
#include "../../content/travel/generated/partners.inc"
};
const OmniStarter *omni_partner_species(uint16_t species){unsigned i;for(i=0;i<OMNI_PARTNER_SPECIES_COUNT;++i)if(omni_starters[i].species==species)return &omni_starters[i];for(i=0;i<sizeof(travel_reference_partners)/sizeof(travel_reference_partners[0]);++i)if(travel_reference_partners[i].species==species)return &travel_reference_partners[i];return 0;}
static const uint16_t partner_base[6]={45,80,50,75,60,120};
static const uint8_t nature_stats[5]={1,2,5,3,4};
const char *omni_nature_name(unsigned n){static const char *names[]={"勤奋","怕寂寞","勇敢","固执","顽皮","大胆","坦率","悠闲","淘气","乐天","胆小","急躁","认真","爽朗","天真","内敛","慢吞吞","冷静","害羞","马虎","温和","温顺","自大","慎重","浮躁"};return n<25?names[n]:"未知";}
const char *omni_partner_name(const OmniPartner *m){const OmniStarter *s=m?omni_partner_species(m->species):0;return !s?"未知":m->form?"搭档皮卡丘":s->name;}
const char *omni_partner_ability(const OmniPartner *m){if(m->ability==1){if(m->species==16)return "蹒跚";if(m->species==19)return "毅力";}return omni_partner_species(m->species)->ability;}
unsigned omni_move_pp(unsigned move){switch(move){case 33:case 10:case 40:return 35;case 45:case 81:return 40;case 39:case 84:return 30;case 729:return 15;default:return 0;}}
uint16_t omni_partner_stat(const OmniPartner *m,uint8_t stat){const OmniStarter *s;unsigned base,v,up,down;if(!m||stat>5||!(s=omni_partner_species(m->species)))return 0;base=m->form?partner_base[stat]:s->base[stat];v=((2u*base+m->ivs[stat]+m->evs[stat]/4)*m->level)/100u+(stat?5u:m->level+10u);if(stat&&m->nature<25){up=nature_stats[m->nature/5];down=nature_stats[m->nature%5];if(up!=down){if(stat==up)v=v*110/100;if(stat==down)v=v*90/100;}}return (uint16_t)v;}
static void create_mon(OmniPartner *m,unsigned choice){const OmniStarter *s=&omni_starters[choice-1];unsigned i;memset(m,0,sizeof(*m));m->species=s->species;m->level=5;m->experience=125;for(i=0;i<6;++i)m->ivs[i]=31;for(i=0;i<4;++i){m->moves[i]=s->moves[i];m->pp[i]=s->pp[i];}m->hp=omni_partner_stat(m,0);}
void omni_adventure_new(OmniAdventure *s){if(!s)return;memset(s,0,sizeof(*s));s->rng=0x50414c4cu;s->location=OMNI_BEDROOM;s->money=3000;}
int omni_adventure_enter(OmniAdventure *s,uint16_t location){if(!s||location<1||location>10)return OMNI_ADVENTURE_ARGUMENT;if(location>=6&&location<=9&&(!s->starter||((s->events&OMNI_EVENT_INITIALIZATION)&&!(s->events&OMNI_EVENT_GARY_DONE))))return OMNI_ADVENTURE_LOCKED;s->location=location;return OMNI_ADVENTURE_OK;}
void omni_adventure_heal(OmniAdventure *s){unsigned i;if(!s)return;for(i=0;i<s->party_count;++i){unsigned k;s->party[i].hp=omni_partner_stat(&s->party[i],0);s->party[i].status=0;for(k=0;k<4;++k)s->party[i].pp[k]=(uint8_t)omni_move_pp(s->party[i].moves[k]);}}
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
 "小茂已经出发，暂时不在研究所。",
 "小茂：来试试伙伴的本领吧！\n是想再战斗一次吗？",
 "这里是真新镇。\n面对人物或告示牌按 A 交谈。\n镇子北面通往一号道路。",
 "我喜欢沿着镇子散步。\n按住 B 可以跑步。\n南边的水域暂时不能通行。",
 "奈奈美：小茂已经出发三天了。\n希望你们能相互照顾。\n累了就回来休息吧。",
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
const char *omni_practice_move_name(uint16_t id){switch(id){case 84:return "电击";case 33:return "撞击";case 10:return "抓";case 45:return "叫声";case 39:return "摇尾巴";case 165:return "挣扎";case 40:return "毒针";case 81:return "吐丝";case 729:return "电电加速";default:return "—";}}
int omni_practice_begin(OmniAdventure *s,OmniPractice *b,const OmniDex *dex,OmniDexState *state){unsigned rival;if(!s||!b)return OMNI_ADVENTURE_ARGUMENT;if(s->location!=OMNI_LAB||!s->starter||!s->party[0].hp)return OMNI_ADVENTURE_LOCKED;rival=s->starter%3+1;if(record_species(dex,state,omni_starters[rival-1].species,OMNI_DEX_SEEN))return OMNI_ADVENTURE_ARGUMENT;memset(b,0,sizeof(*b));b->mons[0]=s->party[0];create_mon(&b->mons[1],rival);b->rng=s->rng;b->active=1;return OMNI_ADVENTURE_OK;}
static void action(OmniPractice *b,unsigned who,unsigned slot,OmniPracticeAction *log){
 OmniPartner *m=&b->mons[who],*target=&b->mons[who^1];unsigned move=165,damage,atk,def,critical;
 memset(log,0,sizeof(*log));log->actor=(uint8_t)who;if(slot<4&&m->pp[slot]){move=m->moves[slot];}log->move=(uint16_t)move;if(m->status&&((random32(&b->rng)>>16)%4)==0){log->miss=1;log->hp[0]=b->mons[0].hp;log->hp[1]=b->mons[1].hp;return;}
 if(slot<4&&m->pp[slot])--m->pp[slot];
 if(move==81){if(b->speed[who^1]>-6){--b->speed[who^1];log->status=4;}else log->status=2;}
 else if(move==45||move==39){int8_t *stage=move==45?&b->attack[who^1]:&b->defense[who^1];if(*stage>-6){--*stage;log->status=1;}else log->status=2;}
 else{
  critical=move==729||((random32(&b->rng)>>16)%24)==0;log->critical=(uint8_t)critical;
  atk=scaled(omni_partner_stat(m,move==84?3:1),move==84||(critical&&b->attack[who]<0)?0:b->attack[who]);def=scaled(omni_partner_stat(target,move==84?4:2),move==84||(critical&&b->defense[who^1]>0)?0:b->defense[who^1]);if(!def)def=1;
  damage=((2*m->level/5+2)*(move==165||move==729?50u:move==40?15u:40u)*atk/def)/50+2;if(((move==84||move==729)&&m->species==25)||(move!=84&&move!=165&&(m->species==16||m->species==19)))damage=damage*3/2;if(move==84||move==729){if(target->species==7||target->species==16)damage*=2;if(target->species==1||target->species==25)damage/=2;}if(critical)damage=damage*3/2;damage=damage*(85+(random32(&b->rng)>>16)%16)/100;if(!damage)damage=1;
  log->damage=(uint16_t)(damage>target->hp?target->hp:damage);target->hp-=log->damage;if(move==84&&target->species!=25&&!target->status&&target->hp&&((random32(&b->rng)>>16)%10)==0){target->status=1;log->status=3;}
  if(move==165){unsigned recoil=omni_partner_stat(m,0)/4;if(!recoil)recoil=1;m->hp=(uint16_t)(m->hp>recoil?m->hp-recoil:0);}
 }
 log->hp[0]=b->mons[0].hp;log->hp[1]=b->mons[1].hp;
}
int omni_practice_turn(OmniPractice *b,uint8_t slot,OmniPracticeTurn *out){
 unsigned enemy,first,i,slots[2],speed0,speed1;
 if(!b||!out||!b->active||b->outcome)return OMNI_ADVENTURE_ARGUMENT;
 if(slot>3)return OMNI_ADVENTURE_ARGUMENT;if(!b->mons[0].pp[slot]&&(b->mons[0].pp[0]||b->mons[0].pp[1]||b->mons[0].pp[2]||b->mons[0].pp[3]))return OMNI_ADVENTURE_LOCKED;
 /* Only public stages/HP and the rival's own PP inform this small policy. */
 enemy=(b->turns<2&&b->mons[1].pp[1]&&b->attack[0]>-2&&((random32(&b->rng)>>16)%3==0))?1:0;if(!b->mons[1].pp[enemy])enemy^=1;
 slots[0]=slot;slots[1]=enemy;speed0=scaled(omni_partner_stat(&b->mons[0],5),b->speed[0]);speed1=scaled(omni_partner_stat(&b->mons[1],5),b->speed[1]);if(b->mons[0].status)speed0/=2;if(b->mons[1].status)speed1/=2;first=speed0==speed1?(random32(&b->rng)>>16)&1u:speed0>speed1?0:1;
 if(b->mons[0].moves[slot]==729&&b->mons[0].pp[slot])first=0;
 memset(out,0,sizeof(*out));for(i=0;i<2;++i){unsigned who=first^i;action(b,who,slots[who],&out->actions[out->count++]);if(!b->mons[0].hp||!b->mons[1].hp){b->outcome=b->mons[0].hp?1:b->mons[1].hp?2:3;break;}}
 ++b->turns;out->outcome=b->outcome;return OMNI_ADVENTURE_OK;
}
int omni_practice_finish(OmniAdventure *s,OmniPractice *b){
 unsigned i,oldhp;if(!s||!b||!b->active||!b->outcome||!s->starter)return OMNI_ADVENTURE_LOCKED;
 if(b->outcome==1&&b->opponent_slot+1<b->opponent_count)return OMNI_ADVENTURE_LOCKED;
 if((b->kind==OMNI_BATTLE_PRACTICE||b->kind==OMNI_BATTLE_GARY)&&s->location!=OMNI_LAB)return OMNI_ADVENTURE_LOCKED;
 s->party[b->party_slot]=b->mons[0];s->rng=b->rng;
 if(b->outcome<=3){if(s->battles_played<65535)++s->battles_played;if(b->outcome==1&&s->battles_won<65535)++s->battles_won;}
 if(b->kind==OMNI_BATTLE_GARY){s->events|=OMNI_EVENT_GARY_DONE;s->chapter=3;omni_adventure_heal(s);}
 else if(b->kind==OMNI_BATTLE_OLD_MAN){if(b->outcome==1)s->events|=OMNI_EVENT_OLD_DONE|OMNI_EVENT_WEEDLE_PENDING;omni_adventure_heal(s);}
 else if(b->kind==OMNI_BATTLE_TUTORIAL){s->events|=OMNI_EVENT_OLD_DONE|OMNI_EVENT_WEEDLE_PENDING;}
 else if(b->kind==OMNI_BATTLE_PRACTICE){if(s->chapter==2){s->chapter=3;s->money+=100;}omni_adventure_heal(s);}
 else if(b->outcome==1){OmniPartner *m=&s->party[b->party_slot];oldhp=omni_partner_stat(m,0);m->experience+=b->mons[1].level*12;if(m->experience>1000)m->experience=1000;while(m->level<10&&m->experience>=(unsigned)(m->level+1)*(m->level+1)*(m->level+1))++m->level;m->hp+=(uint16_t)(omni_partner_stat(m,0)-oldhp);if(b->kind==OMNI_BATTLE_ROCKET&&!(s->events&OMNI_EVENT_ROCKET)){s->events|=OMNI_EVENT_ROCKET;s->money=s->money>999599?999999:s->money+400;}}
 if(b->kind!=OMNI_BATTLE_GARY&&b->kind!=OMNI_BATTLE_OLD_MAN&&(b->outcome==2||b->outcome==3)){for(i=0;i<s->party_count&&!s->party[i].hp;++i){}if(i==s->party_count){omni_adventure_heal(s);s->money-=s->money/10;s->location=OMNI_HOME;}}
 b->active=0;return 0;
}
static void put16(uint8_t *p,unsigned v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void put32(uint8_t *p,uint32_t v){put16(p,v);put16(p+2,v>>16);}
static unsigned get16(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static uint32_t get32(const uint8_t *p){return get16(p)|((uint32_t)get16(p+2)<<16);}
static uint32_t checksum(const uint8_t *p,unsigned n){uint32_t h=2166136261u;while(n--)h=(h^*p++)*16777619u;return h;}
static int valid_mon(const OmniPartner *m){unsigned i,total=0;const OmniStarter *spec=omni_partner_species(m->species);if(!spec||m->level<2||m->level>10||m->experience>1000||m->status>1||m->nature>24||m->ability>1||(m->ability&&m->species!=16&&m->species!=19)||m->form>1||m->bond_eligible>1||(m->form&&m->species!=25)||(m->bond_eligible&&!m->form))return 0;for(i=0;i<6;++i){if(m->ivs[i]>31||m->evs[i]>252)return 0;total+=m->evs[i];}if(total>510||m->hp>omni_partner_stat(m,0))return 0;for(i=0;i<4;++i){unsigned move=m->moves[i];if(m->pp[i]>omni_move_pp(move)||(move&&move!=spec->moves[0]&&move!=spec->moves[1]&&!(m->form&&move==729)))return 0;}return 1;}
static int valid(const OmniAdventure *s){unsigned i;if(!s||s->location<1||s->location>10||s->chapter>3||s->starter>4||s->party_count>6||s->companion>s->party_count||s->mount>s->party_count||(s->mount&&s->mount==s->companion)||s->storage_count>12||s->pc_claimed>1||s->events>2047||s->potions>999||s->balls>999||s->money>999999||s->battles_won>s->battles_played||s->badges>8||s->play_seconds>3599999)return 0;
 if(!!s->starter!=(s->chapter>=2)||!!s->starter!=!!s->party_count||(!s->starter&&s->location>=6&&s->location<=9))return 0;
 if((s->events&OMNI_EVENT_ROCKET)&&!(s->events&OMNI_EVENT_CENTER))return 0;
 if((s->events&OMNI_EVENT_DELIVERED)&&!(s->events&OMNI_EVENT_PARCEL))return 0;
 if((s->events&OMNI_EVENT_GIFTS)&&(!s->starter||!(s->events&OMNI_EVENT_INITIALIZATION)))return 0;
 for(i=0;i<s->party_count;++i)if(!valid_mon(&s->party[i]))return 0;
 for(i=0;i<s->storage_count;++i)if(!valid_mon(&s->storage[i]))return 0;return 1;
}
static void save_mon(const OmniPartner *m,uint8_t *p,uint8_t *e){unsigned i;put16(p,m->species);p[2]=m->level;p[3]=m->status;put16(p+4,m->hp);memcpy(p+6,m->pp,4);put32(p+10,m->experience);for(i=0;i<4;++i)put16(e+i*2,m->moves[i]);for(i=0;i<6;++i){e[8+i]=m->ivs[i];put16(e+14+i*2,m->evs[i]);}e[26]=m->nature;e[27]=m->ability;e[28]=m->form;e[29]=m->bond_eligible;}
static void load_mon(OmniPartner *m,const uint8_t *p,const uint8_t *e,unsigned version){unsigned i;const OmniStarter *spec;m->species=(uint16_t)get16(p);m->level=p[2];m->status=version>=2?p[3]:0;m->hp=(uint16_t)get16(p+4);memcpy(m->pp,p+6,4);m->experience=version>=2?get32(p+10):125;spec=omni_partner_species(m->species);for(i=0;i<6;++i)m->ivs[i]=31;if(spec)for(i=0;i<4;++i)m->moves[i]=spec->moves[i];if(e){for(i=0;i<4;++i)m->moves[i]=(uint16_t)get16(e+i*2);for(i=0;i<6;++i){m->ivs[i]=e[8+i];m->evs[i]=(uint16_t)get16(e+14+i*2);}m->nature=e[26];m->ability=e[27];m->form=e[28];m->bond_eligible=e[29];}}
int omni_adventure_save(const OmniAdventure *s,uint8_t *out,size_t cap,size_t *written){unsigned i;if(!out||!written||cap<OMNI_ADVENTURE_SAVE_BYTES||!valid(s))return OMNI_ADVENTURE_ARGUMENT;memset(out,0,OMNI_ADVENTURE_SAVE_BYTES);memcpy(out,"OADV",4);put32(out+4,6);put32(out+8,s->rng);put16(out+12,s->location);out[14]=s->chapter;out[15]=s->starter;out[16]=s->party_count;out[17]=s->pc_claimed;put16(out+18,s->potions);put16(out+20,s->balls);put16(out+22,s->events);put32(out+24,s->money);put16(out+28,s->battles_won);put16(out+30,s->battles_played);for(i=0;i<s->party_count;++i)save_mon(&s->party[i],out+32+i*16,out+140+i*32);put32(out+128,s->play_seconds);out[132]=s->badges;out[133]=s->companion;out[134]=s->mount;out[332]=s->storage_count;for(i=0;i<s->storage_count;++i)save_mon(&s->storage[i],out+336+i*48,out+352+i*48);put32(out+912,checksum(out,912));*written=OMNI_ADVENTURE_SAVE_BYTES;return 0;}
int omni_adventure_load(OmniAdventure *s,const uint8_t *in,size_t n){OmniAdventure copy;unsigned i,version;if(!s||!in||(n!=132&&n!=140&&n!=OMNI_ADVENTURE_SAVE_BYTES)||memcmp(in,"OADV",4))return OMNI_ADVENTURE_BAD_SAVE;version=get32(in+4);if(version<1||version>6||n!=(version<3?132:version==3?140:OMNI_ADVENTURE_SAVE_BYTES)||get32(in+n-4)!=checksum(in,(unsigned)n-4))return OMNI_ADVENTURE_BAD_SAVE;memset(&copy,0,sizeof(copy));copy.rng=get32(in+8);if(version>=3){copy.play_seconds=get32(in+128);copy.badges=in[132];if(version>=5)copy.companion=in[133];if(version>=6)copy.mount=in[134];}copy.location=(uint16_t)get16(in+12);copy.chapter=in[14];copy.starter=in[15];copy.party_count=in[16];copy.pc_claimed=in[17];copy.potions=(uint16_t)get16(in+18);copy.balls=(uint16_t)get16(in+20);copy.events=version>=2?(uint16_t)get16(in+22):0;copy.money=get32(in+24);copy.battles_won=(uint16_t)get16(in+28);copy.battles_played=(uint16_t)get16(in+30);for(i=0;i<copy.party_count&&i<6;++i)load_mon(&copy.party[i],in+32+i*16,version>=4?in+140+i*32:0,version);if(version>=4){copy.storage_count=in[332];for(i=0;i<copy.storage_count&&i<12;++i)load_mon(&copy.storage[i],in+336+i*48,in+352+i*48,4);}if(version==1&&(copy.location>5||copy.starter>3||copy.party_count>1||(copy.party_count&&(copy.party[0].level!=5||copy.party[0].species!=omni_starters[copy.starter?copy.starter-1:0].species))))return OMNI_ADVENTURE_BAD_SAVE;if(!valid(&copy))return OMNI_ADVENTURE_BAD_SAVE;*s=copy;return 0;}

const char *omni_adventure_objective(const OmniAdventure *s){
 if(!s->starter)return "前往研究所，认识皮卡丘";
 if((s->events&OMNI_EVENT_INITIALIZATION)&&!(s->events&OMNI_EVENT_GARY_DONE))return "完成研究所的小茂对战";
 if((s->events&OMNI_EVENT_INITIALIZATION)&&!(s->events&OMNI_EVENT_OLD_DONE))return "拜访常青市北面的捕捉老人";
 if(!(s->events&OMNI_EVENT_CENTER))return "沿一号道路前往常青中心";
 if(!(s->events&OMNI_EVENT_INITIALIZATION)&&!(s->events&OMNI_EVENT_ROCKET))return "保护中心，阻止火箭队";
 if(!(s->events&OMNI_EVENT_PARCEL))return "去常青商店领取博士包裹";
 if(!(s->events&OMNI_EVENT_DELIVERED))return "把包裹送回大木研究所";
 return "开场完成，常青森林待开放";
}
const char *omni_adventure_visit(OmniAdventure *s,uint8_t person){
 if(!s)return 0;
 if(person==OMNI_NURSE&&s->location==OMNI_CENTER){omni_adventure_heal(s);s->events|=OMNI_EVENT_CENTER;return (s->events&(OMNI_EVENT_INITIALIZATION|OMNI_EVENT_ROCKET))?"乔伊：伙伴都恢复精神了。\n祝你们一路平安！":"乔伊：欢迎来到宝可梦中心。\n伙伴的体力和 PP 已恢复。\n那边的人似乎盯着大家的球。";}
 if(person==OMNI_CLERK&&s->location==OMNI_MART){if(!(s->events&OMNI_EVENT_PARCEL)){s->events|=OMNI_EVENT_PARCEL;return "店员：你是真新镇的小智吧？\n请把这份包裹交给大木博士。\n包裹已经放进背包。";}return "店员：欢迎！\n精灵球 200 元，伤药 300 元。";}
 if(person==OMNI_OAK&&s->location==OMNI_LAB&&(s->events&OMNI_EVENT_PARCEL)&&!(s->events&OMNI_EVENT_DELIVERED)){s->events|=OMNI_EVENT_DELIVERED;s->balls=(uint16_t)(s->balls>994?999:s->balls+5);return "大木：谢谢你送来包裹！\n这五个精灵球送给你。\n好好记录旅途中遇见的伙伴。\n接下来查看训练家卡片，\n继续完成旅途中的目标吧。";}
 if(person==OMNI_ROUTE_GUIDE&&s->location==OMNI_ROUTE1)return "草丛里会遇见野生宝可梦。\n战斗时按 R 投出精灵球，\n按 B 尝试离开。\n队伍最多六只，请留好位置。";
 return 0;
}
int omni_adventure_buy(OmniAdventure *s,uint8_t item){uint16_t *count;unsigned cost;if(!s||item>1)return OMNI_ADVENTURE_ARGUMENT;if(s->location!=OMNI_MART)return OMNI_ADVENTURE_LOCKED;count=item?&s->potions:&s->balls;cost=item?300:200;if(*count>=999||s->money<cost)return OMNI_ADVENTURE_LOCKED;s->money-=cost;++*count;return 0;}
int omni_adventure_swap(OmniAdventure *s,uint8_t first,uint8_t second){OmniPartner temp;uint8_t a=(uint8_t)(first+1),b=(uint8_t)(second+1);if(!s||first>=s->party_count||second>=s->party_count)return OMNI_ADVENTURE_ARGUMENT;if(s->companion==a)s->companion=b;else if(s->companion==b)s->companion=a;if(s->mount==a)s->mount=b;else if(s->mount==b)s->mount=a;temp=s->party[first];s->party[first]=s->party[second];s->party[second]=temp;return 0;}
int omni_adventure_lead(OmniAdventure *s,uint8_t slot){if(!s||slot>=s->party_count)return OMNI_ADVENTURE_ARGUMENT;if(!s->party[slot].hp)return OMNI_ADVENTURE_LOCKED;return omni_adventure_swap(s,0,slot);}
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
 unsigned max,chance;if(!s||!b||!b->active||b->outcome||(b->kind!=OMNI_BATTLE_WILD&&b->kind!=OMNI_BATTLE_TUTORIAL))return OMNI_ADVENTURE_LOCKED;
 if(b->kind==OMNI_BATTLE_TUTORIAL){b->outcome=4;return 0;}
 if(!s->balls||s->party_count>=6)return OMNI_ADVENTURE_LOCKED;
 --s->balls;max=omni_partner_stat(&b->mons[1],0);chance=35+(max-b->mons[1].hp)*60/max;if(b->mons[1].status)chance+=15;if(chance>99)chance=99;
 if((random32(&b->rng)>>16)%100>=chance)return OMNI_ADVENTURE_ALREADY;
 if(record_species(dex,state,b->mons[1].species,OMNI_DEX_REGISTERED))return OMNI_ADVENTURE_ARGUMENT;
 s->party[s->party_count++]=b->mons[1];b->outcome=4;return 0;
}
int omni_adventure_escape(OmniAdventure *s,OmniPractice *b){(void)s;if(!b||!b->active||b->outcome||b->kind!=OMNI_BATTLE_WILD)return OMNI_ADVENTURE_LOCKED;b->outcome=5;return 0;}
int omni_adventure_switch(OmniAdventure *s,OmniPractice *b,uint8_t slot){if(!s||!b||!b->active||slot>=s->party_count||!s->party[slot].hp||slot==b->party_slot)return OMNI_ADVENTURE_LOCKED;s->party[b->party_slot]=b->mons[0];b->party_slot=slot;b->mons[0]=s->party[slot];b->attack[0]=b->defense[0]=b->speed[0]=0;b->outcome=0;return 0;}
int omni_adventure_step(OmniAdventure *s,uint8_t grass){if(!s||!s->starter||s->location!=OMNI_ROUTE1||!grass)return 0;return ((random32(&s->rng)>>16)%16)==0;}
int omni_practice_wait(OmniPractice *b,OmniPracticeTurn *out){if(!b||!out||!b->active||b->outcome)return OMNI_ADVENTURE_LOCKED;memset(out,0,sizeof(*out));action(b,1,b->mons[1].pp[0]?0:1,&out->actions[0]);out->count=1;if(!b->mons[0].hp||!b->mons[1].hp)b->outcome=b->mons[0].hp?1:b->mons[1].hp?2:3;++b->turns;out->outcome=b->outcome;return 0;}

void omni_adventure_elapsed(OmniAdventure *s,uint32_t seconds){if(!s)return;s->play_seconds=seconds>3599999-s->play_seconds?3599999:s->play_seconds+seconds;}

int omni_initialization_gifts(OmniAdventure *s,const OmniDex *dex,OmniDexState *state){
 unsigned i;if(!s||s->location!=OMNI_LAB)return OMNI_ADVENTURE_LOCKED;
 if(!dex||!state||!dex->entries||!state->flags)return OMNI_ADVENTURE_ARGUMENT;
 if(s->events&OMNI_EVENT_GIFTS)return OMNI_ADVENTURE_ALREADY;
 if(s->party_count||s->starter)return OMNI_ADVENTURE_LOCKED;
 /* Validate every registration before granting anything. */
 for(i=0;i<4;++i){unsigned j;for(j=0;j<dex->count;++j)if(dex->entries[j].national==omni_starters[i].species&&dex->entries[j].category==1)break;if(j==dex->count||state->count!=dex->count)return OMNI_ADVENTURE_ARGUMENT;}
 create_mon(&s->party[0],4);s->party[0].form=1;s->party[0].bond_eligible=1;
 s->party[0].moves[2]=729;s->party[0].pp[2]=15;s->party[0].nature=10;
 s->party[0].evs[3]=252;s->party[0].evs[5]=252;s->party[0].evs[0]=4;
 for(i=1;i<4;++i){create_mon(&s->party[i],i);s->party[i].nature=i==2?10:15;s->party[i].evs[3]=252;s->party[i].evs[i==2?5:0]=252;s->party[i].evs[2]=4;}
 s->party_count=4;s->starter=4;s->chapter=2;s->balls=(uint16_t)(s->balls>899?999:s->balls+100);
 s->events|=OMNI_EVENT_INITIALIZATION|OMNI_EVENT_GIFTS;omni_adventure_heal(s);
 for(i=0;i<4;++i)record_species(dex,state,s->party[i].species,OMNI_DEX_REGISTERED);
 if(omni_dex_find(dex,OMNI_PARTNER_PIKACHU_DEX_ID)>=0)omni_dex_record(dex,state,OMNI_PARTNER_PIKACHU_DEX_ID,OMNI_DEX_REGISTERED);
 return 0;
}
int omni_initialization_battle(OmniAdventure *s,OmniPractice *b,uint8_t kind,const OmniDex *dex,OmniDexState *state){
 unsigned i,choice;if(!s||!b||!(s->events&OMNI_EVENT_GIFTS)||kind<3||kind>5)return OMNI_ADVENTURE_LOCKED;
 if((kind==OMNI_BATTLE_GARY&&(s->location!=OMNI_LAB||(s->events&OMNI_EVENT_GARY_DONE)))||(kind!=OMNI_BATTLE_GARY&&(s->location!=OMNI_VIRIDIAN||(s->events&OMNI_EVENT_OLD_DONE))))return OMNI_ADVENTURE_LOCKED;
 for(i=0;i<s->party_count&&!s->party[i].hp;++i){}if(i==s->party_count)return OMNI_ADVENTURE_LOCKED;
 choice=kind==OMNI_BATTLE_GARY?3:kind==OMNI_BATTLE_OLD_MAN?5:8;
 if(record_species(dex,state,omni_starters[choice-1].species,OMNI_DEX_SEEN))return OMNI_ADVENTURE_ARGUMENT;
 memset(b,0,sizeof(*b));b->kind=kind;b->party_slot=(uint8_t)i;b->mons[0]=s->party[i];create_mon(&b->mons[1],choice);
 b->mons[1].level=kind==OMNI_BATTLE_GARY?8:kind==OMNI_BATTLE_OLD_MAN?7:3;
 b->mons[1].experience=b->mons[1].level*b->mons[1].level*b->mons[1].level;b->mons[1].hp=omni_partner_stat(&b->mons[1],0);
 if(kind==OMNI_BATTLE_GARY){b->opponent_count=3;b->opponents[0]=b->mons[1];create_mon(&b->opponents[1],5);create_mon(&b->opponents[2],6);for(i=1;i<3;++i){b->opponents[i].level=(uint8_t)(8-i);b->opponents[i].experience=b->opponents[i].level*b->opponents[i].level*b->opponents[i].level;b->opponents[i].hp=omni_partner_stat(&b->opponents[i],0);}}
 b->rng=s->rng;b->active=1;return 0;
}
int omni_practice_next_opponent(OmniPractice *b,const OmniDex *dex,OmniDexState *state){
 unsigned next;if(!b||!b->active||b->outcome!=1)return OMNI_ADVENTURE_LOCKED;next=b->opponent_slot+1;if(next>=b->opponent_count)return OMNI_ADVENTURE_LOCKED;
 if(record_species(dex,state,b->opponents[next].species,OMNI_DEX_SEEN))return OMNI_ADVENTURE_ARGUMENT;
 b->opponent_slot=(uint8_t)next;b->mons[1]=b->opponents[next];b->attack[1]=b->defense[1]=b->speed[1]=0;b->outcome=0;return 0;
}
int omni_initialization_weedle(OmniAdventure *s,const OmniDex *dex,OmniDexState *state){
 OmniPartner mon;if(!s||!(s->events&OMNI_EVENT_WEEDLE_PENDING))return OMNI_ADVENTURE_ALREADY;
 if(s->party_count>=6&&s->storage_count>=12)return OMNI_ADVENTURE_LOCKED;
 if(record_species(dex,state,13,OMNI_DEX_REGISTERED))return OMNI_ADVENTURE_ARGUMENT;
 create_mon(&mon,8);mon.level=3;mon.experience=27;mon.hp=omni_partner_stat(&mon,0);
 if(s->party_count<6)s->party[s->party_count++]=mon;else s->storage[s->storage_count++]=mon;
 s->events&=(uint16_t)~OMNI_EVENT_WEEDLE_PENDING;return 0;
}
int omni_adventure_train(OmniAdventure *s,uint8_t slot,uint8_t tool,uint8_t parameter,uint16_t value){
 OmniPartner *m;unsigned i,total=0,old,max;if(!s||!(s->events&OMNI_EVENT_GIFTS)||tool>OMNI_TOOL_ESCAPE)return OMNI_ADVENTURE_LOCKED;
 if(tool==OMNI_TOOL_ESCAPE){if(s->location!=OMNI_SERVERS)return OMNI_ADVENTURE_LOCKED;s->location=OMNI_LAB;return 0;}
 if(slot>=s->party_count)return OMNI_ADVENTURE_ARGUMENT;m=&s->party[slot];old=omni_partner_stat(m,0);
 if(tool==OMNI_TOOL_MINT){if(value>24)return OMNI_ADVENTURE_ARGUMENT;m->nature=(uint8_t)value;}
 else if(tool==OMNI_TOOL_IV){for(i=0;i<6;++i)m->ivs[i]=31;}
 else if(tool==OMNI_TOOL_ABILITY){if(m->species!=16&&m->species!=19)return OMNI_ADVENTURE_ALREADY;m->ability^=1;}
 else{if(parameter>5||value>252)return OMNI_ADVENTURE_ARGUMENT;for(i=0;i<6;++i)total+=i==parameter?value:m->evs[i];if(total>510)return OMNI_ADVENTURE_LOCKED;m->evs[parameter]=value;}
 max=omni_partner_stat(m,0);if(m->hp)m->hp=(uint16_t)(max>=old?m->hp+max-old:m->hp>old-max?m->hp-(old-max):1);return 0;
}
int omni_adventure_store(OmniAdventure *s,uint8_t slot){unsigned i;if(!s||slot>=s->party_count||s->party_count<=1||s->storage_count>=12)return OMNI_ADVENTURE_LOCKED;for(i=0;i<s->party_count;++i)if(i!=slot&&s->party[i].hp)break;if(i==s->party_count)return OMNI_ADVENTURE_LOCKED;if(s->companion==slot+1)s->companion=0;else if(s->companion>slot+1)--s->companion;if(s->mount==slot+1)s->mount=0;else if(s->mount>slot+1)--s->mount;s->storage[s->storage_count++]=s->party[slot];for(i=slot;i+1<s->party_count;++i)s->party[i]=s->party[i+1];memset(&s->party[--s->party_count],0,sizeof(s->party[0]));return 0;}
int omni_adventure_withdraw(OmniAdventure *s,uint8_t slot){unsigned i;if(!s||slot>=s->storage_count||s->party_count>=6)return OMNI_ADVENTURE_LOCKED;s->party[s->party_count++]=s->storage[slot];for(i=slot;i+1<s->storage_count;++i)s->storage[i]=s->storage[i+1];memset(&s->storage[--s->storage_count],0,sizeof(s->storage[0]));return 0;}

int omni_adventure_companion(OmniAdventure *s,uint8_t slot){if(!s||slot>s->party_count)return OMNI_ADVENTURE_ARGUMENT;if(slot&&(!s->party[slot-1].hp||slot==s->mount))return OMNI_ADVENTURE_LOCKED;s->companion=slot;return 0;}

int omni_adventure_mount(OmniAdventure *s,uint8_t slot){if(!s||slot>s->party_count)return OMNI_ADVENTURE_ARGUMENT;if(slot&&(!s->party[slot-1].hp||slot==s->companion))return OMNI_ADVENTURE_LOCKED;s->mount=slot;return 0;}
