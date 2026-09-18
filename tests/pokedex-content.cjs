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
assert.equal(catalog.entries.filter(e=>e.identity_evidence).length,100);
for(const e of catalog.entries.filter(e=>e.research_only))assert.equal(e.stats,null);
assert(byForm('dragonitemega').identity_evidence);
assert(byForm('dragonitemega').research_only,'Identity evidence must not approve reference stats');
assert.equal(byForm('rayquazamega').form_transition_reference.required_move,'Dragon Ascent');
assert.deepEqual(byForm('rayquazamega').required_items,[]);
assert.equal(byForm('urshifurapidstrikegmax').form_transition_reference.changes_from,'Urshifu-Rapid-Strike');
console.log('PASS: 34 evidenced Gmax records, 66 evidenced Mega records, cap classification, transition exceptions and evidence isolation');
