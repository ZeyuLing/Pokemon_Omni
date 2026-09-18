'use strict';
const fs=require('node:fs'),path=require('node:path');
module.exports=({entries,reference,l,Dex,toID,root})=>{
 const art=JSON.parse(fs.readFileSync(path.join(root,'content/pokedex/form-art-reference.json'),'utf8'));
 const byForm=new Map(art.records.map(r=>[r.form_id,r]));
 const availability=JSON.parse(fs.readFileSync(path.join(root,'content/pokedex/art-availability.json'),'utf8'));
 const byId=new Map(entries.map(e=>[e.entry_id,e]));
 const primary=entries.filter(e=>e.category!=='dynamax'&&!e.supplemental&&e.category!=='rocket_bond_candidate');
 const bySource=new Map(primary.map(e=>[e.source_form_id||e.species_id.slice(8),e]));
 const itemName=n=>reference.items[toID(n)]||n;
 const evolutionMethods={levelFriendship:'亲密度提升后升级',levelHold:'携带物品升级',levelMove:'学会指定招式后升级',levelExtra:'满足特殊条件后升级',trade:'通信交换',useItem:'使用进化物品',other:'特殊进化条件'};
 for(const e of entries){
  const s=e.category==='rocket_bond_candidate'?null:Dex.species.get(e.source_form_id||e.name_reference);
  const meta=reference.species.get(e.national_number);
  if(e.pokeapi){
   const pid=String(e.pokeapi.pokemon_id);
   e.field_crosschecks={stats:e.stats_crosscheck?.agrees||false,types:JSON.stringify(e.types)===JSON.stringify(reference.formTypes.get(String(e.pokeapi.form_id))||reference.types.get(pid)),ability_numbers:JSON.stringify([...new Set(e.abilities.map(a=>a.id))].sort())===JSON.stringify([...new Set(reference.abilityNumbers.get(pid)||[])].sort())};
   if(!e.field_crosschecks.ability_numbers){
    const available=reference.abilityNumbers.get(pid);
    e.ability_comparison={showdown:e.abilities.map(a=>a.id),pokeapi:available||[],status:!available?'second_source_missing':'different_record_scope',explanation_zh:!available?'PokeAPI 对此形态没有特性记录；当前仅列回合制适配参考，尚未获得第二来源确认。':s.forme?.includes('Totem')?'Showdown 列霸主个体的限定特性，PokeAPI 沿用整个物种的特性集合。':s.baseSpecies==='Pikachu'||s.id==='pichuspikyeared'?'Showdown 列特殊装扮／活动个体的限定特性，PokeAPI 沿用物种特性集合。':s.baseSpecies==='Darmanitan'?'达摩状态由达摩模式特性触发；物种表中的其他特性不应自动赋予该战斗状态。':'两份来源对特殊特性个体的拆分方式不同；图鉴保留 Showdown 跨版本集合，具体个体是否合法须使用来源规则校验。'};
   }
  }
  e.species_facts=meta?{legendary:meta.is_legendary==='1',mythical:meta.is_mythical==='1',gender_rate:+meta.gender_rate,gender_visual_difference:meta.has_gender_differences==='1',capture_rate:+meta.capture_rate,growth_rate_id:+meta.growth_rate_id,egg_cycles:+meta.hatch_counter}:null;
  e.acquisition={status:'awaiting_world_design',gate_id:null,locations:[],note:'本项目地图与捕捉剧情尚未编排，不能把原作地点当作本项目获取地点。'};
  if(e.category==='rocket_bond_candidate'){
   e.art_reference={status:'author_art_not_imported',variants:{},source:null};
   e.transition={status:'author_trigger_not_documented',parent_entry_ids:[],summary_zh:'作者文档提供形态数值；本项目羁绊触发、训练家绑定与获取条件待设计。'};
   if(e.name_reference.startsWith('Sacred Dragon Dun')){e.parent_species_reference={id:'rocket:dun',name:'Dun',status:'author_custom_species',lineage_note:'作者 Primigenios y Antiguos 文档列在 Dunsparce / Blessparce / Dun 一节；不能直接当成官方土龙节节。'};}
   continue;
  }
  const parent=e.source_entry_id?byId.get(e.source_entry_id):null;
  const artRow=byForm.get((parent||e).pokeapi?.form_id);
  const variants=artRow?.sprites||{};
  e.art_reference={status:variants.front_default?'metadata_mapped':'reference_image_pending',source:artRow?.metadata_url||null,variants};
  e.art_reference.front_http_status=availability.urls[variants.front_default]?.status||null;
  // Ordinary Dynamax has no new design; explicitly show the source form illustration.
  if(parent)e.art_reference={...e.art_reference,status:variants.front_default?'source_form_illustration':'reference_image_pending'};
  e.default_form_label_zh=e.category==='base'?e.form_name_zh||null:null;
  const from=e.form_transition_reference?.changes_from;
  const sources=parent?[parent]:[...(Array.isArray(from)?from:from?[from]:[])].map(n=>bySource.get(Dex.species.get(n).id)).filter(Boolean);
  if(!sources.length&&e.category!=='base'){const base=bySource.get(Dex.species.get(s.baseSpecies).id);if(base&&base!==e)sources.push(base);}
  let summary='具体转换条件参考原作；本项目触发规则待配置。';
  if(e.category==='base')summary='基础物种条目；下方展示参考进化关系。';
  if(e.category==='mega')summary=e.form_transition_reference?.required_move?'学会 '+(l.moves[Dex.moves.get(e.form_transition_reference.required_move).num]||e.form_transition_reference.required_move)+' 后满足 Mega 条件；无普通 Mega 石要求。':'满足 Mega 条件并使用对应进化石'+(e.required_items.length?'（'+e.required_items.map(itemName).join('／')+'）':'')+'。';
  if(e.category==='dynamax')summary='剑盾收录范围内的可用常驻形态；战斗中激活极巨化。资格经社区剑盾数据交叉核对。';
  if(e.category==='gigantamax')summary='需要具有超极巨化资格的特定个体；战斗中使用极巨化机制进入本形态。普通个体不能仅凭物种名称转换。';
  if(e.category==='cosmetic')summary='外观变体独立记录；不自动推导额外能力提升。';
  if(e.category==='gender_form')summary='性别决定的形态；不能视为任意切换按钮。';
  if(e.category==='regional')summary='地区变体；具体出生、进化或获取条件由原作和本项目剧情决定。';
  if(e.category==='battle_state')summary='战斗中由对应特性或条件触发的状态；不是常驻捕捉形态。';
  if(e.category==='fusion')summary='通过对应合体操作与伙伴宝可梦形成；合体与解除关系需由游戏规则处理。';
  if(e.category==='primal_reversion')summary='携带对应宝珠进入战斗后原始回归。';
  if(e.category==='type_form')summary='携带对应石板、存储碟或卡带形成属性／招式变化；按各物种规则处理。';
  if(e.category==='ultra_burst')summary='合体奈克洛兹玛满足究极爆发条件后转换；不当作独立野生物种。';
  if(e.category==='tera_related')summary='太晶化或对应特性触发的特殊形态；普通宝可梦的太晶属性另存为个体状态。';
  e.transition={status:'reference_not_project_rule',parent_entry_ids:sources.map(x=>x.entry_id),summary_zh:summary};
  e.evolution_edges=(s.evos||[]).map(n=>{
   const target=Dex.species.get(n),record=bySource.get(target.id);
   return {to_entry_id:record?.entry_id||null,name_zh:record?.name_zh_hans||l.species[target.num]||n,level:target.evoLevel||null,method:target.evoType||'level',item:target.evoItem||null,item_zh:target.evoItem?itemName(target.evoItem):null,move:target.evoMove||null,move_zh:target.evoMove?l.moves[Dex.moves.get(target.evoMove).num]||target.evoMove:null,condition:target.evoCondition||null,summary_zh:target.evoLevel?`等级达到 ${target.evoLevel}`:evolutionMethods[target.evoType]||'按原作特殊条件进化',source:'pokemon-showdown@0.11.11'};
  });
  e.evolution_rule_records=reference.rows('pokemon_evolution').filter(r=>+r.evolved_species_id===e.national_number&&(!r.evolved_pokemon_form_id||e.pokeapi_form_ids?.includes(+r.evolved_pokemon_form_id)));
 }
 // A source default does not always match Showdown's battle default. Links use resolved IDs above.
 for(const e of entries)if(e.art_reference?.status==='reference_image_pending'&&e.sprite_id)e.art_reference.fallback_url=`https://play.pokemonshowdown.com/sprites/gen5/${encodeURIComponent(e.sprite_id)}.png`;
};
