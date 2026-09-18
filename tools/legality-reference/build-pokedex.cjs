'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {Dex,toID}=require('pokemon-showdown');
const root=path.resolve(__dirname,'../..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const write=(p,s)=>{fs.mkdirSync(path.dirname(path.join(root,p)),{recursive:true});fs.writeFileSync(path.join(root,p),s);};
const json=(p,o)=>write(p,JSON.stringify(o,null,2)+'\n');
const source=read('content/pokedex/entries.json');
const l=read('content/pokedex/localization.zh-Hans.json');
const reference=require('./reference-sources.cjs');
const rules=require('./catalog-rules.cjs');
const bondReference=read('content/bond/author-reference.json');
const championsReference=read('content/pokedex/champions-ability-reference.json');
const evidence=read('content/pokedex/official-form-evidence.json');
const officialForms=new Map();
for(const source of evidence.sources)for(const id of source.form_ids){
 assert(!officialForms.has(id),`Duplicate official form evidence: ${id}`);
 assert(Dex.species.get(id).exists,`Unknown official form ID: ${id}`);
 officialForms.set(id,{url:source.url,title:source.title,claims:source.claims,reviewed_at:evidence.reviewed_at});
}
const types=['Normal','Fire','Water','Electric','Grass','Ice','Fighting','Poison','Ground','Flying','Psychic','Bug','Rock','Ghost','Dragon','Dark','Steel','Fairy'];
const typeNames=['一般','火','水','电','草','冰','格斗','毒','地面','飞行','超能力','虫','岩石','幽灵','龙','恶','钢','妖精'];
const categories=['base','mega','gigantamax','regional','primal_reversion','ultra_burst','tera_related','other_form_review','rocket_bond_candidate','cosmetic','dynamax','battle_state','fusion','gender_form','size_form','type_form','special_form'];
const categoryNames=['普通形态','Mega 进化','超极巨化','地区形态','原始回归','究极爆发','太晶特殊形态','其他形态','羁绊形态','外观形态','极巨化','战斗状态','合体形态','性别形态','体型差异','属性形态','特殊形态'];
const suffixes={'Alola':'阿罗拉','Galar':'伽勒尔','Hisui':'洗翠','Paldea':'帕底亚','Mega':'超级进化','Mega-X':'超级进化 X','Mega-Y':'超级进化 Y','Mega-Z':'超级进化 Z','Gmax':'超极巨化','Primal':'原始回归','Ultra':'究极爆发','Ash':'小智版','Origin':'起源形态','Therian':'灵兽形态','Crowned':'剑盾之王','Complete':'完全体','Terastal':'太晶形态','Stellar':'星晶形态'};
for(const s of Dex.species.all().filter(s=>s.isMega))for(const item of s.requiredItems||[]){if(!reference.items[toID(item)]||/^[a-z]/i.test(reference.items[toID(item)]))reference.items[toID(item)]=(l.species[s.num]||s.baseSpecies)+'进化石'+(/ [XYZ]$/.test(item)?' '+item.slice(-1):'');}
let entries=source.entries.map(e=>({...e}));
const known=new Set(entries.map(e=>e.source_form_id||e.species_id?.slice(8)));
for(const s of Dex.species.all().filter(s=>s.num>0&&s.num<=1025)) for(const name of s.cosmeticFormes||[]) {
 const f=Dex.species.get(name);if(known.has(f.id))continue;known.add(f.id);
 entries.push({entry_id:`dex:cosmetic:${f.id}`,species_id:`pokemon:${Dex.species.get(s.baseSpecies).id}`,national_number:s.num,name_reference:name,source_form_id:f.id,category:'cosmetic',evidence_status:'pinned_reference_identity',production_ready:false});
}
reference.augment(entries);
for(const e of entries)if(e.category!=='rocket_bond_candidate')e.category=rules.category(e,Dex.species.get(e.source_form_id||e.name_reference));
const normal=entries.filter(e=>e.category==='base'||(e.category!=='rocket_bond_candidate'&&!e.pokeapi?.battle_only));
const dynamaxExcluded=[];
for(const e of normal) {
 const s=Dex.species.get(e.source_form_id||e.name_reference),ss=Dex.mod('gen8').species.get(s.id);
 // Official Sword/Shield rule does NOT establish eligibility for the whole National Dex.
 // Showdown is a secondary availability index, not an official per-species citation.
 if(!ss.exists||ss.isNonstandard||ss.battleOnly||s.isMega||ss.cannotDynamax||s.cannotDynamax||['zacian','zamazenta','eternatus'].includes(s.baseSpecies.toLowerCase())){
  dynamaxExcluded.push({species_id:e.species_id,reason:ss.cannotDynamax?'mechanic_forbidden':'outside_supported_swsh_reference_scope'});continue;
 }
 entries.push({entry_id:`${e.entry_id}:dynamax`,source_entry_id:e.entry_id,species_id:e.species_id,national_number:e.national_number,name_reference:`${s.name} [Dynamax]`,source_form_id:s.id,category:'dynamax',evidence_status:'official_general_rule_with_community_roster_crosscheck',production_ready:false,
  eligibility_evidence:{scope:'Pokemon Sword/Shield',official_rule:'https://swordshield.pokemon.com/en-us/gameplay/dynamaxing-max-moves/',official_compatibility_guidance:'https://support.pokemon.com/hc/en-us/articles/360039592832-How-can-I-tell-which-games-I-can-transfer-my-Pok%C3%A9mon-to-in-Pok%C3%A9mon-HOME',availability_reference:'pokemon-showdown@0.11.11 gen8',official_species_specific_verification:false}});
}
assert(!entries.some(e=>e.category==='dynamax'&&['weedle','kakuna','beedrill','sprigatito','zacian','zamazenta','eternatus'].includes(e.source_form_id)));
json('content/pokedex/dynamax-exclusions.json',{policy:'No speculative Dynamax entries for unsupported species. Exclusion is scoped to Sword/Shield, not a claim about every official game.',excluded:dynamaxExcluded});
const stableId=s=>{let h=2166136261;for(const b of Buffer.from(s))h=Math.imul(h^b,16777619)>>>0;return h;};
const bounds=[151,251,386,493,649,721,809,905,1025];
const moves={},abilities={},movePools={};
function pool(s,visited=new Set()) {
 if(!s?.exists||visited.has(s.id))return [];visited.add(s.id);
 const data=Dex.species.getLearnsetData(s.id);
 let result=[];
 if(data.learnset) {
  if(!movePools[s.id])movePools[s.id]=data.learnset;
  result.push(s.id);
 }
 if(s.prevo)result.push(...pool(Dex.species.get(s.prevo),visited));
 if(s.name!==s.baseSpecies)result.push(...pool(Dex.species.get(s.baseSpecies),visited));
 return [...new Set(result)];
}
for(const e of entries) {
 const isBond=e.category==='rocket_bond_candidate';
 const bond=isBond?bondReference.records.find(b=>e.name_reference===`${b.name} [Rocket bond candidate]`):null;
 const s=isBond?null:Dex.species.get(e.source_form_id||e.name_reference);
 const statsCrosschecked=e.pokeapi&&s&&Object.keys(s.baseStats).every(k=>s.baseStats[k]===e.pokeapi.stats[k]);
 const pending=isBond||e.evidence_status==='omni_eligibility_review'||((s?.isNonstandard==='Future'||s?.isNonstandard==='Custom')&&!statsCrosschecked);
 e.numeric_id=stableId(e.entry_id);e.category_id=categories.indexOf(e.category)+1;
 assert(e.category_id>0);e.generation=e.national_number?bounds.findIndex(n=>n>=e.national_number)+1:0;
 const baseName=l.species[e.national_number]||e.name_reference;
 e.name_zh_hans=isBond?`${baseName} · 羁绊${e.name_reference.includes('Andra')?'（Andra）':e.name_reference.includes('Protagonist')?'（主角）':''}`
  :e.category==='base'?baseName:e.category==='dynamax'?`${baseName} · 极巨化`:`${baseName} · ${suffixes[s.forme]||s.forme||s.name.replace(s.baseSpecies+'-','')}`;
 e.search_name_en=e.name_reference;e.research_only=pending;
 const namedForms={toxtricitygmax:'颤弦蝾螈 · 高调超极巨化',toxtricitylowkeygmax:'颤弦蝾螈 · 低调超极巨化',urshifugmax:'武道熊师 · 一击流超极巨化',urshifurapidstrikegmax:'武道熊师 · 连击流超极巨化',zaciancrowned:'苍响 · 剑之王',zamazentacrowned:'藏玛然特 · 盾之王'};
 if(e.category!=='dynamax'&&namedForms[s?.id])e.name_zh_hans=namedForms[s.id];
 const caps={Original:'初始',Hoenn:'丰缘',Sinnoh:'神奥',Unova:'合众',Kalos:'卡洛斯',Alola:'阿罗拉',Partner:'就决定是你了',World:'世界'};
 if(s?.baseSpecies==='Pikachu'&&caps[s.forme])e.name_zh_hans=`皮卡丘 · ${caps[s.forme]}之帽`;
 if(e.form_name_zh&&e.category!=='base'&&!['mega','gigantamax'].includes(e.category))e.name_zh_hans=`${baseName} · ${e.form_name_zh}`;
 if(!isBond&&e.category!=='dynamax')e.name_zh_hans=rules.label(e,s,baseName,Object.fromEntries(types.map((t,i)=>[t,typeNames[i]])));
 e.name_translation_source=e.form_name_zh?'PokeAPI Chinese form-name snapshot':'Project editorial label / species Chinese name';
 e.identity_evidence=e.category==='dynamax'?null:officialForms.get(s?.id)||null;
 e.identity_status=e.identity_evidence?'official_named_form':'reference_or_candidate';
 e.stats_status=pending?'pending_review':statsCrosschecked?'two_reference_sources_agree':'pinned_community_reference';
 e.reference_status=pending?'待核实':'参考数据';
 if(e.identity_evidence)e.reference_status=pending?'官方形态 · 数值待核验':'官方形态 · 参考数值';
 e.battle_data_approved=false;e.capture_gate_status='未配置';
 e.types=s&&!pending?s.types:[];
 e.stats=s&&!pending?s.baseStats:null;
 if(bond){
  e.stats=bond.stats;e.types=bond.types;e.stats_status='author_document_reference';
  e.reference_status='作者资料 · 版本待核对';
  e.author_evidence={url:bondReference.author_post,document:bondReference.document,document_sha256:bondReference.document_sha256,version_status:bondReference.version_status};
  e.source_issues=bond.source_issues;e.reported_total=bond.reported_total;
  if(bond.name==='Sacred Dragon Dun')e.name_zh_hans='神圣龙 · Dun 羁绊';
  for(const tag of [' EN',' RAI',' SUI'])if(bond.name.endsWith(tag))e.name_zh_hans+=`（${tag.trim()}）`;
 }
 e.height_m=s&&!pending?s.heightm:null;e.weight_kg=s&&!pending?s.weightkg:null;
 e.abilities=s&&!pending?Object.entries(s.abilities).map(([slot,n])=>({slot,id:toID(n)})):[];
 if(bond)e.abilities=[{slot:'0',id:toID(bond.ability)}];
 const champions=championsReference.records.find(r=>r.source_form_id===s?.id);
 if(champions){e.abilities=champions.abilities.map(({slot,id})=>({slot,id}));e.ability_evidence={source:championsReference.sources[0].url,commit:championsReference.commit,scope:championsReference.scope};}
 for(const a of e.abilities){const v=Dex.abilities.get(a.id);abilities[a.id]={name_en:v.name,name_zh:l.abilities[v.num]||v.name,reference_number:Math.max(0,v.num)};}
 if(champions)for(const a of champions.abilities)abilities[a.id]={name_en:a.name_en,name_zh:l.abilities[a.num]||a.name_en,reference_number:a.num};
 e.move_pool_ids=s&&!pending?pool(s):[];
 e.ability_status=bond?'author_document_reference':s?.isNonstandard==='Future'?(Dex.mod('champions').species.get(s.id).isNonstandard?'turn_based_adaptation_reference':'champions_reference'):'pinned_community_reference';
 if(champions)e.ability_status='champions_2026_09_reference';
 e.move_pool_status=isBond?'not_documented':s?.isNonstandard==='Future'?'base_species_reference_not_ZA_learnset':'cross_generation_reference';
 e.prevo=s?.prevo||null;e.evolutions=s?.evos||[];
 e.evolution_reference=s?{level:s.evoLevel||null,method:s.evoType||null,item:s.evoItem||null,move:s.evoMove||null,condition:s.evoCondition||null}:null;
 e.required_items=s?.requiredItems||[];
 e.required_items_zh=e.required_items.map(n=>reference.items[toID(n)]||n);
 e.stats_crosscheck=e.pokeapi?{source:'PokeAPI CSV SHA-256 snapshot',pokemon_id:e.pokeapi.pokemon_id,agrees:!!statsCrosschecked}:null;
 e.form_transition_reference=s&&!isBond?{source:'pokemon-showdown@0.11.11',changes_from:s.changesFrom||null,battle_only:s.battleOnly||null,required_move:s.requiredMove||null,required_items:e.required_items,project_rule_approved:false}:null;
 e.sprite_id=s&&!pending?s.spriteid:null;
 if(e.supplemental)e.sprite_id=e.sprite_id_override;
 e.registration_rule=e.category==='base'||e.category==='regional'||e.category==='cosmetic'?'见到可记录；获得或转换后登记':'见到可记录；实际激活或剧情确认后登记';
 e.mechanic_note=e.category==='dynamax'?'极巨化是《剑／盾》的战斗状态，不是专属超极巨化外形。资格依据：官方机制说明＋社区剑盾收录表交叉核对，尚非逐物种官方证明。下方像素图、种族值、身高体重均为基础形态参考，不能当作极巨化后的体型与实际 HP。':e.category==='rocket_bond_candidate'?'火箭队 2.1 候选；形态数值、触发条件与素材尚待作者资料核实。':pending?'名称已纳入研究目录；不展示未审定的战斗数值。':'属性和能力来自固定参考包；本项目战斗规则与获取路线另行审定。';
 if(bond)e.mechanic_note='属性、特性与六项数值来自作者发布包的羁绊说明文档；文档未标注 2.1，精确版本对应、招式表、触发条件及素材仍待核实。保留参考数值，暂不开放登记。';
 if(s?.isNonstandard==='Future'&&statsCrosschecked)e.mechanic_note='六项种族值已在固定 Showdown 与 PokeAPI 数据中逐项对照一致。Z-A 与传统回合制规则不同，所列特性仅是回合制适配参考，招式为基础物种参考；尚未批准为本项目战斗规则。';
 if(champions)e.mechanic_note='六项种族值已交叉核对；特性采用 2026 年 9 月 Champions M-C 的固定 Showdown 快照，覆盖旧包的临时适配值。招式仍为跨版本参考，本项目对战规则尚未审定。';
 e.presentation='standalone';
}
for(const e of entries.filter(e=>e.category==='dynamax')){const parent=entries.find(p=>p.entry_id===e.source_entry_id);e.name_zh_hans=parent.name_zh_hans+' · 极巨化';}
require('./finalize-catalog.cjs')({entries,reference,l,Dex,toID,root});
require('./official-zukan.cjs')({entries,reference,Dex,root});
json('content/pokedex/form-source-audit.json',{source:'PokeAPI CSV SHA-256 snapshot',records:reference.audit});
for(const p of Object.values(movePools))for(const id of Object.keys(p))if(!moves[id]) {
 const m=Dex.moves.get(id);moves[id]={name_en:m.name,name_zh:l.moves[m.num]||m.name,type:m.type,category:m.category,power:m.basePower,accuracy:m.accuracy,pp:m.pp};
}
entries.sort((a,b)=>(a.national_number||65535)-(b.national_number||65535)||a.category_id-b.category_id||a.entry_id.localeCompare(b.entry_id,'en'));
assert.equal(new Set(entries.map(e=>e.numeric_id)).size,entries.length,'hash collision');assert(!entries.some(e=>!e.numeric_id));
assert.equal(entries.filter(e=>e.category==='base').length,1025);
assert.equal(Object.keys(l.species).filter(n=>+n<=1025).length,1025);
const catalog={schema_version:2,reference:'pokemon-showdown@0.11.11',localization_source:'PokeAPI CSV commit + SHA-256 manifest',announced:read('content/pokedex/announced-pokemon.json'),types:types.map((id,i)=>({id,name:typeNames[i]})),categories:categories.map((id,i)=>({id,name:categoryNames[i]})),entries,moves,abilities,move_pools:movePools};
const digest=crypto.createHash('sha256').update(JSON.stringify(catalog)).digest('hex');catalog.content_sha256=digest;
json('content/pokedex/catalog.json',catalog);
const cstr=s=>JSON.stringify(s);
const rows=entries.map(e=>{let mask=0;for(const t of e.types)mask|=1<<types.indexOf(t);return `    {${e.numeric_id}u,${cstr(e.name_zh_hans)},${cstr(e.search_name_en)},${e.national_number||0},${mask&65535},${mask>>>16},${e.category_id},${e.generation},${e.research_only?1:0},0}`;});
const byEntryId=new Map(entries.map(e=>[e.entry_id,e]));
const profileRows=entries.map(e=>{
 const parent=byEntryId.get(e.transition?.parent_entry_ids[0]);
 const stats=['hp','atk','def','spa','spd','spe'].map(k=>e.stats?.[k]||0);
 const abilityNums=['0','1','H','S'].map(slot=>{const a=e.abilities.find(v=>v.slot===slot);return a?abilities[a.id].reference_number||Math.max(0,Dex.abilities.get(a.id).num):0;});
 return `    {${e.numeric_id}u,${parent?.numeric_id||0}u,{${stats.join(',')}},{${abilityNums.join(',')}},${e.types[0]?types.indexOf(e.types[0])+1:0},${e.types[1]?types.indexOf(e.types[1])+1:0},${e.stats?1:0},${e.author_evidence?1:0}}`;
});
write('content/pokedex/generated/catalog.c',`/* Generated by build-pokedex.cjs; do not edit. ${digest} */\n#include "catalog.h"\nstatic const OmniDexEntry entries[] = {\n${rows.join(',\n')}\n};\nconst OmniDex omni_pokedex_catalog = {entries,${entries.length}};\nconst OmniDexProfile omni_pokedex_profiles[] = {\n${profileRows.join(',\n')}\n};\n`);
write('content/pokedex/generated/catalog.h',`#ifndef OMNI_GENERATED_DEX_H\n#define OMNI_GENERATED_DEX_H\n#include "omni/pokedex.h"\n#define OMNI_CATALOG_ENTRY_COUNT ${entries.length}\nextern const OmniDex omni_pokedex_catalog;\nextern const OmniDexProfile omni_pokedex_profiles[OMNI_CATALOG_ENTRY_COUNT];\n#endif\n`);
const counts={};for(const e of entries)counts[e.category]=(counts[e.category]||0)+1;
const report=require('./catalog-coverage.cjs')({entries,reference,digest,categories});
json('content/pokedex/coverage.json',report.coverage);json('content/pokedex/gaps.json',report.gaps);
console.log(JSON.stringify({entries:entries.length,counts,move_pools:Object.keys(movePools).length,localized_species:1025,digest},null,2));
