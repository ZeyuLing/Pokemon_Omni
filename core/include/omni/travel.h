#ifndef OMNI_TRAVEL_H
#define OMNI_TRAVEL_H
#include <stdint.h>
enum { OMNI_LAND=1, OMNI_WATER=2, OMNI_INDOOR=4, OMNI_ROUGH=8 };
enum { OMNI_BODY_SMALL, OMNI_BODY_MEDIUM, OMNI_BODY_LARGE };
enum { OMNI_SUPPORT_NONE, OMNI_SUPPORT_BACK, OMNI_SUPPORT_SHELL };
enum { OMNI_TRAVEL_OK, OMNI_TRAVEL_UNKNOWN, OMNI_TRAVEL_SMALL,
 OMNI_TRAVEL_SUPPORT, OMNI_TRAVEL_CONTACT, OMNI_TRAVEL_TERRAIN, OMNI_TRAVEL_SPACE };
typedef struct {
 uint16_t species; uint8_t body,support,safe_contact,surfaces,clearance;
} OmniTravelProfile;
/* Authored anatomical capabilities, never inferred from elemental type alone. */
const OmniTravelProfile *omni_travel_profile(uint16_t species);
int omni_travel_ride(const OmniTravelProfile *,unsigned terrain,unsigned clearance);
unsigned omni_travel_speed(unsigned mounted,unsigned running,unsigned terrain);
/* One selected companion is owned by the party state. This transient view never
 * survives a warp/load; no stale route may cross a scene boundary. */
typedef struct {
 int16_t x,y,from_x,from_y,to_x,to_y;
 uint16_t location,species;uint8_t face,visible,mounted,walking;
} OmniTravel;
void omni_travel_reset(OmniTravel *,unsigned location,unsigned species,int x,int y);
void omni_travel_step(OmniTravel *,int old_x,int old_y,unsigned terrain,unsigned clear);
void omni_travel_sample(OmniTravel *,unsigned progress);
#endif
