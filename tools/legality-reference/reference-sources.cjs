'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {Dex,toID}=require('pokemon-showdown');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'research/catalog-sources');
function csv(text){let result=[],row=[],field='',quoted=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(field);field='';}else if(c==='\n'&&!quoted){row.push(field.replace(/\r$/,''));result.push(row);row=[];field='';}else field+=c;}if(field||row.length){row.push(field);result.push(row);}assert(!quoted);const header=result.shift();return result.map(r=>Object.fromEntries(header.map((h,i)=>[h,r[i]||''])));}
const manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
const tables={};for(const f of manifest.files){const bytes=fs.readFileSync(path.join(dir,f.file));assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),f.sha256);tables[f.file]=csv(bytes.toString('utf8').replace(/^\uFEFF/,''));}
const rows=name=>tables[name+'.csv'];
const pokemon=new Map(rows('pokemon').map(p=>[p.id,p]));
const species=new Map(rows('pokemon_species').map(p=>[+p.id,p]));
const statNames=['hp','atk','def','spa','spd','spe'];
const stats=new Map();for(const r of rows('pokemon_stats')){if(!stats.has(r.pokemon_id))stats.set(r.pokemon_id,{});stats.get(r.pokemon_id)[statNames[+r.stat_id-1]]=+r.base_stat;}
const typeOrder=['','Normal','Fighting','Flying','Poison','Ground','Rock','Bug','Ghost','Steel','Fire','Water','Grass','Electric','Psychic','Ice','Dragon','Dark','Fairy','Stellar'];
const types=new Map();for(const r of rows('pokemon_types')){if(!types.has(r.pokemon_id))types.set(r.pokemon_id,[]);types.get(r.pokemon_id)[+r.slot-1]=typeOrder[+r.type_id];}
const abilityById=new Map(rows('abilities').map(a=>[a.id,toID(a.identifier)]));
const abilityNumbers=new Map();for(const r of rows('pokemon_abilities')){if(!abilityNumbers.has(r.pokemon_id))abilityNumbers.set(r.pokemon_id,[]);abilityNumbers.get(r.pokemon_id).push(abilityById.get(r.ability_id));}
const formTypes=new Map();for(const r of rows('pokemon_form_types')){if(!formTypes.has(r.pokemon_form_id))formTypes.set(r.pokemon_form_id,[]);formTypes.get(r.pokemon_form_id)[+r.slot-1]=typeOrder[+r.type_id];}
const formNames=new Map(rows('pokemon_form_names').filter(r=>r.local_language_id==='12').map(r=>[r.pokemon_form_id,r.form_name]));
const itemNames=new Map(rows('item_names').filter(r=>r.local_language_id==='12').map(r=>[r.item_id,r.name]));
const items=Object.fromEntries(rows('items').map(r=>[toID(r.identifier),itemNames.get(r.id)||r.identifier]));
for(const r of rows('items'))if(/--held$/.test(r.identifier))items[toID(r.identifier.replace(/--held$/,''))]=itemNames.get(r.id)||r.identifier;
const aliases={
 'frillish-male':'frillish','jellicent-male':'jellicent','pyroar-male':'pyroar','indeedee-male':'indeedee','indeedee-female':'indeedeef','basculegion-male':'basculegion','basculegion-female':'basculegionf','oinkologne-male':'oinkologne','oinkologne-female':'oinkolognef',
 'minior-red-meteor':'miniormeteor','minior-red':'minior','maushold-family-of-four':'mausholdfour','maushold-family-of-three':'maushold',
 'raticate-totem-alola':'raticatealolatotem','zygarde-10-power-construct':'zygarde10','zygarde-50-power-construct':'zygarde',
 'mimikyu-totem-disguised':'mimikyutotem','mimikyu-totem-busted':'mimikyubustedtotem','marowak-totem':'marowakalolatotem','rockruff-own-tempo':'rockruffdusk',
 'darmanitan-galar-standard':'darmanitangalar','tauros-paldea-combat-breed':'taurospaldeacombat','tauros-paldea-blaze-breed':'taurospaldeablaze','tauros-paldea-aqua-breed':'taurospaldeaaqua','meowstic-male-mega':'meowsticmmega',
 'koraidon-apex-build':'koraidon','miraidon-ultimate-mode':'miraidon',
};
function resolve(identifier){
 let name=aliases[identifier]||identifier;
 if(/^pikachu-.*-cap$/.test(name))name=name.slice(0,-4);
 if(/^squawkabilly-.*-plumage$/.test(name))name=name.replace('-plumage','').replace('-green','');
 const s=Dex.species.get(name);return s.exists?s:null;
}
const audit=[];
function augment(entries){
 const represented=new Map(entries.filter(e=>e.category!=='rocket_bond_candidate').map(e=>[e.source_form_id||e.species_id?.slice(8),e]));
 for(const f of rows('pokemon_forms')){
  const p=pokemon.get(f.pokemon_id),n=+p.species_id;
  if(f.identifier==='arceus-unknown'){audit.push({form_id:+f.id,identifier:f.identifier,status:'excluded',reason:'Historical unused ??? type placeholder, not a obtainable form'});continue;}
  // These encode future evolution appearance, without a distinct current appearance/stat block.
  if(/^(mothim|scatterbug|spewpa)-/.test(f.identifier)){
   const parent=entries.find(e=>e.category==='base'&&e.national_number===n);
   if(!parent.pokeapi)parent.pokeapi={form_id:+f.id,pokemon_id:+p.id,identifier:f.identifier,form_identifier:f.form_identifier,stats:stats.get(p.id),height_m:+p.height/10,weight_kg:+p.weight/10,battle_only:false};
   (parent.inherited_appearance_variants??=[]).push({identifier:f.identifier,pokeapi_form_id:+f.id});
   audit.push({form_id:+f.id,identifier:f.identifier,status:'represented_as_metadata',entry_id:parent.entry_id});continue;
  }
  let s=resolve(f.identifier),e=s&&represented.get(s.id);
  // Alcremie requires cream AND sweet; old cream entries are the strawberry variants.
  if(n===869&&f.identifier!=='alcremie-gmax'){
   const cream=f.identifier.replace(/^alcremie-/,'').replace(/-(strawberry|berry|love|star|clover|flower|ribbon)-sweet$/,'');
   s=Dex.species.get(cream==='vanilla-cream'?'alcremie':'alcremie-'+cream);
   e=f.identifier.endsWith('-strawberry-sweet')&&s.exists?represented.get(s.id):null;
   if(!s.exists)s=Dex.species.get('alcremie');
  }
  if(!e){
   const base=Dex.species.get(species.get(n).identifier);
   const parent=/^minior-.*-meteor$/.test(p.identifier)?Dex.species.get('miniormeteor'):resolve(p.identifier)||base;
   const fallback=s||parent;
   e={entry_id:`dex:appearance:${f.identifier}`,species_id:`pokemon:${base.id}`,national_number:n,name_reference:f.identifier,source_form_id:fallback.id,
    category:f.is_mega==='1'?'mega':f.is_battle_only==='1'?'battle_state':'cosmetic',evidence_status:'pinned_pokeapi_form_identity',production_ready:false,
    supplemental:true,sprite_id_override:null};
   entries.push(e);
  }
  (e.pokeapi_form_ids??=[]).push(+f.id);
  // The first row is the canonical display; alternative ability encodings stay metadata.
  if(!e.pokeapi){e.pokeapi={form_id:+f.id,pokemon_id:+p.id,identifier:f.identifier,form_identifier:f.form_identifier,stats:stats.get(p.id),height_m:+p.height/10,weight_kg:+p.weight/10,battle_only:f.is_battle_only==='1'};e.form_name_zh=formNames.get(f.id)||null;}
  audit.push({form_id:+f.id,identifier:f.identifier,status:'represented',entry_id:e.entry_id});
 }
 return entries;
}
module.exports={augment,audit,rows,resolve,stats,types,formTypes,abilityNumbers,pokemon,species,items,formNames};
