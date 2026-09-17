'use strict';
// Identity inventory only. This does not approve battle stats or acquisition routes.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {Dex}=require('pokemon-showdown');
const localizationPath=path.resolve(__dirname,'../../content/pokedex/localization.zh-Hans.json');
const names=fs.existsSync(localizationPath)?JSON.parse(fs.readFileSync(localizationPath,'utf8')).species:{};
const ends=[151,251,386,493,649,721,809,905,1025];
const species=Dex.species.all().filter(s=>s.num>0 && s.num<=1025 && s.name===s.baseSpecies)
  .sort((a,b)=>a.num-b.num).map(s=>({id:`pokemon:${s.id}`,national_number:s.num,name_en:s.name,
    name_zh_hans:names[s.num]||null,introduced_generation:ends.findIndex(n=>s.num<=n)+1,
    scope:'included',data_status:names[s.num]?'localized_identity_rules_pending':'identity_imported_rules_and_localization_pending',
    acquisition_status:'unassigned',capture_gate_status:'unassigned'}));
assert.equal(species.length,1025);
assert.equal(new Set(species.map(s=>s.id)).size,1025);
species.forEach((s,i)=>assert.equal(s.national_number,i+1));
const output={schema_version:1,source:{package:'pokemon-showdown',version:'0.11.11',kind:'identity_reference_not_complete_game_catalog'},
  scope:'generation_1_to_9_national_species',forms_included:false,species};
const dest=path.resolve(__dirname,'../../content/species/national-index.json');
fs.mkdirSync(path.dirname(dest),{recursive:true});
fs.writeFileSync(dest,JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({species:species.length,generations:ends.map((n,i)=>({generation:i+1,count:n-(ends[i-1]||0)})),destination:dest},null,2));
