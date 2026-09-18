#ifndef OMNI_POKEDEX_H
#define OMNI_POKEDEX_H
#include <stddef.h>
#include <stdint.h>

/* A catalog is immutable ROM data; state is caller-owned RAM. No platform APIs. */
typedef struct {
    uint32_t id; /* Stable hashed symbolic entry ID; compiler rejects collisions. */
    const char *name_zh, *name_en;
    uint16_t national, type_mask, type_mask_hi;
    uint8_t category, generation, research_only, reserved;
} OmniDexEntry;
typedef struct { const OmniDexEntry *entries; uint16_t count; } OmniDex;

/* Read-only catalog references, not approved battle rules. Same index order as OmniDex. */
typedef struct {
    uint32_t id, parent_id;
    uint16_t stats[6]; /* HP, attack, defense, special attack, special defense, speed */
    uint16_t abilities[4]; /* normal 0/1, hidden H, special S; 0 means absent */
    uint8_t type1, type2, has_stats, author_reference;
} OmniDexProfile;
const OmniDexProfile *omni_dex_profile(const OmniDex *dex, const OmniDexProfile *profiles,
    uint16_t profile_count, uint32_t id);
typedef struct { uint8_t *flags; uint16_t count; } OmniDexState;
typedef struct {
    const char *text;
    uint16_t national;
    uint8_t category, generation, type, progress, include_research;
} OmniDexFilter;
enum { OMNI_DEX_SEEN=1, OMNI_DEX_REGISTERED=2, OMNI_DEX_UNLOCKED=4 };
enum { OMNI_DEX_OK, OMNI_DEX_ARGUMENT, OMNI_DEX_UNKNOWN, OMNI_DEX_RESEARCH,
       OMNI_DEX_CAPACITY, OMNI_DEX_BAD_SAVE, OMNI_DEX_DUPLICATE };

int omni_dex_validate(const OmniDex *dex);
int32_t omni_dex_find(const OmniDex *dex, uint32_t id);
int omni_dex_matches(const OmniDexEntry *entry, uint8_t flags, const OmniDexFilter *filter);
/* Returns full result count; writes at most capacity indices after offset. */
uint16_t omni_dex_query(const OmniDex *dex, const OmniDexState *state, const OmniDexFilter *filter,
    uint16_t offset, uint16_t *indices, uint16_t capacity);
int omni_dex_record(const OmniDex *dex, OmniDexState *state, uint32_t id, uint8_t event);
uint16_t omni_dex_count(const OmniDex *dex, const OmniDexState *state, uint8_t flag, uint8_t include_research);
/* Versioned little-endian save: stable IDs + flags + checksum. No struct dumps.
 * Import validates before any write, ignores removed IDs and retains newly added
 * entries at zero. Buffer must not alias state or immutable catalog memory. */
size_t omni_dex_save_size(const OmniDexState *state);
int omni_dex_save(const OmniDex *dex, const OmniDexState *state, uint8_t *out, size_t capacity, size_t *written);
int omni_dex_load(const OmniDex *dex, OmniDexState *state, const uint8_t *bytes, size_t length);
#endif
