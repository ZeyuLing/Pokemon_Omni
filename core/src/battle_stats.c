#include "omni/battle_stats.h"
uint16_t omni_hp_stat(uint16_t base,uint8_t level,uint8_t iv,uint16_t ev,uint8_t fixed) {
    uint32_t hp;
    if(!base||base>255||!level||level>100||iv>31||ev>252||fixed>1)return 0;
    if(fixed)return 1;
    hp=((2u*base+iv+ev/4u)*level)/100u+level+10u;
    return (uint16_t)hp;
}
uint16_t omni_dynamax_max_hp(uint16_t hp,uint8_t level,uint8_t fixed) {
    uint32_t result;
    if(!hp||level>10||fixed>1||(fixed&&hp!=1))return 0;
    if(fixed)return 1;
    result=(uint32_t)hp*(30u+level)/20u;
    return result>65535u?0:(uint16_t)result;
}
