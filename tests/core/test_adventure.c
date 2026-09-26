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
#ifdef OMNI_TEST_WASM
 rounds_checked=total;
#endif
 printf("PASS: starter/story/one-time rewards, save atomicity, public-state practice policy, %u deterministic battle rounds\n",total);
 return 0;
}
