#ifndef OMNI_BATTLEFIELD_H
#define OMNI_BATTLEFIELD_H
#include <stdint.h>
/* Scripted map-event combat, not a PvP rules engine. Units and attack timing
 * are platform-independent; adapters supply sprites, particles and sound. */
typedef struct {int16_t x,y,tx,ty;uint16_t start,duration,phase;uint8_t sprite,team,layer,target,attack,role;} OmniWarActor;
typedef struct {int16_t x,y;uint8_t face,step,action,hit;uint16_t phase;} OmniWarPose;
enum {OMNI_WAR_IDLE,OMNI_WAR_ADVANCE,OMNI_WAR_CHARGE,OMNI_WAR_FIRE,OMNI_WAR_RECOVER};
void omni_war_sample(const OmniWarActor *,unsigned count,unsigned index,uint32_t ticks,OmniWarPose *);
#endif
