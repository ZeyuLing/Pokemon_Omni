#include "omni/training.h"
uint8_t omni_training_status(const OmniTrainingPlan *p,uint8_t gen,uint8_t kind,uint8_t known,uint8_t unlocked){
 unsigned i,j,total=0,moves=0;
 if(!p||!p->entry_id||!p->source_validated||!p->ability||p->nature>=25||!p->level||p->level>100||p->generation<3||p->generation>9||p->battle_kind<1||p->battle_kind>2||(known&~7u)||(unlocked&~known))return OMNI_PLAN_BAD_DATA;
 for(i=0;i<6;++i){if(p->evs[i]>252||p->ivs[i]>31)return OMNI_PLAN_BAD_DATA;total+=p->evs[i];}
 if(total>510)return OMNI_PLAN_BAD_DATA;
 for(i=0;i<4;++i)if(p->moves[i]){++moves;for(j=0;j<i;++j)if(p->moves[i]==p->moves[j])return OMNI_PLAN_BAD_DATA;}
 if(!moves)return OMNI_PLAN_BAD_DATA;
 if(gen!=p->generation||kind!=p->battle_kind)return OMNI_PLAN_WRONG_FORMAT;
 if(known&~unlocked)return OMNI_PLAN_LOCKED;
 if(known!=7)return OMNI_PLAN_UNKNOWN_GATES;
 return OMNI_PLAN_OK;
}
