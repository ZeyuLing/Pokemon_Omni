'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
module.exports=({root,entries,abilities,stableId,categories})=>{
 const source=JSON.parse(fs.readFileSync(path.join(root,'content/source-variants/ultra-emerald-5.8.json'),'utf8'));
 const selected=new Map(source.records.map(r=>[r.source_sid,r.entry_id]));
 for(const row of source.records){
  const base=entries.find(e=>e.category==='base'&&e.national_number===row.national_number);
  const parent=selected.get(row.parent_source_sid)||base?.entry_id;
  const items=[...new Set(row.incoming_evolutions.map(e=>e.item_name).filter(Boolean))];
  const conditions=row.incoming_evolutions.map(e=>`${e.source_name}：${e.method_raw===7?'使用'+e.item_name:e.method_raw===6?'携带'+e.item_name+'通信交换':e.method_raw===1?'亲密度进化':e.method_raw===251?'超进化条件 '+e.item_name:'条件编号 '+e.method_raw}`);
  for(const a of row.abilities)abilities[`ue58_${a.source_id}`]={name_en:`UE58 ability ${a.source_id}`,name_zh:a.name||`源特性 ${a.source_id}（名称待核实）`,reference_number:0,source_ability_id:a.source_id,source_rom_sha256:source.source_rom_sha256};
  for(const asset of Object.values(row.variants)){
   assert(asset.path.startsWith('assets/imported/ultra-emerald-5.8-user/form-sprites/')&&!asset.path.includes('..'));
   if(fs.existsSync(path.join(root,asset.path)))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,asset.path))).digest('hex'),asset.sha256);
  }
  entries.push({entry_id:row.entry_id,numeric_id:stableId(row.entry_id),species_id:base?.species_id||`omni:ultra58:${row.source_sid}`,
   national_number:row.national_number,name_reference:`Ultra Emerald 5.8 / ${row.source_sid}`,search_name_en:`Ultra Emerald 5.8 ${row.source_sid} ${base?.search_name_en||''}`,
   name_zh_hans:row.display_name,category:'source_variant',category_id:categories.indexOf('source_variant')+1,generation:base?.generation||0,
   research_only:true,production_ready:false,battle_data_approved:false,presentation:'standalone',identity_status:'source_rom_variant',identity_evidence:null,
   reference_status:'究极绿宝石 5.8 · 用户版本',stats_status:'hash_locked_source_rom',ability_status:'source_rom_uint16_table',
   stats:Object.fromEntries(['hp','atk','def','spa','spd','spe'].map(k=>[k,row.stats[k]])),types:row.types,
   abilities:row.abilities.map(a=>({slot:a.slot,id:`ue58_${a.source_id}`})),move_pool_ids:[],move_pool_status:'source_learnset_pending',
   height_m:null,weight_kg:null,prevo:null,evolutions:[],evolution_edges:[],required_items:[],required_items_zh:items,
   transition:{parent_entry_ids:parent?[parent]:[],summary_zh:conditions.length?'来源版本进化表：'+conditions.join('；')+'。本作条件尚未接入。':'未找到常规进化表入口，获取脚本尚待核实。',status:'source_table_only'},
   form_transition_reference:null,registration_rule:'来源形态可查看；本作获取与战斗规则接入后开放登记',capture_gate_status:'未配置',acquisition:{note:'来源于用户提供的神战永久超进化修改版；本作获取剧情尚待设计。'},
   mechanic_note:'图片、六项种族值、属性与特性编号取自你提供的 5.8 修改版。特性使用该版本独立编号；效果、招式、永久保持与解除规则仍待核验，不能直接等同官方机制。',
   source_rom_evidence:{sha256:source.source_rom_sha256,species_id:row.source_sid,source_name:row.source_name,record_sha256:row.record_sha256,ability_table_offset:row.ability_table_offset,incoming_evolutions:row.incoming_evolutions},
   art_reference:{status:'source_rom_extracted',source:null,variants:Object.fromEntries(Object.entries(row.variants).map(([k,v])=>[k,v.url])),assets:row.variants,local_only:true,normal_shiny_identical:row.normal_shiny_identical}
  });
 }
};
