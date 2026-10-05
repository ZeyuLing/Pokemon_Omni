#include "omni/travel.h"
/* Size describes usable support/body volume, not a snake's total length.
 * These are Omni design classifications; unreviewed species can follow but
 * cannot be mounted until their anatomical profile is supplied. */
static const OmniTravelProfile profiles[]={
 {1,0,0,1,OMNI_LAND,1},{4,0,0,1,OMNI_LAND,1},
 {7,0,0,1,OMNI_LAND|OMNI_WATER,1},{25,0,0,1,OMNI_LAND,1},
 {16,0,0,1,OMNI_LAND|OMNI_WATER,1},{19,0,0,1,OMNI_LAND,1},
 {109,0,0,0,OMNI_LAND|OMNI_WATER,1},{13,0,0,0,OMNI_LAND,1},
 {111,OMNI_BODY_MEDIUM,OMNI_SUPPORT_BACK,1,OMNI_LAND,1},
 {59,OMNI_BODY_MEDIUM,OMNI_SUPPORT_BACK,1,OMNI_LAND,1},
 {128,OMNI_BODY_MEDIUM,OMNI_SUPPORT_BACK,1,OMNI_LAND,1},
 {78,OMNI_BODY_MEDIUM,OMNI_SUPPORT_BACK,1,OMNI_LAND,1},
 {131,OMNI_BODY_LARGE,OMNI_SUPPORT_SHELL,1,OMNI_WATER,2},
 {95,OMNI_BODY_LARGE,OMNI_SUPPORT_BACK,1,OMNI_LAND,2},
 {130,OMNI_BODY_LARGE,OMNI_SUPPORT_BACK,1,OMNI_WATER,2}
};
const OmniTravelProfile *omni_travel_profile(uint16_t species){unsigned i;for(i=0;i<sizeof(profiles)/sizeof(profiles[0]);++i)if(profiles[i].species==species)return &profiles[i];return 0;}
int omni_travel_ride(const OmniTravelProfile *p,unsigned terrain,unsigned clearance){
 if(!p)return OMNI_TRAVEL_UNKNOWN;
 if(p->body<OMNI_BODY_MEDIUM)return OMNI_TRAVEL_SMALL;
 if(!p->support)return OMNI_TRAVEL_SUPPORT;
 if(!p->safe_contact)return OMNI_TRAVEL_CONTACT;
 if((terrain&OMNI_INDOOR)||!(p->surfaces&terrain&(OMNI_LAND|OMNI_WATER)))return OMNI_TRAVEL_TERRAIN;
 if(clearance<p->clearance)return OMNI_TRAVEL_SPACE;
 return OMNI_TRAVEL_OK;
}
unsigned omni_travel_speed(unsigned mounted,unsigned running,unsigned terrain){return mounted?((terrain&OMNI_ROUGH)?4:8):(running?4:2);}
void omni_travel_reset(OmniTravel *t,unsigned location,unsigned species,int x,int y){
 t->x=t->from_x=t->to_x=(int16_t)x;t->y=t->from_y=t->to_y=(int16_t)y;
 t->location=(uint16_t)location;t->species=(uint16_t)species;t->face=0;t->visible=t->walking=0;
}
void omni_travel_step(OmniTravel *t,int old_x,int old_y,unsigned terrain,unsigned clear){
 const OmniTravelProfile *p=omni_travel_profile(t->species);int dx,dy;
 if(!t->species||!clear||(p&&(p->clearance>clear||!(p->surfaces&terrain&(OMNI_LAND|OMNI_WATER))))||(!p&&!(terrain&OMNI_LAND))){t->visible=t->walking=0;return;}
 if(!t->visible){t->x=(int16_t)old_x;t->y=(int16_t)old_y;}
 t->from_x=t->x;t->from_y=t->y;t->to_x=(int16_t)old_x;t->to_y=(int16_t)old_y;
 dx=old_x-t->x;dy=old_y-t->y;
 /* Never cut a corner or teleport along a stale route after a blocked tile. */
 if((dx&&dy)||dx>16||dx<-16||dy>16||dy<-16){t->visible=t->walking=0;return;}
 if(dx||dy)t->face=(uint8_t)(dx?dx>0?3:2:dy>0?0:1);
 t->visible=1;t->walking=(uint8_t)!!(dx||dy);
}
void omni_travel_sample(OmniTravel *t,unsigned progress){if(progress>16)progress=16;t->x=(int16_t)(t->from_x+(t->to_x-t->from_x)*(int)progress/16);t->y=(int16_t)(t->from_y+(t->to_y-t->from_y)*(int)progress/16);if(progress==16)t->walking=0;}
