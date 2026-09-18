'use strict';
const fs=require('node:fs'),path=require('node:path');
module.exports=({entries,reference,Dex,root})=>{
 const snapshot=JSON.parse(fs.readFileSync(path.join(root,'content/pokedex/official-zukan-reference.json'),'utf8'));
 const norm=s=>String(s||'').normalize('NFKC').replace(/[\s・]/g,'');
 const speciesNames=new Map(reference.rows('pokemon_species_names').filter(r=>r.local_language_id==='1').map(r=>[+r.pokemon_species_id,r.name]));
 const jpForms=new Map(reference.rows('pokemon_form_names').filter(r=>r.local_language_id==='1').map(r=>[+r.pokemon_form_id,r.form_name]));
 const officialTypes=['','Normal','Fire','Water','Grass','Electric','Ice','Fighting','Poison','Ground','Flying','Psychic','Bug','Rock','Ghost','Dragon','Dark','Steel','Fairy'];
 const explicit={taurospaldeacombat:'0128-1',taurospaldeablaze:'0128-2',taurospaldeaaqua:'0128-3',kyogreprimal:'0382-1',groudonprimal:'0383-1',darmanitangalarzen:'0555-3',toxtricitygmax:'0849-2',toxtricitylowkeygmax:'0849-3',tatsugiricurlymega:'0978-3',tatsugiridroopymega:'0978-4',tatsugiristretchymega:'0978-5'};
 const linked=new Set();
 for(const e of entries){
  if(e.category==='rocket_bond_candidate'||e.category==='dynamax')continue;
  const rows=snapshot.records.filter(r=>+r.no===e.national_number),name=speciesNames.get(e.national_number),s=Dex.species.get(e.source_form_id||e.name_reference);
  if(!rows.length)continue;
  e.species_identity_evidence={url:`https://zukan.pokemon.co.jp/detail/${String(e.national_number).padStart(4,'0')}`,claims:['species_identity'],checked_at:snapshot.checked_at};
  const jpForm=jpForms.get(e.pokeapi?.form_id);
  let candidates=[];
  if(e.category==='mega'){
   const letter=/Mega-([XYZ])$/.exec(s.forme)?.[1]||'';
   candidates=rows.filter(r=>norm(r.name)===norm('メガ'+name+letter));
   if(candidates.length>1){const exact=candidates.filter(r=>norm(r.sub_name)===norm(jpForm));if(exact.length===1)candidates=exact;else candidates=candidates.filter(r=>s.id.includes('original')?r.sub_name.includes('500')||r.sub_name.includes('５００'):!r.sub_name);}
  }else if(e.category==='gigantamax'){
   candidates=rows.filter(r=>r.kyodai_flg===1);
   if(candidates.length>1)candidates=candidates.filter(r=>JSON.stringify([r.type_1,r.type_2].filter(Boolean).map(t=>officialTypes[t]))===JSON.stringify(e.types));
  }else if(jpForm){
   candidates=rows.filter(r=>norm(r.name)===norm(name)&&norm(r.sub_name)===norm(jpForm));
  }
  if(e.category==='base'&&!candidates.length){candidates=rows.filter(r=>r.sub===0&&norm(r.name)===norm(name));}
  if(explicit[s.id])candidates=rows.filter(r=>r.zukan_no===explicit[s.id]);
  if(candidates.length!==1)continue;
  const record=candidates[0];
  // Base Minior is the red core in Showdown; the site's default is the meteor shell.
  if(e.national_number===774&&e.category==='base'&&!record.sub_name.includes('コア'))continue;
  if(e.national_number===869&&e.category!=='gigantamax'&&e.category!=='base')continue; // no sweet/cream identities on this page
  const family=s.id==='meowsticfmega'||s.id==='meowsticmmega'||e.national_number===869&&e.category==='base';
  const recordTypes=[record.type_1,record.type_2].filter(Boolean).map(t=>officialTypes[t]);
  if(JSON.stringify([...e.types].sort())!==JSON.stringify([...recordTypes].sort()))throw Error(`Official type mismatch: ${e.entry_id} -> ${record.zukan_no}`);
  e.official_profile={zukan_no:record.zukan_no,name_ja:record.name,form_name_ja:record.sub_name,url:`https://zukan.pokemon.co.jp/detail/${record.zukan_no}`,types:[record.type_1,record.type_2].filter(Boolean).map(t=>officialTypes[t]),height:record.takasa,weight:record.omosa,image_url:record.image_m,match:family?'mega_family':'named_form'};
  linked.add(record.zukan_no);
  if(e.category!=='base'&&!e.identity_evidence)e.identity_evidence={url:e.official_profile.url,title:'宝可梦官方图鉴：对应形态',claims:[family?'mega_family_identity':'form_identity'],reviewed_at:snapshot.checked_at};
  if(e.identity_evidence)e.identity_status='official_named_form';
  if(e.identity_evidence)e.reference_status=e.research_only?'官方形态 · 数值待核验':'官方形态 · 参考数值';
  if(!e.art_reference.variants.front_default){e.art_reference={status:'official_reference_image',source:e.official_profile.url,variants:{front_default:record.image_m},front_http_status:null};}
 }
 // Unfezant's female appearance is a general gender sprite variant of the base species.
 const unfezant=entries.find(e=>e.entry_id==='dex:unfezant:base'),female=snapshot.records.find(r=>r.zukan_no==='0521-1');
 if(unfezant&&female){unfezant.gender_appearance_evidence={url:'https://zukan.pokemon.co.jp/detail/0521-1',claims:['female_appearance']};linked.add(female.zukan_no);}
 const audit={official_rows:snapshot.records.length,matched_rows:linked.size,unmatched_rows:snapshot.records.filter(r=>!linked.has(r.zukan_no)).map(r=>({zukan_no:r.zukan_no,national_number:+r.no,name_ja:r.name,form_name_ja:r.sub_name,url:`https://zukan.pokemon.co.jp/detail/${r.zukan_no}`}))};
 fs.writeFileSync(path.join(root,'content/pokedex/official-zukan-audit.json'),JSON.stringify(audit,null,2)+'\n');
};
