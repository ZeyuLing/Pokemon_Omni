'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {Dex,TeamValidator,toID}=require('pokemon-showdown');
const root=path.resolve(__dirname,'../..'),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const catalog=read('content/pokedex/catalog.json'),sources=read('research/competitive-sources/manifest.json'),local=read('content/pokedex/localization.zh-Hans.json');
const ref=require('./reference-sources.cjs');
const natures=['Hardy','Lonely','Brave','Adamant','Naughty','Bold','Docile','Relaxed','Impish','Lax','Timid','Hasty','Serious','Jolly','Naive','Modest','Mild','Quiet','Bashful','Rash','Calm','Gentle','Sassy','Careful','Quirky'];
const natureZh=['勤奋','怕寂寞','勇敢','固执','顽皮','大胆','坦率','悠闲','淘气','乐天','胆小','急躁','认真','爽朗','天真','内敛','慢吞吞','冷静','害羞','马虎','温和','温顺','自大','慎重','浮躁'];
const keys=['hp','atk','def','spa','spd','spe'],array=x=>Array.isArray(x)?x:[x];
const records=[],rejected=[];
const primary=new Map();for(const e of catalog.entries.filter(e=>!e.research_only&&e.category!=='dynamax')){const id=toID(e.source_form_id||e.name_reference);if(!primary.has(id))primary.set(id,e);}
const itemNotes={leftovers:'每回合回复少量 HP，适合需要多次上场的耐久型方案。',heavydutyboots:'避免入场陷阱造成的影响，适合频繁换入或怕隐形岩的宝可梦。',choicescarf:'提高速度，但上场后会锁定第一次选择的招式。',choiceband:'提高物理攻击，但上场后会锁定第一次选择的招式。',choicespecs:'提高特殊攻击，但上场后会锁定第一次选择的招式。',lifeorb:'提高招式伤害；多数攻击命中后会损失自身 HP。',focussash:'满 HP 时保住一次本会致命的攻击；需留意陷阱和多段攻击。',assaultvest:'提高特防，但无法选择变化招式。',rockyhelmet:'对接触攻击者造成反伤，适合承受物理攻击。',lightclay:'延长光墙、反射壁和极光幕的持续时间。',eviolite:'提升仍可进化宝可梦的防御与特防。',sitrusberry:'HP 降至条件后回复，一场对战中通常只触发一次。',lumberry:'解除一次异常状态或混乱。',blacksludge:'适合毒属性的每回合回复；非毒属性携带会受损。',airballoon:'暂时免疫地面招式，受到攻击后破裂。',loadeddice:'用于与多段攻击配合，具体效果取决于招式。',boosterenergy:'用于触发古代活性或夸克充能，不能给任意特性带来强化。'};
for(const src of sources.records){
 const bytes=fs.readFileSync(path.join(root,'research/competitive-sources',src.file));assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),src.sha256);
 const raw=JSON.parse(bytes),validator=new TeamValidator(src.format),mod=validator.dex;
 for(const [species,sets] of Object.entries(raw))for(const [label,source] of Object.entries(sets)){
  const e=primary.get(toID(species)),s=mod.species.get(species);
  if(!e||!s.exists){rejected.push({format:src.format,species,label,reason:'No exact catalog form'});continue;}
  if(source.item===undefined||!source.evs||!source.nature){rejected.push({format:src.format,species,label,reason:'Source omits held item, EV spread or nature; incomplete plan not recommended'});continue;}
  const uniqueAbilities=[...new Set(Object.values(s.abilities))];
  const ability=array(source.ability)[0]||(uniqueAbilities.length===1?uniqueAbilities[0]:null);
  if(!ability){rejected.push({format:src.format,species,label,reason:'Source omits a non-unique ability; not guessed'});continue;}
  let choices=[[]];for(const slot of source.moves||[])choices=choices.flatMap(row=>array(slot).map(move=>[...row,move])).slice(0,128);
  let chosen;
  for(const moves of choices){
   if(new Set(moves).size!==moves.length)continue;
   const set={species,ability,moves,item:array(source.item)[0]||'',nature:array(source.nature)[0]||'Serious',evs:array(source.evs)[0]||{},ivs:array(source.ivs)[0]||{},level:source.level||100};
   if(source.teratypes)set.teraType=array(source.teratypes)[0];
   const problems=validator.validateSet(structuredClone(set),{});
   if(!problems?.length){chosen=set;break;}
  }
  if(!chosen){rejected.push({format:src.format,species,label,reason:'No primary move combination passed pinned format validator'});continue;}
  const item=Dex.items.get(chosen.item),abilityData=Dex.abilities.get(chosen.ability);
  const alternatives=array(source.item).filter(Boolean).filter(n=>n!==chosen.item).filter(n=>!validator.validateSet({...structuredClone(chosen),item:n},{})?.length);
  const role=chosen.moves.some(m=>['Dragon Dance','Swords Dance','Nasty Plot','Calm Mind','Quiver Dance','Shell Smash'].includes(m))?'强化展开':label.toLowerCase().includes('defens')?'耐久支援':chosen.moves.some(m=>['Trick Room','Tailwind','Reflect','Aurora Veil'].includes(m))?'队伍支援':(chosen.evs.atk||0)>(chosen.evs.spa||0)?'物理进攻':'特殊／功能型';
  records.push({id:`${src.format}:${e.entry_id}:${toID(label)}`,entry_id:e.entry_id,numeric_id:e.numeric_id,label,role,format:src.format,generation:+src.format[3],battle_kind:src.format.includes('doubles')?2:1,status:'source_format_validated',omni_battle_approved:false,story_availability:'unconfigured',source:src.url,analysis_url:`https://www.smogon.com/dex/${src.format[3]==='9'?'sv':src.format[3]==='8'?'ss':'sm'}/pokemon/${s.id}/`,
   item:{id:item.id,name_en:item.name,name_zh:ref.items[item.id]||item.name,num:Math.max(0,item.num),effect:itemNotes[item.id]||item.shortDesc||item.desc||'参考原作对应赛制的道具效果。'},
   alternative_items:alternatives.map(n=>({id:toID(n),name:ref.items[toID(n)]||n})),
   ability:{id:abilityData.id,num:abilityData.num,name_zh:local.abilities[abilityData.num]||abilityData.name},nature:chosen.nature,nature_zh:natureZh[natures.indexOf(chosen.nature)],nature_id:natures.indexOf(chosen.nature),level:chosen.level,
   evs:Object.fromEntries(keys.map(k=>[k,chosen.evs[k]||0])),ivs:Object.fromEntries(keys.map(k=>[k,chosen.ivs[k]??31])),
   moves:chosen.moves.map(n=>{const m=mod.moves.get(n);return {id:m.id,num:m.num,name_zh:local.moves[m.num]||m.name,name_en:m.name};}),tera_type:chosen.teraType||null,
   mechanic:item.megaStone?1:item.zMove||item.zMoveType?2:chosen.teraType?4:0,
   strategy_notes:[...(['Solar Power','Chlorophyll'].includes(chosen.ability)?['需要晴天支持；应与能建立天气的队友配合。']:[]),...(['Swift Swim','Rain Dish'].includes(chosen.ability)?['需要雨天支持，队伍与换入时机应围绕天气持续回合安排。']:[]),...(chosen.moves.includes('Trick Room')?['适合空间队伍；低速与个体值选择需要和队友协同。']:[]),...(chosen.moves.some(m=>['Dragon Dance','Swords Dance','Nasty Plot','Calm Mind','Quiver Dance','Shell Smash'].includes(m))?['先创造安全的强化回合；要考虑对手的先制招式、异常状态和逼换手段。']:[]),...(chosen.moves.some(m=>['Stealth Rock','Spikes','Toxic Spikes'].includes(m))?['通过入场陷阱积累收益，留意对方的清场手段。']:[])],
   usage_note:'这是来源赛制的参考方案，已检查该组合的个体合法性；没有将其认定为 Omni 最优方案。剧情获取与队伍搭配需要另外核对。',export_text:chosen});
 }
}
const result={schema_version:1,validator:'pokemon-showdown@0.11.11',records,rejected,coverage:{plans:records.length,forms:new Set(records.map(r=>r.entry_id)).size,uncovered_forms:catalog.entries.length-new Set(records.map(r=>r.entry_id)).size},notice:'Only exact source forms are mapped. No inferred plans for bond forms or transient states. Availability is unknown until story gates are configured.'};
result.content_sha256=crypto.createHash('sha256').update(JSON.stringify(records)).digest('hex');
fs.mkdirSync(path.join(root,'content/training/generated'),{recursive:true});fs.writeFileSync(path.join(root,'content/training/plans.json'),JSON.stringify(result,null,2)+'\n');
const rows=records.map((r,i)=>`{${r.numeric_id}u,${r.item.num},${r.ability.num},{${[0,1,2,3].map(j=>r.moves[j]?.num||0)}},{${keys.map(k=>r.evs[k])}},{${keys.map(k=>r.ivs[k])}},${r.level},${r.nature_id},${r.generation},${r.battle_kind},${r.mechanic},1}`);
fs.writeFileSync(path.join(root,'content/training/generated/plans.h'),`#include "omni/training.h"\n#define OMNI_TRAINING_COUNT ${records.length}\n#define OMNI_TRAINING_HASH 0x${result.content_sha256.slice(0,8)}u\nextern const OmniTrainingPlan omni_training_plans[OMNI_TRAINING_COUNT];\n`);
fs.writeFileSync(path.join(root,'content/training/generated/plans.c'),`/* Generated; source-format legality does not approve Omni battle rules. */\n#include "plans.h"\nconst OmniTrainingPlan omni_training_plans[OMNI_TRAINING_COUNT]={\n${rows.join(',\n')}\n};\n`);
console.log(JSON.stringify({coverage:result.coverage,rejected:rejected.length}));
