/* Regression boundaries for a source ROM with incompatible ability numbering. */
const assert=require('node:assert/strict');
const catalog=require('../content/pokedex/catalog.json'),source=require('../content/source-variants/ultra-emerald-5.8.json');
const entries=new Map(catalog.entries.map(e=>[e.entry_id,e])),bySid=sid=>entries.get(`dex:omni:ultra58:${sid}`);
assert.equal(source.records.length,35);
assert.equal(catalog.entries.filter(e=>e.category==='source_variant').length,35);
for(const row of source.records){
 const e=bySid(row.source_sid);assert(e&&e.research_only&&!e.battle_data_approved&&!e.production_ready);
 assert.deepEqual(e.stats,row.stats);assert.deepEqual(e.types,row.types);
 assert.equal(e.source_rom_evidence.sha256,source.source_rom_sha256);
 for(const [i,a] of e.abilities.entries()){
  const ability=catalog.abilities[a.id];assert.equal(ability.source_ability_id,row.ability_ids[i]);
  assert.equal(ability.reference_number,0,'Do not treat hack ability IDs as official IDs');
 }
 assert.equal(Object.keys(e.art_reference.variants).length,4);
 assert.deepEqual(e.move_pool_ids,[],'Do not inherit unsupported official moves');
 for(const parent of e.transition.parent_entry_ids)assert(entries.has(parent));
}
assert.deepEqual(bySid(413).transition.parent_entry_ids,['dex:omni:ultra58:432']);
assert.deepEqual(bySid(1336).required_items_zh,['光之石']);
assert.deepEqual(bySid(1337).required_items_zh,['暗之石']);
assert.deepEqual(bySid(1383).required_items_zh,['光之石']);
assert.deepEqual(bySid(1384).required_items_zh,['火之石']);
assert.deepEqual(source.records.find(r=>r.source_sid===1383).ability_ids,[220,220,220]);
assert.equal(catalog.abilities.ue58_335.name_zh,'源特性 335（名称待核实）');
assert.equal(catalog.entries.filter(e=>e.category==='base').length,1025);
assert.equal(catalog.entries.filter(e=>e.category==='mega').length,97);
assert.equal(entries.get('dex:mewtwo:base').stats.atk,110,'Source balance changes must not overwrite official references');
const inventory=require('../content/source-variants/ultra-emerald-5.8-inventory.json');
assert.equal(inventory.records.length,1385);
for(const sid of [201,412,417,435,436,437,438,439,1386])assert(!bySid(sid),'Do not import placeholders as new forms');
console.log('PASS: 35 isolated source variants, 140 image references, explicit incoming evolutions, source-only abilities, no placeholder forms or official-data overwrite');
