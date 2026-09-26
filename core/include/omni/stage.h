#ifndef OMNI_STAGE_H
#define OMNI_STAGE_H
#include <stdint.h>
/* Logical stage units: 16 units per tile, actor left edge and foot-tile bottom.
 * The GBA adapter maps one unit to one pixel; another view can map the same
 * route to its world coordinates. No framebuffer or hardware dependencies. */
typedef struct {int16_t x,y;} OmniWalkPoint;
typedef struct {const uint8_t *cells;uint16_t w,h;} OmniWalkGrid;
int omni_walk_clear(const OmniWalkGrid *,int x,int y);
/* Returns 0 at an invalid segment, retaining the last safe position. */
int omni_walk_sample(const OmniWalkGrid *,const OmniWalkPoint *,unsigned count,
                    unsigned ticks,unsigned duration,OmniWalkPoint *,uint8_t *face);
#endif
