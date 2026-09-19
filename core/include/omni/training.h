#ifndef OMNI_TRAINING_H
#define OMNI_TRAINING_H
#include <stdint.h>
typedef struct {
 uint32_t entry_id;
 uint16_t item, ability, moves[4], evs[6];
 uint8_t ivs[6], level, nature, generation, battle_kind, mechanic, source_validated;
} OmniTrainingPlan;
enum { OMNI_PLAN_OK, OMNI_PLAN_BAD_DATA, OMNI_PLAN_WRONG_FORMAT, OMNI_PLAN_UNKNOWN_GATES, OMNI_PLAN_LOCKED };
/* Three gate bits: species, item and complete move acquisition. Unknown is not unlocked. */
uint8_t omni_training_status(const OmniTrainingPlan *, uint8_t generation, uint8_t battle_kind,
    uint8_t known_gates, uint8_t unlocked_gates);
#endif
