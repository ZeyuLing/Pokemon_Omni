#include "omni/battle_policy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(expr) do { ++checks; if (!(expr)) { fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); exit(1); } } while (0)
/* Artificial, explicitly non-production identities. Two exclusive routes test source compatibility. */
static const OmniMove moves[] = {{1, 10}, {2, 5}, {3, 20}, {4, 15}};
static const uint16_t items[] = {1, 2};
static const OmniLearnable basic[] = {{1, 1}, {2, 10}};
static const OmniLearnable event_a[] = {{1, 1}, {3, 1}};
static const OmniLearnable event_b[] = {{1, 1}, {4, 1}};
static const OmniRoute routes[] = {
    {1, {1, 2, 0}, 0, 0x1ffffff, 1, 7, 0, basic, 2},
    {2, {1, 0, 0}, 0, 1, 5, 1, 2, event_a, 2},
    {2, {1, 0, 0}, 0, 1, 5, 1, 2, event_b, 2}
};
static const OmniRoute gated_route[] = {{3, {1, 0, 0}, 9, 0x1ffffff, 1, 7, 0, basic, 2}};
static const OmniSpecies species[] = {
    {1, 0, OMNI_FORM_BASE, 1, routes, 3, 31},
    {2, 7, OMNI_FORM_BASE, 1, routes, 3, 31},
    {3, 0, OMNI_FORM_PERMANENT_MEGA, 1, routes, 3, 0},
    {4, 0, OMNI_FORM_TEMPORARY, 1, routes, 3, 0},
    {5, 0, OMNI_FORM_BASE, 0, NULL, 0, 0},
    {6, 0, OMNI_FORM_BASE, 1, gated_route, 1, 31}
};
static const OmniCatalog catalog = {1, species, 6, moves, 4, items, 2};
static OmniMon mon(void) {
    OmniMon m = {0};
    m.instance_id = 1; m.species = 1; m.ability = 1; m.source_id = 1;
    m.level = 20; m.moves[0] = 1; m.pp[0] = 10;
    return m;
}
static OmniValidationContext context(void) {
    OmniValidationContext v = {OMNI_HARD, OMNI_PLAYER, 50, 0, 1, NULL, 0}; return v;
}
static void legality(void) {
    OmniValidationContext v = context();
    OmniMon m = mon();
    OmniCatalog bad = catalog;
    uint16_t gates[] = {7, 9};
    CHECK(omni_catalog_validate(&catalog) == OMNI_OK);
    bad.species = NULL; CHECK(omni_catalog_validate(&bad) == OMNI_DATA_UNAVAILABLE);
    CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    m.evs[0] = 252; m.evs[1] = 252; m.evs[2] = 6;
    CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    m.evs[2] = 7; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_INVALID_DATA);
    m = mon(); m.evs[0] = 253; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_INVALID_DATA);
    m = mon(); m.ivs[4] = 32; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_INVALID_DATA);
    m = mon(); m.level = 101; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_INVALID_DATA);
    m = mon(); m.nature = 25; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_INVALID_DATA);
    m = mon(); m.ability = 3; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.item = 9; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.moves[0] = 4; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.moves[1] = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.moves[1] = 2; m.level = 9; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.moves[0] = 0; m.pp[0] = 0; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.pp[1] = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_INVALID_DATA);
    m = mon(); m.pp_ups[0] = 3; m.pp[0] = 16; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    m.pp[0] = 17; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_INVALID_DATA);
    m.pp[0] = 0; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    m.pp_ups[0] = 4; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.source_id = 2; m.moves[1] = 3; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    m.moves[2] = 4; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD); /* individually legal, incompatible together */
    m.moves[2] = 0; m.shiny = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m.shiny = 0; m.nature = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m.nature = 0; m.gender = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m = mon(); m.species = 2; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_CAPTURE_LOCKED);
    v.unlocked_capture_gates = gates; v.unlocked_count = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    m.species = 6; m.source_id = 3; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_CAPTURE_LOCKED);
    v.unlocked_count = 2; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    v = context(); v.difficulty = OMNI_EASY; m = mon(); m.species = 2; m.level = 100;
    CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    v.difficulty = OMNI_HARD; m.species = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_LEVEL_CAPPED);
    m = mon(); m.species = 3; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_PLAYER_PERMANENT_MEGA);
    v.side = OMNI_NPC; v.allow_permanent_mega = 1; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_NPC_PRIVILEGE_DENIED);
    v.difficulty = OMNI_INSANE; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    m.item = 2; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_OK);
    v.allow_permanent_mega = 0; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_NPC_PRIVILEGE_DENIED);
    m.species = 4; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_ILLEGAL_BUILD);
    m.species = 5; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_DATA_UNAVAILABLE);
    m.species = 99; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_DATA_UNAVAILABLE);
    m = mon(); v.content_version = 2; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_DATA_UNAVAILABLE);
    v = context(); v.difficulty = (OmniDifficulty)99; CHECK(omni_validate_mon(&catalog, &v, &m) == OMNI_BAD_ARGUMENT);
}
static void levels(void) {
    unsigned d, base, h;
    uint8_t out = 0;
    OmniMon party[6];
    for (d = 0; d < 3; ++d) for (base = 1; base <= 100; ++base) for (h = 1; h <= 100; ++h) {
        unsigned expected = base;
        if (d && h > base) expected = h == 100 ? 100 : h + 1;
        CHECK(omni_npc_level((OmniDifficulty)d, (uint8_t)base, (uint8_t)base, (uint8_t)h, 0, 0, &out) == OMNI_OK);
        CHECK(out == expected);
    }
    CHECK(omni_npc_level(OMNI_HARD, 15, 25, 24, 30, 0, &out) == OMNI_OK && out == 30);
    CHECK(omni_npc_level(OMNI_EASY, 15, 25, 99, 30, 0, &out) == OMNI_OK && out == 25);
    CHECK(omni_npc_level(OMNI_INSANE, 1, 25, 50, 30, 1, &out) == OMNI_OK && out == 1);
    CHECK(omni_npc_level(OMNI_HARD, 0, 25, 50, 30, 0, &out) == OMNI_BAD_ARGUMENT);
    for (d = 0; d < 6; ++d) { party[d] = mon(); party[d].instance_id = d + 1; }
    party[5].level = 80; party[5].fainted = 1;
    CHECK(omni_party_highest_level(party, 6) == 80); /* bench AND fainted included */
    party[5].egg = 1; CHECK(omni_party_highest_level(party, 6) == 20);
    CHECK(omni_party_highest_level(party, 7) == 0);
}
static void storage(void) {
    OmniValidationContext v = context();
    OmniMon party[6] = {{0}}, pc[4] = {{0}}, before[6], pc_before[4];
    OmniReport report;
    uint8_t n = 2;
    uint16_t stored = 0;
    party[0] = mon(); party[1] = mon(); party[1].instance_id = 2; party[1].species = 2;
    report = omni_validate_party(&catalog, &v, party, n);
    CHECK(!report.ready && report.quarantine_mask == 2 && report.issues[0].slot == 1);
    memcpy(before, party, sizeof(party)); memcpy(pc_before, pc, sizeof(pc));
    CHECK(omni_quarantine(party, &n, pc, &stored, 0, &catalog, &v) == OMNI_STORAGE_FULL);
    CHECK(n == 2 && !stored && !memcmp(before, party, sizeof(party)) && !memcmp(pc_before, pc, sizeof(pc)));
    CHECK(omni_quarantine(party, &n, pc, &stored, 4, &catalog, &v) == OMNI_OK);
    CHECK(n == 1 && stored == 1 && pc[0].instance_id == 2 && !memcmp(&pc[0], &before[1], sizeof(OmniMon)));
    CHECK(omni_validate_party(&catalog, &v, party, n).ready);
    CHECK(omni_quarantine(party, &n, pc, &stored, 4, &catalog, &v) == OMNI_OK && stored == 1);
    party[0] = pc[0]; /* illegally pulled locked mon back out; gate catches it again */
    CHECK(omni_validate_party(&catalog, &v, party, 1).quarantine_mask == 1);
    CHECK(omni_quarantine(party, &n, pc, &stored, 4, &catalog, &v) == OMNI_STORAGE_CONFLICT);
    party[0] = mon(); party[0].species = 99;
    CHECK(!omni_validate_party(&catalog, &v, party, 1).quarantine_mask);
    CHECK(omni_quarantine(party, &n, pc, &stored, 4, &catalog, &v) == OMNI_DATA_UNAVAILABLE);
    party[0] = mon(); party[0].level = 60; CHECK(!omni_validate_party(&catalog, &v, party, 1).quarantine_mask);
    party[0] = mon(); party[0].fainted = 1; CHECK(omni_validate_party(&catalog, &v, party, 1).issues[0].code == OMNI_NO_BATTLER);
    party[0] = mon(); party[1] = mon(); CHECK(omni_validate_party(&catalog, &v, party, 2).issues[0].code == OMNI_INVALID_DATA);
    party[0] = mon(); party[0].species = 2; party[0].instance_id = 10;
    CHECK(omni_quarantine(party, &n, pc, &stored, 4, &catalog, &v) == OMNI_OK && n == 0 && stored == 2);
    CHECK(!omni_validate_party(&catalog, &v, party, n).ready);
}
static void mechanics(void) {
    OmniMechanicBudget b = {{{0}}};
    unsigned i;
    for (i = 0; i < OMNI_GIMMICK_COUNT; ++i) {
        CHECK(omni_commit_gimmick(&b, OMNI_HARD, OMNI_PLAYER, (OmniGimmick)i, 0, 1, 1, 0) == OMNI_OK);
        CHECK(omni_commit_gimmick(&b, OMNI_HARD, OMNI_PLAYER, (OmniGimmick)i, 0, 1, 1, 0) == OMNI_QUOTA_SPENT);
        CHECK(omni_commit_gimmick(&b, OMNI_HARD, OMNI_NPC, (OmniGimmick)i, 0, 1, 1, 0) == OMNI_OK);
    }
    for (i = 0; i < 300; ++i) CHECK(omni_commit_gimmick(&b, OMNI_EASY, OMNI_PLAYER, OMNI_Z_MOVE, 0, 1, 1, 0) == OMNI_OK);
    b = (OmniMechanicBudget){{{0}}};
    CHECK(omni_commit_gimmick(&b, OMNI_INSANE, OMNI_NPC, OMNI_TERA, 1, 1, 1, 0) == OMNI_MECHANIC_INCOMPATIBLE);
    CHECK(!b.used[OMNI_NPC][OMNI_TERA] && !b.used[OMNI_NPC][OMNI_MEGA]);
    CHECK(omni_commit_gimmick(&b, OMNI_INSANE, OMNI_NPC, OMNI_MEGA, 0, 1, 1, 0) == OMNI_OK);
    CHECK(omni_commit_gimmick(&b, OMNI_EASY, OMNI_PLAYER, OMNI_MEGA, 0, 1, 1, 1) == OMNI_MECHANIC_INCOMPATIBLE);
    CHECK(omni_commit_gimmick(&b, OMNI_HARD, OMNI_PLAYER, OMNI_MEGA, 0, 1, 0, 0) == OMNI_MECHANIC_INCOMPATIBLE);
    CHECK(!b.used[OMNI_PLAYER][OMNI_MEGA]);
    CHECK(omni_bag_allowed(OMNI_EASY, OMNI_PLAYER));
    CHECK(!omni_bag_allowed(OMNI_HARD, OMNI_PLAYER) && !omni_bag_allowed(OMNI_INSANE, OMNI_NPC));
    CHECK(omni_encounter_action(0, 1, 0, 0) == OMNI_AUTO_CHALLENGE);
    CHECK(omni_encounter_action(1, 1, 0, 0) == OMNI_IGNORE);
    CHECK(omni_encounter_action(1, 0, 1, 0) == OMNI_ASK_REMATCH);
    CHECK(omni_encounter_action(1, 0, 1, 1) == OMNI_START_REMATCH);
    CHECK(omni_encounter_action(1, 0, 0, 1) == OMNI_IGNORE);
}
int main(void) {
    legality(); levels(); storage(); mechanics();
    printf("PASS: %u checks (includes exhaustive 3 x 100 x 100 level matrix).\n", checks);
    return 0;
}
