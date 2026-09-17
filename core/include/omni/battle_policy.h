#ifndef OMNI_BATTLE_POLICY_H
#define OMNI_BATTLE_POLICY_H
#include <stddef.h>
#include <stdint.h>

#define OMNI_PARTY_SIZE 6
#define OMNI_MOVE_SLOTS 4
#define OMNI_GIMMICK_COUNT 5
#define OMNI_POLICY_VERSION 1

typedef enum { OMNI_EASY, OMNI_HARD, OMNI_INSANE } OmniDifficulty;
typedef enum { OMNI_PLAYER, OMNI_NPC } OmniSide;
typedef enum { OMNI_MEGA, OMNI_DYNAMAX, OMNI_Z_MOVE, OMNI_TERA, OMNI_BOND } OmniGimmick;
typedef enum { OMNI_FORM_BASE, OMNI_FORM_TEMPORARY, OMNI_FORM_PERMANENT_MEGA } OmniFormKind;
typedef enum {
    OMNI_OK, OMNI_BAD_ARGUMENT, OMNI_INVALID_DATA, OMNI_DATA_UNAVAILABLE,
    OMNI_CAPTURE_LOCKED, OMNI_LEVEL_CAPPED, OMNI_ILLEGAL_BUILD,
    OMNI_PLAYER_PERMANENT_MEGA, OMNI_NPC_PRIVILEGE_DENIED,
    OMNI_NO_BATTLER, OMNI_STORAGE_FULL, OMNI_STORAGE_CONFLICT,
    OMNI_QUOTA_SPENT, OMNI_MECHANIC_INCOMPATIBLE
} OmniCode;

/* Persisted domain data, NOT a byte-for-byte save format. Never serialize this struct. */
typedef struct {
    uint32_t instance_id;
    uint16_t species, ability, item, source_id;
    uint16_t moves[OMNI_MOVE_SLOTS], evs[6];
    uint8_t ivs[6], pp[OMNI_MOVE_SLOTS], pp_ups[OMNI_MOVE_SLOTS];
    uint8_t level, nature, gender, shiny, egg, fainted;
} OmniMon;

typedef struct { uint16_t id; uint8_t base_pp; } OmniMove;
typedef struct { uint16_t id; uint8_t minimum_level; } OmniLearnable;
/* Each route describes a mutually compatible complete acquisition/build path.
 * A move union across routes is NOT sufficient to validate a set. */
typedef struct {
    uint16_t source_id, abilities[3], capture_gate;
    uint32_t nature_mask;
    uint8_t minimum_level, gender_mask, shiny_rule; /* shiny: 0 any, 1 yes, 2 no */
    const OmniLearnable *moves;
    uint16_t move_count;
} OmniRoute;
typedef struct {
    uint16_t id, capture_gate;
    uint8_t form_kind, data_complete;
    const OmniRoute *routes;
    uint16_t route_count;
    uint8_t gimmick_mask; /* Known species/form eligibility, not item or turn eligibility. */
} OmniSpecies;
typedef struct {
    uint32_t content_version;
    const OmniSpecies *species;
    uint16_t species_count;
    const OmniMove *moves;
    uint16_t move_count;
    const uint16_t *items;
    uint16_t item_count;
} OmniCatalog;
typedef struct {
    OmniDifficulty difficulty;
    OmniSide side;
    uint8_t level_cap, allow_permanent_mega;
    uint32_t content_version;
    const uint16_t *unlocked_capture_gates;
    uint16_t unlocked_count;
} OmniValidationContext;
typedef struct { OmniCode code; uint8_t slot; } OmniIssue;
typedef struct {
    OmniIssue issues[OMNI_PARTY_SIZE];
    uint8_t issue_count, quarantine_mask, ready;
} OmniReport;

OmniCode omni_catalog_validate(const OmniCatalog *catalog);
OmniCode omni_validate_mon(const OmniCatalog *, const OmniValidationContext *, const OmniMon *);
OmniReport omni_validate_party(const OmniCatalog *, const OmniValidationContext *, const OmniMon *, uint8_t count);
/* The only mutation API here: caller runs game-save transaction around successful output.
 * Checks all capacity and identity constraints BEFORE touching memory. No release/deletion. */
OmniCode omni_quarantine(OmniMon *party, uint8_t *party_count, OmniMon *storage,
    uint16_t *storage_count, uint16_t storage_capacity, const OmniCatalog *, const OmniValidationContext *);

uint8_t omni_party_highest_level(const OmniMon *party, uint8_t count);
OmniCode omni_npc_level(OmniDifficulty difficulty, uint8_t authored_level,
    uint8_t progress_level, uint8_t party_highest, uint8_t gym_cap,
    uint8_t audited_low_level_exception, uint8_t *out_level);

typedef enum { OMNI_IGNORE, OMNI_AUTO_CHALLENGE, OMNI_ASK_REMATCH, OMNI_START_REMATCH } OmniEncounterAction;
OmniEncounterAction omni_encounter_action(uint8_t battle_started_before, uint8_t in_sight,
    uint8_t interacted, uint8_t confirmed);

typedef struct { uint8_t used[2][OMNI_GIMMICK_COUNT]; } OmniMechanicBudget;
/* Call on successful activation commit, never when merely previewing a menu. */
OmniCode omni_commit_gimmick(OmniMechanicBudget *, OmniDifficulty, OmniSide,
    OmniGimmick, uint8_t permanent_mega, uint8_t species_eligible,
    uint8_t item_and_turn_eligible, uint8_t incompatible_form_active);
uint8_t omni_bag_allowed(OmniDifficulty, OmniSide);
const char *omni_code_name(OmniCode);
#endif
