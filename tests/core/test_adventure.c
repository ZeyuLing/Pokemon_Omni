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
 {333,"Squirtle","Squirtle",7,0,0,1,1,0,0}
};
static const OmniDex dex={entries,3};
int main(void){
 unsigned starter,seed,total=0;
 for(starter=1;starter<=3;++starter){
  OmniAdventure g,old,loaded;OmniPractice b,b2;OmniPracticeTurn out,out2;uint8_t flags[3]={0},save[132];size_t size=0;OmniDexState state={flags,3};
  omni_adventure_new(&g);assert(g.location==OMNI_BEDROOM);assert(omni_adventure_interact(&g,OMNI_OAK)==OMNI_TALK_INVALID);
  assert(omni_adventure_choose(&g,starter,&dex,&state)==OMNI_ADVENTURE_LOCKED);
  assert(omni_adventure_interact(&g,OMNI_PC)==OMNI_TALK_PC_POTION);assert(g.potions==1);
  assert(omni_adventure_interact(&g,OMNI_PC)==OMNI_TALK_PC_EMPTY);assert(g.potions==1);
  omni_adventure_enter(&g,OMNI_LAB);assert(omni_adventure_interact(&g,OMNI_OAK)==OMNI_TALK_OAK_OFFER);
  assert(!omni_adventure_choose(&g,starter,&dex,&state));assert(flags[starter-1]==3&&g.potions==4&&g.chapter==2);
  old=g;assert(omni_adventure_choose(&g,starter,&dex,&state)==OMNI_ADVENTURE_ALREADY);assert(!memcmp(&g,&old,sizeof(g)));
  assert(omni_adventure_potion(&g,0)==OMNI_ADVENTURE_LOCKED);g.party[0].hp=1;assert(!omni_adventure_potion(&g,0));assert(g.potions==3);
  assert(!omni_adventure_save(&g,save,sizeof(save),&size)&&size==132);assert(!omni_adventure_load(&loaded,save,size));assert(!memcmp(&loaded,&g,sizeof(g)));
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
#ifdef OMNI_TEST_WASM
 rounds_checked=total;
#endif
 printf("PASS: starter/story/one-time rewards, save atomicity, public-state practice policy, %u deterministic battle rounds\n",total);
 return 0;
}
