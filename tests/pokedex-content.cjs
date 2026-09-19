'use strict';
const assert=require('node:assert/strict');
const catalog=require('../content/pokedex/catalog.json');
const evidence=require('../content/pokedex/official-form-evidence.json');
const byForm=id=>catalog.entries.find(e=>e.source_form_id===id&&e.category!=='dynamax');
const gmax=catalog.entries.filter(e=>e.category==='gigantamax');
assert.equal(gmax.length,34);
for(const e of gmax)assert(e.identity_evidence?.claims.includes('form_identity'));
assert.equal(byForm('toxtricitylowkeygmax').category,'gigantamax');
assert.equal(byForm('urshifurapidstrikegmax').category,'gigantamax');
assert.equal(byForm('pikachualola').category,'cosmetic');
assert(byForm('pikachualola').name_zh_hans.includes('之帽'));
for(const source of evidence.sources)for(const id of source.form_ids){
 const e=byForm(id);assert(e,`Missing evidenced form ${id}`);
 assert.equal(e.identity_evidence.url,source.url);
 assert.equal(e.battle_data_approved,false);
}
assert.equal(evidence.sources.find(s=>s.key==='mega_classic').form_ids.length,48);
assert.equal(evidence.sources.flatMap(s=>s.form_ids).length,131);
for(const e of catalog.entries.filter(e=>e.research_only))assert(e.author_evidence&&e.stats);
assert(byForm('dragonitemega').identity_evidence);
assert.equal(byForm('dragonitemega').stats_status,'two_reference_sources_agree');
assert.equal(byForm('dragonitemega').battle_data_approved,false,'Reference data must not approve project battle rules');
assert.equal(byForm('rayquazamega').form_transition_reference.required_move,'Dragon Ascent');
assert.deepEqual(byForm('rayquazamega').required_items,[]);
assert.equal(byForm('urshifurapidstrikegmax').form_transition_reference.changes_from,'Urshifu-Rapid-Strike');
const audit=require('../content/pokedex/form-source-audit.json');
const official=require('../content/pokedex/official-zukan-audit.json');
const coverage=require('../content/pokedex/coverage.json');
assert.equal(official.official_rows,1302);assert.equal(official.matched_rows,1302);assert.deepEqual(official.unmatched_rows,[]);
assert.equal(audit.records.length,1579);assert.equal(coverage.source_form_rows_accounted_for,1579);
const entries=new Map(catalog.entries.map(e=>[e.entry_id,e]));
for(const r of audit.records){assert(['represented','represented_as_metadata','excluded'].includes(r.status));if(r.entry_id)assert(entries.has(r.entry_id));else assert(r.reason);}
for(const [id,num] of Object.entries(require('./fixtures/pokedex-ids-v1.json'))){assert(entries.has(id),`Old entry removed: ${id}`);assert.equal(entries.get(id).numeric_id,num);}
assert.equal(coverage.alcremie_appearance_combinations,63);
assert.equal(catalog.entries.filter(e=>e.national_number===201&&e.category!=='dynamax').length,28);
assert.equal(catalog.entries.filter(e=>e.national_number===774&&e.category!=='dynamax').length,14);
assert.equal(catalog.entries.filter(e=>e.category==='other_form_review').length,0);
for(const e of catalog.entries){
 assert(e.stats&&Object.keys(e.stats).length===6,`Missing six stats ${e.entry_id}`);
 assert(Object.values(e.stats).every(n=>Number.isInteger(n)&&n>0&&n<=255));
 assert(e.types.length>0);assert(e.abilities.length>0);
 if(e.field_crosschecks){assert(e.field_crosschecks.stats,`Stats differ: ${e.entry_id}`);assert(e.field_crosschecks.types,`Types differ: ${e.entry_id}`);}
 for(const id of e.transition.parent_entry_ids)assert(entries.has(id));
 if(e.category==='dynamax'){const p=entries.get(e.source_entry_id);assert(p);assert.deepEqual(e.stats,p.stats);assert.equal(e.name_zh_hans,p.name_zh_hans+' · 极巨化');}
 if(!e.author_evidence)assert(!/[A-Za-z]{3}/.test(e.name_zh_hans),`Untranslated form: ${e.name_zh_hans}`);
}
const bonds=catalog.entries.filter(e=>e.author_evidence);assert.equal(bonds.length,23);assert(bonds.every(e=>e.research_only&&!e.battle_data_approved));
assert.equal(bonds.find(e=>e.entry_id.endsWith(':rhyperior')).reported_total,670);
assert.equal(Object.values(bonds.find(e=>e.entry_id.endsWith(':rhyperior')).stats).reduce((a,b)=>a+b),660);
assert.equal(catalog.announced.records.length,5);assert(catalog.announced.records.every(e=>e.stats===null));
assert.equal(byForm('garchompmegaz').abilities[0].id,'levitate');
assert.equal(byForm('lucariomegaz').abilities[0].id,'auraguard');
assert.equal(catalog.abilities.auraguard.reference_number,319);
console.log('PASS: complete pinned form inventories, official 1302-row reconciliation, six-stat/type comparisons, author bond contradictions, all previous IDs and transition links');

for(const id of ['ogerpontealtera','ogerponwellspringtera','ogerponhearthflametera','ogerponcornerstonetera']){assert.equal(byForm(id).art_reference.status,'official_game_screenshot');assert.equal(byForm(id).art_reference.front_http_status,200);}
for(const r of require('../content/pokedex/supplemental-art-reference.json').records){
 const e=r.entry_id?entries.get(r.entry_id):byForm(r.source_form_id);
 const art=e.art_reference.status==='rom_extracted'?e.alternative_art_references.find(a=>a.variants.front_default===r.url):e.art_reference;
 assert(art);assert.equal(art.variants.front_default,r.url);assert.equal(art.front_http_status,200);
 if(r.kind==='author_credited_artwork')assert(e.research_only&&art.creator&&art.credit_evidence);
}
for(const r of require('../assets/source/bond-concepts/manifest.json').records){
 const e=entries.get(r.entry_id),art=e.alternative_art_references.find(a=>a.status==='ai_original_concept');
 assert(art);assert(e.research_only&&!e.battle_data_approved&&art.not_source_game_appearance);
 assert.equal(art.sha256,r.sha256);
}
const rom=require('../content/bond/rom-reference.json');assert.equal(rom.records.length,23);
for(const r of rom.records){
 const e=entries.get(r.entry_id);assert.equal(e.art_reference.status,'rom_extracted');
 assert.equal(e.stats_status,'two_roms_agree');assert.deepEqual(e.stats,r.user_rom.stats);
 assert.deepEqual(e.types,r.user_rom.types);assert.equal(r.user_rom.species_record_sha256,r.author_rom.species_record_sha256);
 for(const k of ['front','back','normal_palette','shiny_palette'])assert.equal(r.user_rom.assets[k].decoded_sha256,r.author_rom.assets[k].decoded_sha256);
 assert.equal(Object.keys(e.art_reference.variants).length,4);assert(e.art_reference.normal_shiny_identical);
 assert(e.research_only&&!e.battle_data_approved);
}
assert.deepEqual(entries.get('dex:omni:rocket-bond:butterfree').types,['Bug','Psychic']);
assert.equal(entries.get('dex:omni:rocket-bond:volcarona').stats.spd,135);
assert.equal(entries.get('dex:omni:rocket-bond:volcarona').stats.spe,130);
assert.equal(coverage.rom_extracted_bond_art,23);
assert.equal(require('../content/pokedex/gaps.json').missing_artwork.length,0);
console.log('PASS: 23 ROM-verified bonds, original art replaces proposals, all 92 variant references, document discrepancies retained');
