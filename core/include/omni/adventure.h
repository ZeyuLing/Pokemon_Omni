#ifndef OMNI_ADVENTURE_H
#define OMNI_ADVENTURE_H
#include "omni/pokedex.h"
/* Stable semantic location/person IDs; screen coordinates live in adapters. */
enum { OMNI_PALLET=1, OMNI_HOME=2, OMNI_BEDROOM=3, OMNI_RIVAL_HOME=4, OMNI_LAB=5, OMNI_ROUTE1=6, OMNI_VIRIDIAN=7, OMNI_CENTER=8, OMNI_MART=9 };
enum { OMNI_OAK=1, OMNI_MOM=2, OMNI_RIVAL=3, OMNI_NEIGHBOR=4, OMNI_WALKER=5, OMNI_DAISY=6, OMNI_AIDE=7, OMNI_PC=8, OMNI_PIKACHU=9, OMNI_NURSE=10, OMNI_ROCKET=11, OMNI_CLERK=12, OMNI_ROUTE_GUIDE=13 };
enum { OMNI_ADVENTURE_OK, OMNI_ADVENTURE_ARGUMENT, OMNI_ADVENTURE_LOCKED, OMNI_ADVENTURE_ALREADY, OMNI_ADVENTURE_BAD_SAVE };
enum { OMNI_TALK_INVALID, OMNI_TALK_OAK_OFFER, OMNI_TALK_OAK_PARTNER, OMNI_TALK_OAK_DONE, OMNI_TALK_MOM_START, OMNI_TALK_HEALED, OMNI_TALK_RIVAL_WAIT, OMNI_TALK_RIVAL_BATTLE, OMNI_TALK_NEIGHBOR, OMNI_TALK_WALKER, OMNI_TALK_DAISY, OMNI_TALK_AIDE, OMNI_TALK_PC_POTION, OMNI_TALK_PC_EMPTY };
enum { OMNI_EVENT_CENTER=1, OMNI_EVENT_ROCKET=2, OMNI_EVENT_PARCEL=4, OMNI_EVENT_DELIVERED=8 };
enum { OMNI_BATTLE_PRACTICE=0, OMNI_BATTLE_WILD=1, OMNI_BATTLE_ROCKET=2 };
typedef struct { uint16_t species,hp;uint8_t level,pp[4],status;uint32_t experience; } OmniPartner;
typedef struct {
 uint32_t rng,money;
 uint16_t location,potions,balls,battles_won,battles_played;
 uint8_t chapter,starter,party_count,pc_claimed;
 uint16_t events;
 OmniPartner party[6];
} OmniAdventure;
typedef struct { uint16_t species,base[6],moves[2];uint8_t pp[2];const char *name,*ability; } OmniStarter;
extern const OmniStarter omni_starters[7];
void omni_adventure_new(OmniAdventure *);
int omni_adventure_enter(OmniAdventure *,uint16_t location);
uint8_t omni_adventure_interact(OmniAdventure *,uint8_t person);
const char *omni_adventure_dialogue(uint8_t talk);
const char *omni_adventure_objective(const OmniAdventure *);
const char *omni_adventure_visit(OmniAdventure *,uint8_t person);
int omni_adventure_buy(OmniAdventure *,uint8_t item);
int omni_adventure_lead(OmniAdventure *,uint8_t slot);
int omni_adventure_choose(OmniAdventure *,uint8_t choice,const OmniDex *,OmniDexState *);
void omni_adventure_heal(OmniAdventure *);
int omni_adventure_potion(OmniAdventure *,uint8_t slot);
uint16_t omni_partner_stat(const OmniPartner *,uint8_t stat);
const OmniStarter *omni_partner_species(uint16_t species);
int omni_adventure_save(const OmniAdventure *,uint8_t *bytes,size_t capacity,size_t *written);
int omni_adventure_load(OmniAdventure *,const uint8_t *bytes,size_t length);

/* Deliberately bounded opening battle rules: Tackle, Scratch, Growl,
 * Tail Whip, Thunder Shock, Struggle. This is NOT the future complete battle engine. */
typedef struct {
 OmniPartner mons[2];int8_t attack[2],defense[2];uint32_t rng;
 uint8_t active,outcome,kind,party_slot;uint16_t turns;
} OmniPractice;
typedef struct {uint8_t actor,miss,critical,status;uint16_t move,damage,hp[2];} OmniPracticeAction;
typedef struct {uint8_t count,outcome;OmniPracticeAction actions[2];} OmniPracticeTurn;
int omni_practice_begin(OmniAdventure *,OmniPractice *,const OmniDex *,OmniDexState *);
int omni_practice_turn(OmniPractice *,uint8_t move_slot,OmniPracticeTurn *);
int omni_practice_finish(OmniAdventure *,OmniPractice *);
int omni_adventure_battle(OmniAdventure *,OmniPractice *,uint8_t kind,const OmniDex *,OmniDexState *);
int omni_adventure_capture(OmniAdventure *,OmniPractice *,const OmniDex *,OmniDexState *);
int omni_adventure_escape(OmniAdventure *,OmniPractice *);
int omni_adventure_switch(OmniAdventure *,OmniPractice *,uint8_t slot);
int omni_adventure_step(OmniAdventure *,uint8_t grass);
int omni_practice_wait(OmniPractice *,OmniPracticeTurn *);
const char *omni_practice_move_name(uint16_t id);
#endif
