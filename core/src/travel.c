#include "omni/travel.h"
/* Generated reference anatomy plus explicit Omni design exceptions. */
static const OmniTravelProfile profiles[]={
#include "../../content/travel/generated/profiles.inc"
};
const OmniTravelProfile *omni_travel_profile(uint16_t species){return species>=1&&species<=sizeof(profiles)/sizeof(profiles[0])?&profiles[species-1]:0;}
int omni_travel_eligible(const OmniTravelProfile *p){
 if(!p)return OMNI_TRAVEL_UNKNOWN;
 if(p->body<OMNI_BODY_MEDIUM)return OMNI_TRAVEL_SMALL;
 if(!p->support)return OMNI_TRAVEL_SUPPORT;
 if(!p->safe_contact)return OMNI_TRAVEL_CONTACT;
 return OMNI_TRAVEL_OK;
}
int omni_travel_access(const OmniTravelProfile *p,unsigned terrain,unsigned clearance,unsigned permissions){
 int reason=omni_travel_eligible(p);if(reason)return reason;
 if(terrain&OMNI_INDOOR)return OMNI_TRAVEL_TERRAIN;
 if(!(terrain&(OMNI_LAND|OMNI_WATER)))return OMNI_TRAVEL_TERRAIN;
 if((terrain&OMNI_WATER)&&!(permissions&OMNI_TRAVEL_PERMISSION_SURF))return OMNI_TRAVEL_SURF_REQUIRED;
 if(clearance<p->clearance)return OMNI_TRAVEL_SPACE;
 return OMNI_TRAVEL_OK;
}
int omni_travel_ride(const OmniTravelProfile *p,unsigned terrain,unsigned clearance){return omni_travel_access(p,terrain,clearance,0);}
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
