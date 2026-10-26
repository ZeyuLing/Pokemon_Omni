#ifndef OMNI_STAGE_H
#define OMNI_STAGE_H
#include <stdint.h>
/* Logical stage units: 16 units per tile, actor left edge and foot-tile bottom.
 * The GBA adapter maps one unit to one pixel; another view can map the same
 * route to its world coordinates. No framebuffer or hardware dependencies. */
typedef struct {int16_t x,y;} OmniWalkPoint;
typedef struct {const uint8_t *cells;uint16_t w,h;} OmniWalkGrid;
int omni_walk_clear(const OmniWalkGrid *,int x,int y);
/* Four-neighbour route through a caller-authored occupancy grid. Scratch needs
 * 2*w*h uint16_t entries; output uses the same foot coordinates as sampling.
 * Returns point count, or zero without emitting a partial route. */
unsigned omni_walk_plan(const OmniWalkGrid *,unsigned from_x,unsigned from_y,
                        unsigned to_x,unsigned to_y,OmniWalkPoint *,unsigned capacity,
                        uint16_t *scratch,unsigned scratch_entries);
/* Returns 0 at an invalid segment, retaining the last safe position. */
int omni_walk_sample(const OmniWalkGrid *,const OmniWalkPoint *,unsigned count,
                    unsigned ticks,unsigned duration,OmniWalkPoint *,uint8_t *face);
#endif
