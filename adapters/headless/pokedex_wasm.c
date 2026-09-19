#include "omni/pokedex.h"
#include "omni/battle_stats.h"
#include "catalog.h"
#include "plans.h"
static uint8_t flags[OMNI_CATALOG_ENTRY_COUNT];
static OmniDexState state={flags,OMNI_CATALOG_ENTRY_COUNT};
static uint8_t input[65536];
static uint16_t results[4096];
unsigned training_hash(void){return OMNI_TRAINING_HASH;}
unsigned training_count(void){return OMNI_TRAINING_COUNT;}
unsigned training_status(unsigned index,unsigned gen,unsigned kind,unsigned known,unsigned unlocked){
    if(index>=OMNI_TRAINING_COUNT||gen>9||kind>2||known>7||unlocked>7)return OMNI_PLAN_BAD_DATA;
    return omni_training_status(&omni_training_plans[index],(uint8_t)gen,(uint8_t)kind,(uint8_t)known,(uint8_t)unlocked);
}
unsigned dex_hp(unsigned base,unsigned level,unsigned iv,unsigned ev,unsigned fixed) {
    if(base>255||level>100||iv>31||ev>252||fixed>1)return 0;
    return omni_hp_stat((uint16_t)base,(uint8_t)level,(uint8_t)iv,(uint16_t)ev,(uint8_t)fixed);
}
unsigned dex_max_hp(unsigned hp,unsigned level,unsigned fixed) {
    if(hp>65535||level>10||fixed>1)return 0;
    return omni_dynamax_max_hp((uint16_t)hp,(uint8_t)level,(uint8_t)fixed);
}
unsigned dex_count(void) { return omni_pokedex_catalog.count; }
unsigned dex_input_ptr(void) { return (unsigned)(uintptr_t)input; }
unsigned dex_result_ptr(void) { return (unsigned)(uintptr_t)results; }
unsigned dex_id(unsigned index) { return index<state.count?omni_pokedex_catalog.entries[index].id:0; }
unsigned dex_stat(unsigned index,unsigned stat) {
    const OmniDexProfile *p;
    if(index>=state.count||stat>=6)return 0;
    p=omni_dex_profile(&omni_pokedex_catalog,omni_pokedex_profiles,OMNI_CATALOG_ENTRY_COUNT,dex_id(index));
    return p&&p->has_stats?p->stats[stat]:0;
}
unsigned dex_parent(unsigned index) {
    return index<state.count?omni_pokedex_profiles[index].parent_id:0;
}
unsigned dex_ability(unsigned index,unsigned slot) {
    return index<state.count&&slot<4?omni_pokedex_profiles[index].abilities[slot]:0;
}
unsigned dex_flags(unsigned index) { return index<state.count?flags[index]:0; }
unsigned dex_total(unsigned flag) { return omni_dex_count(&omni_pokedex_catalog,&state,(uint8_t)flag,0); }
unsigned dex_query(unsigned category,unsigned gen,unsigned type,unsigned progress,unsigned research,unsigned national,unsigned offset) {
    OmniDexFilter f;
    unsigned i;
    if(category>31||gen>9||type>18||progress>4||research>1||national>65535||offset>65535)return 0;
    input[255]=0;
    f.text=(const char*)input;f.category=(uint8_t)category;f.generation=(uint8_t)gen;f.type=(uint8_t)type;
    f.progress=(uint8_t)progress;f.include_research=(uint8_t)research;f.national=(uint16_t)national;
    for(i=0;i<40;++i)results[i]=65535;
    return omni_dex_query(&omni_pokedex_catalog,&state,&f,(uint16_t)offset,results,40);
}
unsigned dex_record(unsigned index,unsigned event) {
    if(index>=state.count||event>255)return OMNI_DEX_ARGUMENT;
    return (unsigned)omni_dex_record(&omni_pokedex_catalog,&state,omni_pokedex_catalog.entries[index].id,(uint8_t)event);
}
unsigned dex_query_all(unsigned category,unsigned gen,unsigned type,unsigned progress,unsigned research,unsigned national){
    OmniDexFilter f;
    if(category>31||gen>9||type>18||progress>4||research>1||national>65535)return 0;
    input[255]=0;f.text=(const char*)input;f.category=(uint8_t)category;f.generation=(uint8_t)gen;f.type=(uint8_t)type;
    f.progress=(uint8_t)progress;f.include_research=(uint8_t)research;f.national=(uint16_t)national;
    return omni_dex_query(&omni_pokedex_catalog,&state,&f,0,results,4096);
}
unsigned dex_save(void) {
    size_t n=0;
    if(omni_dex_save(&omni_pokedex_catalog,&state,input,sizeof(input),&n)!=OMNI_DEX_OK)return 0;
    return (unsigned)n;
}
unsigned dex_load(unsigned n) {
    if(n>sizeof(input))return OMNI_DEX_CAPACITY;
    return (unsigned)omni_dex_load(&omni_pokedex_catalog,&state,input,n);
}
