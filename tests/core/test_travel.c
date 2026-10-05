#ifdef OMNI_TEST_WASM
static unsigned failure_line;
unsigned travel_failure_line(void){return failure_line;}
#define assert(c) do{if(!(c)){failure_line=__LINE__;__builtin_trap();}}while(0)
#define main travel_test
#else
#include <assert.h>
#endif
#include "omni/travel.h"
int main(void){
 OmniTravel t;OmniTravelProfile p={999,1,1,1,OMNI_LAND,2};
 /* Exhaust every species: neither water typing nor riding grants Surf. */
 {unsigned id,eligible=0;for(id=1;id<=1025;++id){const OmniTravelProfile *q=omni_travel_profile(id);
 assert(q&&q->species==id);
 if(!omni_travel_eligible(q)){++eligible;assert(!omni_travel_ride(q,OMNI_LAND,2));
 assert(omni_travel_ride(q,OMNI_WATER,2)==OMNI_TRAVEL_SURF_REQUIRED);
 assert(!omni_travel_access(q,OMNI_WATER,2,OMNI_TRAVEL_PERMISSION_SURF));
 assert(omni_travel_access(q,OMNI_INDOOR|OMNI_LAND,2,OMNI_TRAVEL_PERMISSION_SURF)==OMNI_TRAVEL_TERRAIN);
 assert(omni_travel_access(q,0,2,OMNI_TRAVEL_PERMISSION_SURF)==OMNI_TRAVEL_TERRAIN);
 }}assert(eligible>100);}
 assert(omni_travel_ride(omni_travel_profile(25),OMNI_LAND,1)==OMNI_TRAVEL_SMALL);
 assert(!omni_travel_ride(omni_travel_profile(111),OMNI_LAND,1));
 assert(!omni_travel_ride(omni_travel_profile(131),OMNI_LAND,1));
 assert(!omni_travel_ride(omni_travel_profile(18),OMNI_LAND,1));
 assert(omni_travel_ride(omni_travel_profile(18),OMNI_WATER,1)==OMNI_TRAVEL_SURF_REQUIRED);
 assert(omni_travel_ride(omni_travel_profile(95),OMNI_LAND,1)==OMNI_TRAVEL_SPACE);
 assert(omni_travel_ride(omni_travel_profile(130),OMNI_LAND,1)==OMNI_TRAVEL_SPACE);
 assert(!omni_travel_ride(omni_travel_profile(130),OMNI_LAND,2));
 assert(omni_travel_ride(&p,OMNI_LAND,1)==OMNI_TRAVEL_SPACE);
 p.safe_contact=0;assert(omni_travel_ride(&p,OMNI_LAND,2)==OMNI_TRAVEL_CONTACT);
 p.safe_contact=1;p.support=0;assert(omni_travel_ride(&p,OMNI_LAND,2)==OMNI_TRAVEL_SUPPORT);
 assert(omni_travel_ride(0,OMNI_LAND,2)==OMNI_TRAVEL_UNKNOWN);
 assert(omni_travel_eligible(omni_travel_profile(598))==OMNI_TRAVEL_CONTACT);
 assert(omni_travel_eligible(omni_travel_profile(904))==OMNI_TRAVEL_CONTACT);
 assert(!omni_travel_profile(0)&&!omni_travel_profile(1026));
 assert(omni_travel_speed(1,0,OMNI_LAND)>omni_travel_speed(0,1,OMNI_LAND));
 assert(omni_travel_speed(1,0,OMNI_ROUGH|OMNI_LAND)==4);
 omni_travel_reset(&t,1,25,32,32);omni_travel_step(&t,32,32,OMNI_LAND,1);assert(t.visible);
 omni_travel_step(&t,48,32,OMNI_LAND,1);omni_travel_sample(&t,8);assert(t.x==40&&t.y==32&&t.walking);
 omni_travel_sample(&t,16);assert(t.x==48&&!t.walking);
 omni_travel_step(&t,48,48,OMNI_LAND,1);omni_travel_sample(&t,16);assert(t.x==48&&t.y==48&&t.face==0);
 omni_travel_step(&t,64,64,OMNI_LAND,1);assert(!t.visible);
 omni_travel_step(&t,64,64,OMNI_LAND,0);assert(!t.visible);
 omni_travel_step(&t,64,64,OMNI_WATER,1);assert(!t.visible);
 omni_travel_reset(&t,2,7,16,16);omni_travel_step(&t,16,16,OMNI_WATER,1);assert(!t.visible);
 omni_travel_reset(&t,3,999,16,16);omni_travel_step(&t,16,16,OMNI_LAND,1);assert(t.visible);
 return 0;
}
