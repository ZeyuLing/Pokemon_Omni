#include "omni/battle_policy.h"

static int difficulty_valid(OmniDifficulty d) { return d >= OMNI_EASY && d <= OMNI_INSANE; }
static int side_valid(OmniSide s) { return s == OMNI_PLAYER || s == OMNI_NPC; }
static const OmniSpecies *species_find(const OmniCatalog *c, uint16_t id) {
    uint16_t i;
    for (i = 0; i < c->species_count; ++i) if (c->species[i].id == id) return &c->species[i];
    return NULL;
}
static const OmniMove *move_find(const OmniCatalog *c, uint16_t id) {
    uint16_t i;
    for (i = 0; i < c->move_count; ++i) if (c->moves[i].id == id) return &c->moves[i];
    return NULL;
}
static int has_id(const uint16_t *ids, uint16_t count, uint16_t id) {
    uint16_t i;
    if (!id) return 1;
    for (i = 0; i < count; ++i) if (ids[i] == id) return 1;
    return 0;
}
static int catalog_shape(const OmniCatalog *c) {
    return c && c->content_version && c->species && c->species_count && c->moves && c->move_count
        && (!c->item_count || c->items);
}
OmniCode omni_catalog_validate(const OmniCatalog *c) {
    uint16_t i, j, k, l;
    if (!catalog_shape(c)) return OMNI_DATA_UNAVAILABLE;
    for (i = 0; i < c->move_count; ++i) {
        if (!c->moves[i].id || !c->moves[i].base_pp || c->moves[i].base_pp > 63) return OMNI_INVALID_DATA;
        for (j = 0; j < i; ++j) if (c->moves[i].id == c->moves[j].id) return OMNI_INVALID_DATA;
    }
    for (i = 0; i < c->item_count; ++i) {
        if (!c->items[i]) return OMNI_INVALID_DATA;
        for (j = 0; j < i; ++j) if (c->items[i] == c->items[j]) return OMNI_INVALID_DATA;
    }
    for (i = 0; i < c->species_count; ++i) {
        const OmniSpecies *s = &c->species[i];
        if (!s->id || s->form_kind > OMNI_FORM_PERMANENT_MEGA || s->data_complete > 1
            || s->gimmick_mask > 31 || (s->route_count && !s->routes)
            || (s->data_complete && !s->route_count)) return OMNI_INVALID_DATA;
        for (j = 0; j < i; ++j) if (s->id == c->species[j].id) return OMNI_INVALID_DATA;
        for (j = 0; j < s->route_count; ++j) {
            const OmniRoute *r = &s->routes[j];
            if (!r->source_id || !r->abilities[0] || !r->minimum_level || r->minimum_level > 100
                || !r->nature_mask || (r->nature_mask >> 25) || !r->gender_mask || r->gender_mask > 7
                || r->shiny_rule > 2 || !r->moves || !r->move_count) return OMNI_INVALID_DATA;
            for (k = 0; k < r->move_count; ++k) {
                if (!move_find(c, r->moves[k].id) || !r->moves[k].minimum_level || r->moves[k].minimum_level > 100)
                    return OMNI_INVALID_DATA;
                for (l = 0; l < k; ++l) if (r->moves[l].id == r->moves[k].id) return OMNI_INVALID_DATA;
            }
        }
    }
    return OMNI_OK;
}
static int context_valid(const OmniValidationContext *v) {
    return v && difficulty_valid(v->difficulty) && side_valid(v->side)
        && v->allow_permanent_mega <= 1 && v->level_cap >= 1 && v->level_cap <= 100
        && (!v->unlocked_count || v->unlocked_capture_gates);
}
OmniCode omni_validate_mon(const OmniCatalog *c, const OmniValidationContext *v, const OmniMon *m) {
    const OmniSpecies *s;
    uint32_t ev_total = 0;
    uint16_t rindex, j;
    uint8_t i, k, move_count = 0, route_locked = 0;
    if (!context_valid(v) || !m) return OMNI_BAD_ARGUMENT;
    if (!catalog_shape(c) || c->content_version != v->content_version) return OMNI_DATA_UNAVAILABLE;
    if (!m->instance_id || m->level < 1 || m->level > 100 || m->nature >= 25 || m->gender > 2
        || m->shiny > 1 || m->egg > 1 || m->fainted > 1 || !m->ability) return OMNI_INVALID_DATA;
    s = species_find(c, m->species);
    /* An unknown species might belong to a newer content pack: no accusation or auto-quarantine. */
    if (!s || !s->data_complete || !s->routes || !s->route_count) return OMNI_DATA_UNAVAILABLE;
    if (s->form_kind == OMNI_FORM_TEMPORARY) return OMNI_ILLEGAL_BUILD;
    if (s->form_kind == OMNI_FORM_PERMANENT_MEGA) {
        if (v->side == OMNI_PLAYER) return OMNI_PLAYER_PERMANENT_MEGA;
        if (v->difficulty != OMNI_INSANE || !v->allow_permanent_mega) return OMNI_NPC_PRIVILEGE_DENIED;
    }
    if (!has_id(c->items, c->item_count, m->item)) return OMNI_ILLEGAL_BUILD;
    for (i = 0; i < 6; ++i) {
        if (m->ivs[i] > 31 || m->evs[i] > 252) return OMNI_INVALID_DATA;
        ev_total += m->evs[i];
    }
    if (ev_total > 510) return OMNI_INVALID_DATA;
    for (i = 0; i < OMNI_MOVE_SLOTS; ++i) {
        const OmniMove *move;
        uint16_t max_pp;
        if (!m->moves[i]) {
            if (m->pp[i] || m->pp_ups[i]) return OMNI_INVALID_DATA;
            continue;
        }
        move = move_find(c, m->moves[i]);
        if (!move || m->pp_ups[i] > 3) return OMNI_ILLEGAL_BUILD;
        max_pp = (uint16_t)(move->base_pp * (5 + m->pp_ups[i]) / 5);
        if (m->pp[i] > max_pp) return OMNI_INVALID_DATA;
        for (k = 0; k < i; ++k) if (m->moves[k] == m->moves[i]) return OMNI_ILLEGAL_BUILD;
        ++move_count;
    }
    if (!move_count) return OMNI_ILLEGAL_BUILD;
    if (v->side == OMNI_PLAYER && v->difficulty != OMNI_EASY && !m->egg
        && !has_id(v->unlocked_capture_gates, v->unlocked_count, s->capture_gate)) return OMNI_CAPTURE_LOCKED;
    /* Require one complete compatible route for ALL four moves and source constraints. */
    for (rindex = 0; rindex < s->route_count; ++rindex) {
        const OmniRoute *r = &s->routes[rindex];
        uint8_t fits = 1;
        if (r->source_id != m->source_id || m->level < r->minimum_level
            || !has_id(r->abilities, 3, m->ability) || !(r->nature_mask & (UINT32_C(1) << m->nature))
            || !(r->gender_mask & (1u << m->gender)) || (r->shiny_rule == 1 && !m->shiny)
            || (r->shiny_rule == 2 && m->shiny)) continue;
        for (i = 0; i < OMNI_MOVE_SLOTS; ++i) if (m->moves[i]) {
            uint8_t learned = 0;
            for (j = 0; j < r->move_count; ++j)
                if (r->moves[j].id == m->moves[i] && m->level >= r->moves[j].minimum_level) learned = 1;
            if (!learned) { fits = 0; break; }
        }
        if (!fits) continue;
        if (v->side == OMNI_PLAYER && v->difficulty != OMNI_EASY
            && !has_id(v->unlocked_capture_gates, v->unlocked_count, r->capture_gate)) { route_locked = 1; continue; }
        if (v->side == OMNI_PLAYER && v->difficulty != OMNI_EASY && !m->egg && m->level > v->level_cap)
            return OMNI_LEVEL_CAPPED;
        return OMNI_OK;
    }
    return route_locked ? OMNI_CAPTURE_LOCKED : OMNI_ILLEGAL_BUILD;
}
OmniReport omni_validate_party(const OmniCatalog *c, const OmniValidationContext *v, const OmniMon *party, uint8_t count) {
    OmniReport report = { {{OMNI_OK, 0}}, 0, 0, 0 };
    uint8_t i, j, usable = 0;
    if (!party || !count || count > OMNI_PARTY_SIZE || !context_valid(v)) {
        report.issues[0].code = OMNI_BAD_ARGUMENT; report.issue_count = 1; return report;
    }
    for (i = 0; i < count; ++i) {
        OmniCode code = omni_validate_mon(c, v, &party[i]);
        for (j = 0; j < i; ++j) if (party[i].instance_id && party[i].instance_id == party[j].instance_id) code = OMNI_INVALID_DATA;
        if (code != OMNI_OK) {
            report.issues[report.issue_count].slot = i;
            report.issues[report.issue_count++].code = code;
            /* Do not auto-store on stale/unknown content or level caps. */
            if (code != OMNI_DATA_UNAVAILABLE && code != OMNI_BAD_ARGUMENT && code != OMNI_LEVEL_CAPPED)
                report.quarantine_mask |= (uint8_t)(1u << i);
        } else if (!party[i].egg && !party[i].fainted) usable = 1;
    }
    if (!report.issue_count && !usable) {
        report.issues[0].code = OMNI_NO_BATTLER; report.issue_count = 1;
    }
    report.ready = (uint8_t)(!report.issue_count);
    return report;
}
OmniCode omni_quarantine(OmniMon *party, uint8_t *party_count, OmniMon *storage,
    uint16_t *storage_count, uint16_t capacity, const OmniCatalog *c, const OmniValidationContext *v) {
    OmniReport report;
    uint16_t i, j, needed = 0;
    uint8_t p, write = 0;
    if (!party || !party_count || !storage || !storage_count || *storage_count > capacity
        || !context_valid(v) || v->side != OMNI_PLAYER) return OMNI_BAD_ARGUMENT;
    report = omni_validate_party(c, v, party, *party_count);
    for (p = 0; p < report.issue_count; ++p)
        if (report.issues[p].code == OMNI_BAD_ARGUMENT || report.issues[p].code == OMNI_DATA_UNAVAILABLE)
            return report.issues[p].code;
    for (p = 0; p < *party_count; ++p) if (report.quarantine_mask & (1u << p)) ++needed;
    if (!needed) return OMNI_OK;
    if ((uint32_t)*storage_count + needed > capacity) return OMNI_STORAGE_FULL;
    /* Corrupt duplicate identities require recovery, never an ambiguous move/deletion. */
    for (p = 0; p < *party_count; ++p) {
        if (!party[p].instance_id) return OMNI_STORAGE_CONFLICT;
        for (i = 0; i < p; ++i) if (party[i].instance_id == party[p].instance_id) return OMNI_STORAGE_CONFLICT;
        for (i = 0; i < *storage_count; ++i) if (storage[i].instance_id == party[p].instance_id) return OMNI_STORAGE_CONFLICT;
    }
    for (i = 0; i < *storage_count; ++i) {
        if (!storage[i].instance_id) return OMNI_STORAGE_CONFLICT;
        for (j = 0; j < i; ++j) if (storage[i].instance_id == storage[j].instance_id) return OMNI_STORAGE_CONFLICT;
    }
    for (p = 0; p < *party_count; ++p) {
        if (report.quarantine_mask & (1u << p)) storage[(*storage_count)++] = party[p];
        else party[write++] = party[p];
    }
    for (p = write; p < *party_count; ++p) { OmniMon empty = {0}; party[p] = empty; }
    *party_count = write;
    return OMNI_OK;
}
uint8_t omni_party_highest_level(const OmniMon *party, uint8_t count) {
    uint8_t i, highest = 0;
    if (!party || !count || count > OMNI_PARTY_SIZE) return 0;
    for (i = 0; i < count; ++i) {
        if (!party[i].level || party[i].level > 100 || party[i].egg > 1) return 0;
        if (!party[i].egg && party[i].level > highest) highest = party[i].level;
    }
    return highest;
}
OmniCode omni_npc_level(OmniDifficulty d, uint8_t authored, uint8_t progress,
    uint8_t highest, uint8_t gym_cap, uint8_t exception, uint8_t *out) {
    uint16_t level;
    if (!difficulty_valid(d) || !out || !authored || authored > 100 || !progress || progress > 100
        || !highest || highest > 100 || gym_cap > 100 || exception > 1) return OMNI_BAD_ARGUMENT;
    level = authored > progress ? authored : progress;
    if (d != OMNI_EASY) {
        if (gym_cap > level) level = gym_cap;
        if (!exception && highest > level) level = (uint16_t)highest + 1;
        if (exception) level = authored; /* Explicit authored exception; audit in trainer data. */
    }
    *out = (uint8_t)(level > 100 ? 100 : level);
    return OMNI_OK;
}
OmniEncounterAction omni_encounter_action(uint8_t seen, uint8_t sight, uint8_t interacted, uint8_t confirmed) {
    if (seen > 1 || sight > 1 || interacted > 1 || confirmed > 1) return OMNI_IGNORE;
    if (!seen) return (sight || interacted) ? OMNI_AUTO_CHALLENGE : OMNI_IGNORE;
    if (!interacted) return OMNI_IGNORE;
    return confirmed ? OMNI_START_REMATCH : OMNI_ASK_REMATCH;
}
OmniCode omni_commit_gimmick(OmniMechanicBudget *b, OmniDifficulty d, OmniSide side,
    OmniGimmick g, uint8_t permanent, uint8_t eligible, uint8_t item_turn, uint8_t incompatible) {
    if (!b || !difficulty_valid(d) || !side_valid(side) || g < OMNI_MEGA || g > OMNI_BOND
        || permanent > 1 || eligible > 1 || item_turn > 1 || incompatible > 1) return OMNI_BAD_ARGUMENT;
    if (permanent || !eligible || !item_turn || incompatible) return OMNI_MECHANIC_INCOMPATIBLE;
    if (d == OMNI_EASY && side == OMNI_PLAYER) return OMNI_OK; /* Unlimited, no wrapping counter. */
    if (b->used[side][g]) return OMNI_QUOTA_SPENT;
    b->used[side][g] = 1;
    return OMNI_OK;
}
uint8_t omni_bag_allowed(OmniDifficulty d, OmniSide side) { return (uint8_t)(d == OMNI_EASY && side == OMNI_PLAYER); }
const char *omni_code_name(OmniCode code) {
    static const char *const names[] = {"ok", "bad_argument", "invalid_data", "data_unavailable",
        "capture_locked", "level_capped", "illegal_build", "player_permanent_mega", "npc_privilege_denied",
        "no_battler", "storage_full", "storage_conflict", "quota_spent", "mechanic_incompatible"};
    return (unsigned)code < sizeof(names) / sizeof(names[0]) ? names[code] : "unknown_error";
}
