#include "omni/pokedex.h"
#include "omni/battle_stats.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
static const OmniDexEntry rows[]={
 {101,"喷火龙","Charizard",6,514,0,1,1,0,0},
 {102,"超级喷火龙 X","Charizard-Mega-X",6,16386,0,2,1,0,0},
 {103,"羁绊快龙","Dragonite Bond",149,0,0,9,1,1,0},
 {104,"皮卡丘","Pikachu",25,8,0,1,1,0,0}
};
int main(void) {
 const OmniDex d={rows,4};uint8_t flags[4]={0};OmniDexState s={flags,4};
 OmniDexFilter f={"",0,0,0,0,0,0};uint16_t out[2]={65535,65535};
 uint8_t bytes[100],bad[100],small[10],before[4];size_t written=0;
 {
  const OmniDexProfile profiles[]={{101,0,{78,84,78,109,85,100},{66,0,94},2,10,1,0},{102,101,{78,130,111,130,85,100},{181,0,0},2,15,1,0},{103,0,{0},{0},0,0,0,1},{104,0,{35,55,40,50,50,90},{9,0,31},4,0,1,0}};
  assert(omni_dex_profile(&d,profiles,4,102)->parent_id==101);
  assert(omni_dex_profile(&d,profiles,4,102)->stats[1]==130);
  assert(!omni_dex_profile(&d,profiles,3,102));
  assert(!omni_dex_profile(&d,profiles,4,999));
  assert(!omni_dex_profile(NULL,profiles,4,101));
 }
 assert(omni_hp_stat(78,50,31,0,0)==153);
 assert(omni_dynamax_max_hp(153,10,0)==306);
 assert(omni_dynamax_max_hp(153,0,0)==229);
 assert(omni_hp_stat(78,100,31,252,0)==360);
 assert(omni_dynamax_max_hp(360,10,0)==720);
 assert(omni_hp_stat(1,100,31,252,1)==1&&omni_dynamax_max_hp(1,10,1)==1);
 assert(!omni_hp_stat(78,0,31,0,0)&&!omni_hp_stat(78,50,32,0,0)&&!omni_hp_stat(78,50,31,253,0));
 assert(!omni_dynamax_max_hp(153,11,0)&&!omni_dynamax_max_hp(65535,10,0));
 assert(omni_dex_validate(&d)==OMNI_DEX_OK);
 assert(omni_dex_query(&d,&s,&f,0,out,2)==3 && out[0]==0 && out[1]==3);
 assert(omni_dex_query(&d,&s,&f,2,out,2)==3 && out[0]==1);
 f.include_research=1;assert(omni_dex_query(&d,&s,&f,0,out,2)==4);
 f.text="喷火龙";assert(omni_dex_query(&d,&s,&f,0,out,2)==2);
 f.text="cHaRiZaRd";assert(omni_dex_query(&d,&s,&f,0,out,2)==2);
 f.text="不存在";assert(!omni_dex_query(&d,&s,&f,0,out,2));
 f.text="";f.type=4;assert(omni_dex_query(&d,&s,&f,0,out,2)==1&&out[0]==3);
 f.type=19;assert(!omni_dex_query(&d,&s,&f,0,out,2));f.type=0;
 f.category=2;assert(omni_dex_query(&d,&s,&f,0,out,2)==1);f.category=0;
 f.national=6;assert(omni_dex_query(&d,&s,&f,0,out,2)==2);f.national=0;
 assert(omni_dex_record(&d,&s,101,2)==0&&flags[0]==3&&flags[1]==0);
 assert(omni_dex_record(&d,&s,102,4)==0&&flags[1]==7);
 assert(omni_dex_record(&d,&s,102,1)==0&&flags[1]==7);
 assert(omni_dex_record(&d,&s,103,1)==OMNI_DEX_RESEARCH&&flags[2]==0);
 assert(omni_dex_record(&d,&s,555,1)==OMNI_DEX_UNKNOWN);
 assert(omni_dex_record(&d,&s,101,7)==OMNI_DEX_ARGUMENT);
 f.progress=4;assert(omni_dex_query(&d,&s,&f,0,out,2)==1&&out[0]==1);
 f.progress=1;assert(omni_dex_query(&d,&s,&f,0,out,2)==2);
 assert(omni_dex_count(&d,&s,0,0)==3&&omni_dex_count(&d,&s,1,0)==2);
 memset(small,0x5a,sizeof(small));assert(omni_dex_save(&d,&s,small,sizeof(small),&written)==OMNI_DEX_CAPACITY);
 assert(small[0]==0x5a&&small[9]==0x5a);
 assert(omni_dex_save_size(&s)==26);assert(omni_dex_save(&d,&s,bytes,sizeof(bytes),&written)==0&&written==26);
 memcpy(before,flags,4);memcpy(bad,bytes,written);bad[16]^=1;
 assert(omni_dex_load(&d,&s,bad,written)==OMNI_DEX_BAD_SAVE&&!memcmp(before,flags,4));
 assert(omni_dex_load(&d,&s,bytes,written-1)==OMNI_DEX_BAD_SAVE&&!memcmp(before,flags,4));
 memset(flags,0,4);assert(omni_dex_load(&d,&s,bytes,written)==0&&!memcmp(before,flags,4));
 { /* Stable IDs migrate across catalog reordering, removal and additions. */
   const OmniDexEntry changed[]={rows[1],rows[3],{999,"新增","Added",500,1,0,1,5,0,0}};
   const OmniDex next={changed,3};uint8_t nf[3]={0,0,7};OmniDexState ns={nf,3};
   assert(omni_dex_load(&next,&ns,bytes,written)==0&&nf[0]==7&&nf[1]==0&&nf[2]==0);
 }
 { const OmniDexEntry dup[]={rows[0],rows[0]};const OmniDex x={dup,2};assert(omni_dex_validate(&x)==OMNI_DEX_DUPLICATE); }
 puts("PASS: Pokedex search/filter, independent form progress, research gate, versioned save and atomic migration cases");
 return 0;
}
