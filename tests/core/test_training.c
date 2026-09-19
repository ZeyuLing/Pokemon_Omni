#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include "omni/training.h"
#include "plans.h"
int main(void){unsigned i;OmniTrainingPlan changed;
 for(i=0;i<OMNI_TRAINING_COUNT;++i){const OmniTrainingPlan *p=&omni_training_plans[i];
  assert(omni_training_status(p,p->generation,p->battle_kind,7,7)==OMNI_PLAN_OK);
  assert(omni_training_status(p,p->generation,p->battle_kind,0,0)==OMNI_PLAN_UNKNOWN_GATES);
  assert(omni_training_status(p,p->generation,p->battle_kind,7,5)==OMNI_PLAN_LOCKED);
  assert(omni_training_status(p,p->generation,p->battle_kind==1?2:1,7,7)==OMNI_PLAN_WRONG_FORMAT);
 }
 changed=omni_training_plans[0];changed.evs[0]=253;assert(omni_training_status(&changed,changed.generation,changed.battle_kind,7,7)==OMNI_PLAN_BAD_DATA);
 changed=omni_training_plans[0];changed.evs[0]=252;changed.evs[1]=252;changed.evs[2]=252;assert(omni_training_status(&changed,changed.generation,changed.battle_kind,7,7)==OMNI_PLAN_BAD_DATA);
 changed=omni_training_plans[0];changed.moves[1]=changed.moves[0];assert(omni_training_status(&changed,changed.generation,changed.battle_kind,7,7)==OMNI_PLAN_BAD_DATA);
 changed=omni_training_plans[0];changed.ivs[2]=32;assert(omni_training_status(&changed,changed.generation,changed.battle_kind,7,7)==OMNI_PLAN_BAD_DATA);
 assert(omni_training_status(&changed,9,1,0,7)==OMNI_PLAN_BAD_DATA);
 puts("PASS: all training plans, format boundaries, unknown and locked acquisition gates, EV/IV and duplicate moves");return 0;
}
