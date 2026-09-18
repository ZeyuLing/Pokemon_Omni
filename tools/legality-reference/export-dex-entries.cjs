'use strict';
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {Dex}=require('pokemon-showdown');
const root=path.resolve(__dirname,'../..');
const national=JSON.parse(fs.readFileSync(path.join(root,'content/species/national-index.json'),'utf8'));
const bonds=JSON.parse(fs.readFileSync(path.join(root,'content/bond/rocket-2.1-roster.json'),'utf8'));
const baseIds=new Map(national.species.map(s=>[s.national_number,s.id]));
const entries=national.species.map(s=>({entry_id:`dex:${s.id.slice(8)}:base`,species_id:s.id,national_number:s.national_number,
  name_reference:s.name_en,name_zh_hans:s.name_zh_hans,category:'base',catalog_presentation:'standalone_entry',
  evidence_status:'pinned_reference_identity',production_ready:false,registration_rule:'pending_acquisition_design'}));
function category(s) {
  if (s.isMega) return 'mega';
  if (s.forme.endsWith('Gmax')) return 'gigantamax';
  if (s.baseSpecies==='Pikachu' && ['Original','Hoenn','Sinnoh','Unova','Kalos','Alola','Partner','World'].includes(s.forme)) return 'cosmetic';
  if (s.forme==='Primal') return 'primal_reversion';
  if (s.name==='Necrozma-Ultra') return 'ultra_burst';
  if (s.name.startsWith('Ogerpon-') && s.forme.endsWith('Tera') || s.name.startsWith('Terapagos-')) return 'tera_related';
  if (/^(Alola|Galar|Hisui|Paldea)(-|$)/.test(s.forme)) return 'regional';
  return 'other_form_review';
}
for(const s of Dex.species.all().filter(s=>s.num>0&&s.num<=1025&&s.name!==s.baseSpecies).sort((a,b)=>a.num-b.num||a.id.localeCompare(b.id,'en'))) {
  assert(baseIds.has(s.num));
  entries.push({entry_id:`dex:form:${s.id}`,species_id:baseIds.get(s.num),national_number:s.num,
    name_reference:s.name,name_zh_hans:null,category:category(s),catalog_presentation:'standalone_entry',
    source_form_id:s.id,source_nonstandard:s.isNonstandard||null,
    evidence_status:['Future','Custom'].includes(s.isNonstandard)?'upstream_flag_requires_independent_review':'pinned_reference_identity',
    production_ready:false,registration_rule:'pending_form_review'});
}
const aliases={'Crobat Protagonist':'Crobat','Crobat Andra':'Crobat','Flareon EN':'Flareon','Jolteon RAI':'Jolteon','Vaporeon SUI':'Vaporeon'};
for(const b of bonds.forms) {
  const s=Dex.species.get(aliases[b.name]||b.name);
  entries.push({entry_id:`dex:omni:rocket-bond:${b.name.toLowerCase().replace(/[^a-z0-9]+/g,'-')}`,
    species_id:s.exists&&baseIds.has(s.num)?baseIds.get(s.num):null,national_number:s.exists?s.num:null,
    name_reference:`${b.name} [Rocket bond candidate]`,name_zh_hans:null,category:'rocket_bond_candidate',
    catalog_presentation:'standalone_entry',evidence_status:b.evidence,production_ready:false,
    registration_rule:'pending_rocket_2_1_verification'});
}
assert.equal(new Set(entries.map(e=>e.entry_id)).size,entries.length);
for(const e of entries) if(e.species_id) assert.equal(baseIds.get(e.national_number),e.species_id);
for(const id of ['charizardmegax','charizardmegay','charizardgmax','groudonprimal','necrozmaultra']) assert(entries.some(e=>e.source_form_id===id));
assert.equal(entries.filter(e=>e.category==='rocket_bond_candidate').length,23);
const counts={};for(const e of entries) counts[e.category]=(counts[e.category]||0)+1;
const output={schema_version:1,status:'identity_inventory_not_complete_or_playable_pokedex',
  source:{package:'pokemon-showdown',version:'0.11.11',bond_roster:'content/bond/rocket-2.1-roster.json'},
  notice:'Counts describe this reference snapshot, not verified official totals. Future/Custom flags are upstream format labels, not release-date evidence. Stats, assets, cosmetic combinations and dynamic mechanic entries are not complete.',
  category_counts:counts,entries};
const dest=path.join(root,'content/pokedex/entries.json');fs.mkdirSync(path.dirname(dest),{recursive:true});
fs.writeFileSync(dest,JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({total_identity_records:entries.length,category_counts:counts,checks:'unique entry IDs, valid parent references, representative special forms and bond mapping passed'},null,2));
