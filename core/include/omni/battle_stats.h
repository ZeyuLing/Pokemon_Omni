#ifndef OMNI_BATTLE_STATS_H
#define OMNI_BATTLE_STATS_H
#include <stdint.h>
/* Zero means invalid input. fixed_one_hp is a species rule (Shedinja), not a
 * heuristic inferred from current HP. No effect on the species' base stats. */
uint16_t omni_hp_stat(uint16_t base_hp,uint8_t level,uint8_t iv,uint16_t ev,uint8_t fixed_one_hp);
uint16_t omni_dynamax_max_hp(uint16_t normal_max_hp,uint8_t dynamax_level,uint8_t fixed_one_hp);
#endif
