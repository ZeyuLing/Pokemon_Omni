#ifdef NDEBUG
#undef NDEBUG
#endif
#ifdef OMNI_TEST_WASM
static unsigned failure_line,rounds_checked;
unsigned test_failure_line(void){return failure_line;}
unsigned test_rounds_checked(void){return rounds_checked;}
#define assert(condition) do { if(!(condition)){failure_line=__LINE__;__builtin_trap();} } while(0)
#define printf(...) ((void)0)
#define main omni_adventure_test
#else
#include <assert.h>
#include <stdio.h>
#endif
#include "omni/memory.h"
#include "omni/adventure.h"
static const OmniDexEntry entries[]={
 {111,"Bulbasaur","Bulbasaur",1,0,0,1,1,0,0},
 {222,"Charmander","Charmander",4,0,0,1,1,0,0},
 {333,"Squirtle","Squirtle",7,0,0,1,1,0,0},
 {444,"Pikachu","Pikachu",25,0,0,1,1,0,0},
 {555,"Pidgey","Pidgey",16,0,0,1,1,0,0},
 {666,"Rattata","Rattata",19,0,0,1,1,0,0},
 {777,"Koffing","Koffing",109,0,0,1,1,0,0}
};
static const OmniDex dex={entries,7};
static void legacy_save(uint8_t *bytes){
 unsigned i;uint32_t h=2166136261u;
 bytes[4]=1;bytes[22]=bytes[23]=0;
 for(i=0;i<6;++i){bytes[35+i*16]=0;memset(bytes+42+i*16,0,4);}
 for(i=0;i<128;++i)h=(h^bytes[i])*16777619u;
 for(i=0;i<4;++i)bytes[128+i]=(uint8_t)(h>>(i*8));
}
int main(void){
 unsigned starter,seed,total=0;
 {
  OmniAdventure g,loaded;uint8_t bytes[OMNI_ADVENTURE_SAVE_BYTES];size_t n;
  omni_adventure_new(&g);omni_adventure_elapsed(&g,3661);g.badges=2;
  assert(!omni_adventure_save(&g,bytes,sizeof(bytes),&n));
  assert(!omni_adventure_load(&loaded,bytes,n)&&loaded.play_seconds==3661&&loaded.badges==2);
  omni_adventure_elapsed(&g,0xffffffffu);assert(g.play_seconds==3599999);
  g.badges=9;assert(omni_adventure_save(&g,bytes,sizeof(bytes),&n)==OMNI_ADVENTURE_ARGUMENT);
 }

 for(starter=1;starter<=3;++starter){
  OmniAdventure g,old,loaded;OmniPractice b,b2;OmniPracticeTurn out,out2;uint8_t flags[7]={0},save[OMNI_ADVENTURE_SAVE_BYTES];size_t size=0;OmniDexState state={flags,7};
  omni_adventure_new(&g);assert(g.location==OMNI_BEDROOM);assert(omni_adventure_interact(&g,OMNI_OAK)==OMNI_TALK_INVALID);
  assert(omni_adventure_choose(&g,starter,&dex,&state)==OMNI_ADVENTURE_LOCKED);
  assert(omni_adventure_interact(&g,OMNI_PC)==OMNI_TALK_PC_POTION);assert(g.potions==1);
  assert(omni_adventure_interact(&g,OMNI_PC)==OMNI_TALK_PC_EMPTY);assert(g.potions==1);
  omni_adventure_enter(&g,OMNI_LAB);assert(omni_adventure_interact(&g,OMNI_OAK)==OMNI_TALK_OAK_OFFER);
  assert(!omni_adventure_choose(&g,starter,&dex,&state));assert(flags[starter-1]==3&&g.potions==4&&g.chapter==2);
  old=g;assert(omni_adventure_choose(&g,starter,&dex,&state)==OMNI_ADVENTURE_ALREADY);assert(!memcmp(&g,&old,sizeof(g)));
  assert(omni_adventure_potion(&g,0)==OMNI_ADVENTURE_LOCKED);g.party[0].hp=1;assert(!omni_adventure_potion(&g,0));assert(g.potions==3);
  assert(!omni_adventure_save(&g,save,sizeof(save),&size)&&size==OMNI_ADVENTURE_SAVE_BYTES);assert(!omni_adventure_load(&loaded,save,size));assert(!memcmp(&loaded,&g,sizeof(g)));
  legacy_save(save);size=132;assert(!omni_adventure_load(&loaded,save,size));assert(!memcmp(&loaded,&g,sizeof(g)));
  old=loaded;save[64]^=1;assert(omni_adventure_load(&loaded,save,size)==OMNI_ADVENTURE_BAD_SAVE);assert(!memcmp(&loaded,&old,sizeof(old)));
  for(seed=0;seed<40;++seed){
   unsigned rounds=0;omni_adventure_heal(&g);g.rng=seed;assert(!omni_practice_begin(&g,&b,&dex,&state));b2=b;
   assert(flags[starter%3]&OMNI_DEX_SEEN);
   while(!b.outcome&&rounds++<100){
    uint8_t slot=(rounds<=8)?1:0;
    assert(!omni_practice_turn(&b,slot,&out));assert(!omni_practice_turn(&b2,slot,&out2));assert(!memcmp(&b,&b2,sizeof(b)));assert(!memcmp(&out,&out2,sizeof(out)));
    assert(b.attack[0]>=-6&&b.attack[1]>=-6&&b.defense[0]>=-6&&b.defense[1]>=-6);++total;
   }
   assert(b.outcome);assert(!omni_practice_finish(&g,&b));assert(omni_practice_finish(&g,&b)==OMNI_ADVENTURE_LOCKED);assert(g.chapter==3&&g.money==3100);
  }
  assert(!omni_practice_begin(&g,&b,&dex,&state));b.mons[0].pp[0]=b.mons[0].pp[1]=0;assert(!omni_practice_turn(&b,0,&out));assert(out.actions[0].move==165||out.actions[1].move==165);
 }
 {
  OmniAdventure g,loaded,prior;OmniPractice b;OmniPracticeTurn out;uint8_t flags[7]={0},bytes[OMNI_ADVENTURE_SAVE_BYTES];size_t size;unsigned attempts=0,balls,money;
  OmniDexState state={flags,7};omni_adventure_new(&g);
  assert(omni_adventure_enter(&g,OMNI_ROUTE1)==OMNI_ADVENTURE_LOCKED);
  omni_adventure_enter(&g,OMNI_LAB);omni_adventure_interact(&g,OMNI_OAK);assert(!omni_adventure_choose(&g,4,&dex,&state));assert(g.party[0].species==25&&g.balls==5&&flags[3]==3);
  assert(!omni_adventure_enter(&g,OMNI_ROUTE1));assert(!omni_adventure_battle(&g,&b,1,&dex,&state));b.mons[1].hp=1;balls=g.balls;
  while(omni_adventure_capture(&g,&b,&dex,&state)&&++attempts<5){assert(!omni_practice_wait(&b,&out));assert(out.count==1&&out.actions[0].actor==1);}
  assert(b.outcome==4&&g.party_count==2&&g.balls<balls);assert(!omni_practice_finish(&g,&b));assert(omni_adventure_capture(&g,&b,&dex,&state)==OMNI_ADVENTURE_LOCKED);
  assert(!omni_adventure_lead(&g,1));assert(g.party[0].species!=25);assert(!omni_adventure_lead(&g,1));
  assert(!omni_adventure_save(&g,bytes,sizeof(bytes),&size));assert(!omni_adventure_load(&loaded,bytes,size));assert(!memcmp(&g,&loaded,sizeof(g)));prior=loaded;bytes[50]^=1;assert(omni_adventure_load(&loaded,bytes,size)==OMNI_ADVENTURE_BAD_SAVE);assert(!memcmp(&prior,&loaded,sizeof(prior)));
  omni_adventure_enter(&g,OMNI_CENTER);assert(omni_adventure_battle(&g,&b,2,&dex,&state)==OMNI_ADVENTURE_LOCKED);assert(omni_adventure_visit(&g,OMNI_NURSE));
  assert(!omni_adventure_battle(&g,&b,2,&dex,&state));balls=g.balls;assert(omni_adventure_capture(&g,&b,&dex,&state)==OMNI_ADVENTURE_LOCKED&&g.balls==balls);assert(omni_adventure_escape(&g,&b)==OMNI_ADVENTURE_LOCKED);
  b.mons[1].hp=1;assert(!omni_practice_turn(&b,0,&out));assert(b.outcome==1);money=g.money;assert(!omni_practice_finish(&g,&b));assert(g.events&OMNI_EVENT_ROCKET);assert(g.money==money+400);
  assert(!omni_adventure_battle(&g,&b,2,&dex,&state));b.mons[1].hp=1;assert(!omni_practice_turn(&b,0,&out));assert(!omni_practice_finish(&g,&b));assert(g.money==money+400);
  omni_adventure_enter(&g,OMNI_MART);assert(omni_adventure_visit(&g,OMNI_CLERK));assert(g.events&OMNI_EVENT_PARCEL);balls=g.balls;assert(!omni_adventure_buy(&g,0)&&g.balls==balls+1);g.money=0;assert(omni_adventure_buy(&g,0)==OMNI_ADVENTURE_LOCKED);
  omni_adventure_enter(&g,OMNI_LAB);balls=g.balls;assert(omni_adventure_visit(&g,OMNI_OAK));assert(g.balls==balls+5);assert(!omni_adventure_visit(&g,OMNI_OAK)&&g.balls==balls+5);
  assert(!omni_adventure_save(&g,bytes,sizeof(bytes),&size));assert(!omni_adventure_load(&loaded,bytes,size));assert(loaded.events==15);
  omni_adventure_enter(&g,OMNI_ROUTE1);omni_adventure_heal(&g);assert(!omni_adventure_battle(&g,&b,1,&dex,&state));b.mons[0].hp=0;b.outcome=2;assert(!omni_adventure_switch(&g,&b,1));assert(!g.party[0].hp&&b.party_slot==1&&!b.outcome);assert(!omni_adventure_escape(&g,&b));assert(!omni_practice_finish(&g,&b));
  omni_adventure_heal(&g);g.party_count=6;for(attempts=1;attempts<6;++attempts)g.party[attempts]=g.party[0];assert(!omni_adventure_battle(&g,&b,1,&dex,&state));balls=g.balls;assert(omni_adventure_capture(&g,&b,&dex,&state)==OMNI_ADVENTURE_LOCKED&&g.balls==balls);
  assert(!omni_adventure_save(&g,bytes,sizeof(bytes),&size));assert(!omni_adventure_load(&loaded,bytes,size)&&loaded.party_count==6);
  /* A wipe heals everyone, returns home and charges only once. */
  g.money=1000;for(attempts=0;attempts<6;++attempts)g.party[attempts].hp=0;
  b.mons[0].hp=0;b.outcome=2;assert(!omni_practice_finish(&g,&b));assert(g.location==OMNI_HOME&&g.money==900);
  for(attempts=0;attempts<6;++attempts)assert(g.party[attempts].hp==omni_partner_stat(&g.party[attempts],0));
  assert(omni_practice_finish(&g,&b)==OMNI_ADVENTURE_LOCKED&&g.money==900);
 }
 {
  /* Physical stages cannot weaken Thunder Shock; full paralysis spends no PP. */
  OmniAdventure g;OmniPractice b,c;OmniPracticeTurn out,other;uint8_t flags[7]={0};OmniDexState state={flags,7};unsigned paralyzed=0,attempts;
  omni_adventure_new(&g);omni_adventure_enter(&g,OMNI_LAB);omni_adventure_interact(&g,OMNI_OAK);assert(!omni_adventure_choose(&g,4,&dex,&state));
  omni_adventure_enter(&g,OMNI_ROUTE1);
  for(seed=0;seed<100;++seed){
   g.rng=seed;assert(!omni_adventure_battle(&g,&b,1,&dex,&state));b.mons[1].pp[1]=0;c=b;c.attack[0]=-6;c.defense[1]=-6;
   assert(!omni_practice_turn(&b,0,&out));assert(!omni_practice_turn(&c,0,&other));assert(out.actions[0].actor==0&&out.actions[0].damage==other.actions[0].damage);
   assert(!omni_adventure_battle(&g,&b,1,&dex,&state));b.mons[0].status=1;assert(!omni_practice_turn(&b,0,&out));
   for(attempts=0;attempts<out.count;++attempts)if(!out.actions[attempts].actor&&out.actions[attempts].miss){assert(b.mons[0].pp[0]==30);++paralyzed;}
  }
  assert(paralyzed);
 }
 {
  /* Authored initialization: atomic gifts, exclusive partner, legal reusable
   * training, both battle outcomes, one-time boxed reward and save migration. */
  OmniAdventure g,copy,loaded;OmniPractice b;OmniPracticeTurn out;
  OmniDexEntry all[8];OmniDex full={all,8};uint8_t flags[8]={0},bytes[OMNI_ADVENTURE_SAVE_BYTES];OmniDexState state={flags,8};size_t n;unsigned i,k,balls;
  memcpy(all,entries,sizeof(entries));all[7]=entries[0];all[7].id=888;all[7].national=13;
  omni_adventure_new(&g);omni_adventure_enter(&g,OMNI_LAB);copy=g;
  assert(omni_initialization_gifts(&g,0,&state)==OMNI_ADVENTURE_ARGUMENT);assert(!memcmp(&g,&copy,sizeof(g)));
  assert(!omni_initialization_gifts(&g,&full,&state));assert(g.party_count==4&&g.balls==100&&g.party[0].form==1&&g.party[0].bond_eligible==1);
  assert(g.party[0].moves[2]==729&&g.party[0].pp[2]==15&&omni_partner_stat(&g.party[0],0)==21);
  for(i=0;i<4;++i){unsigned sum=0;for(k=0;k<6;++k){assert(g.party[i].ivs[k]==31);sum+=g.party[i].evs[k];}assert(sum==508);assert(g.party[i].level==5);}
  copy=g;assert(omni_initialization_gifts(&g,&full,&state)==OMNI_ADVENTURE_ALREADY);assert(!memcmp(&g,&copy,sizeof(g)));
  assert(omni_adventure_train(&g,0,OMNI_TOOL_EV,1,252)==OMNI_ADVENTURE_LOCKED);assert(!memcmp(&g,&copy,sizeof(g)));
  assert(!omni_adventure_train(&g,0,OMNI_TOOL_EV,3,0));assert(!omni_adventure_train(&g,0,OMNI_TOOL_EV,1,252));
  assert(!omni_adventure_train(&g,0,OMNI_TOOL_MINT,0,3));assert(omni_partner_stat(&g.party[0],1)==18);
  assert(omni_adventure_train(&g,0,OMNI_TOOL_ABILITY,0,0)==OMNI_ADVENTURE_ALREADY);
  g.party[0].ivs[1]=0;assert(!omni_adventure_train(&g,0,OMNI_TOOL_IV,0,0)&&g.party[0].ivs[1]==31);
  assert(!omni_initialization_battle(&g,&b,OMNI_BATTLE_GARY,&full,&state));assert(b.mons[1].level==8);
  assert(omni_adventure_escape(&g,&b)==OMNI_ADVENTURE_LOCKED);balls=g.balls;assert(omni_adventure_capture(&g,&b,&full,&state)==OMNI_ADVENTURE_LOCKED&&g.balls==balls);
  b.mons[1].hp=1;assert(!omni_practice_turn(&b,2,&out)&&b.outcome==1);assert(out.actions[0].move==729&&out.actions[0].critical&&out.actions[0].actor==0);
  assert(b.opponent_count==3);assert(omni_practice_finish(&g,&b)==OMNI_ADVENTURE_LOCKED);
  for(i=1;i<3;++i){unsigned playerhp=b.mons[0].hp;assert(!omni_practice_next_opponent(&b,&full,&state));assert(b.mons[1].species==(i==1?16:19)&&b.mons[1].level==8-i);assert(!b.outcome&&b.mons[0].hp==playerhp);b.mons[1].hp=1;assert(!omni_practice_turn(&b,2,&out)&&b.outcome==1);}
  assert(omni_practice_next_opponent(&b,&full,&state)==OMNI_ADVENTURE_LOCKED);
  assert(!omni_practice_finish(&g,&b));assert(g.events&OMNI_EVENT_GARY_DONE);assert(g.party[0].hp==omni_partner_stat(&g.party[0],0));
  g=copy;assert(!omni_initialization_battle(&g,&b,OMNI_BATTLE_GARY,&full,&state));b.mons[0].hp=0;b.outcome=2;assert(!omni_practice_finish(&g,&b));assert((g.events&OMNI_EVENT_GARY_DONE)&&g.location==OMNI_LAB&&g.money==3000);
  omni_adventure_enter(&g,OMNI_VIRIDIAN);assert(!omni_initialization_battle(&g,&b,OMNI_BATTLE_TUTORIAL,&full,&state));assert(!omni_adventure_capture(&g,&b,&full,&state)&&g.balls==100);assert(!omni_practice_finish(&g,&b));
  g.party[4]=g.party[5]=g.party[0];g.party_count=6;g.storage_count=12;for(i=0;i<12;++i)g.storage[i]=g.party[0];
  assert(omni_initialization_weedle(&g,&full,&state)==OMNI_ADVENTURE_LOCKED);assert(g.events&OMNI_EVENT_WEEDLE_PENDING);
  g.storage_count=0;memset(g.storage,0,sizeof(g.storage));assert(!omni_initialization_weedle(&g,&full,&state));assert(g.storage_count==1&&g.storage[0].species==13);assert(omni_initialization_weedle(&g,&full,&state)==OMNI_ADVENTURE_ALREADY);
  assert(!omni_adventure_store(&g,1));assert(!omni_adventure_withdraw(&g,0));assert(g.party[5].species==13);
  assert(!omni_adventure_save(&g,bytes,sizeof(bytes),&n));assert(n==916);assert(!omni_adventure_load(&loaded,bytes,n));assert(!memcmp(&g,&loaded,sizeof(g)));
  copy=loaded;bytes[154]=255;assert(omni_adventure_load(&loaded,bytes,n)==OMNI_ADVENTURE_BAD_SAVE);assert(!memcmp(&loaded,&copy,sizeof(loaded)));
  for(i=1;i<g.party_count;++i)g.party[i].hp=0;assert(omni_adventure_store(&g,0)==OMNI_ADVENTURE_LOCKED);
  omni_adventure_enter(&g,OMNI_SERVERS);assert(!omni_adventure_train(&g,0,OMNI_TOOL_ESCAPE,0,0)&&g.location==OMNI_LAB);
 }
#ifdef OMNI_TEST_WASM
 rounds_checked=total;
#endif
 printf("PASS: starter/story/one-time rewards, save atomicity, public-state practice policy, %u deterministic battle rounds\n",total);
 return 0;
}
