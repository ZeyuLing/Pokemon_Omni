const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const data=JSON.parse(fs.readFileSync('content/pokedex/catalog.json','utf8'));
 const c=(await WebAssembly.instantiate(fs.readFileSync('build/pokedex/pokedex.wasm'),{})).instance.exports;
 assert.equal(c.dex_hp(78,50,31,0,0),153);
 assert.equal(c.dex_max_hp(153,10,0),306);
 assert.equal(c.dex_max_hp(153,0,0),229);
 assert.equal(c.dex_hp(78,100,31,252,0),360);
 assert.equal(c.dex_max_hp(1,10,1),1);
 assert.equal(c.dex_hp(78,50,256,0,0),0);
 for(let hp=1;hp<=714;hp++)for(let level=0;level<=10;level++)assert.equal(c.dex_max_hp(hp,level,0),Math.floor(hp*(30+level)/20));
 const put=bytes=>{const memory=new Uint8Array(c.memory.buffer,c.dex_input_ptr(),65536);memory.fill(0);memory.set(bytes);};
 const query=(text='',category=0,type=0,research=1)=>{put(new TextEncoder().encode(text));return c.dex_query(category,0,type,0,research,0,0);};
 assert.equal(c.dex_count(),data.entries.length);
 for(const id of ['weedle','kakuna','beedrill','sprigatito','zacian','zamazenta','eternatus'])assert(!data.entries.some(e=>e.category==='dynamax'&&e.source_form_id===id),`Unsupported Dynamax entry: ${id}`);
 assert(data.entries.some(e=>e.category==='dynamax'&&e.source_form_id==='charizard'));
 for(const e of data.entries.filter(e=>e.category==='dynamax'))assert(e.eligibility_evidence?.official_rule&&e.eligibility_evidence?.availability_reference);
 for(let i=0;i<data.entries.length;i++)assert.equal(c.dex_id(i)>>>0,data.entries[i].numeric_id);
 for(let i=0;i<data.entries.length;i++){
  const e=data.entries[i];
  for(const [j,key] of ['hp','atk','def','spa','spd','spe'].entries())assert.equal(c.dex_stat(i,j),e.stats?.[key]||0);
  for(const [j,slot] of ['0','1','H','S'].entries()){const a=e.abilities.find(a=>a.slot===slot);assert.equal(c.dex_ability(i,j),a?data.abilities[a.id].reference_number:0);}
  assert.equal(c.dex_parent(i)>>>0,data.entries.find(p=>p.entry_id===e.transition.parent_entry_ids[0])?.numeric_id||0);
 }
 assert.equal(c.dex_stat(99999,0),0);assert.equal(c.dex_stat(0,6),0);
 assert.equal(c.dex_ability(99999,0),0);assert.equal(c.dex_ability(0,4),0);
 const visible=data.entries.filter(e=>e.category!=='dynamax');
 assert.equal(query(),visible.length);
 const count=c.dex_query_all(0,0,0,0,1,0),order=Array.from(new Uint16Array(c.memory.buffer,c.dex_result_ptr(),count));
 assert.deepEqual(order.map(i=>data.entries[i].entry_id),[...visible.filter(e=>e.category_id===1),...visible.filter(e=>e.category_id!==1)].map(e=>e.entry_id));
 assert.equal(order.slice(0,1025).filter(i=>data.entries[i].category_id===1).length,1025);
 assert.equal(query('',11),0);
 assert.equal(c.dex_total(0),visible.filter(e=>!e.research_only).length);
 assert.equal(query('喷火龙'),visible.filter(e=>e.name_zh_hans.includes('喷火龙')).length);
 assert.equal(query('CHARIZARD'),query('charizard'));
 for(let cat=1;cat<=data.categories.length;cat++) assert.equal(query('',cat),visible.filter(e=>e.category_id===cat).length);
 for(let type=1;type<=data.types.length;type++)assert.equal(query('',0,type),visible.filter(e=>e.types.includes(data.types[type-1].id)).length);
 assert.equal(query('',0,0,0),visible.filter(e=>!e.research_only).length);
 const base=data.entries.findIndex(e=>e.entry_id==='dex:charizard:base'),mega=data.entries.findIndex(e=>e.source_form_id==='charizardmegax'),bond=data.entries.findIndex(e=>e.category==='rocket_bond_candidate');
 assert.equal(c.dex_record(mega,2),0);assert.equal(c.dex_flags(mega),3);assert.equal(c.dex_flags(base),0);
 assert.equal(c.dex_record(bond,2),3);assert.equal(c.dex_flags(bond),0);
 const n=c.dex_save(),save=new Uint8Array(c.memory.buffer,c.dex_input_ptr(),n).slice();
 const damaged=save.slice();damaged[12]^=1;put(damaged);assert.equal(c.dex_load(n),5);assert.equal(c.dex_flags(mega),3);
 put(save);assert.equal(c.dex_load(n),0);assert.equal(c.dex_flags(mega),3);
 // Historical Dynamax IDs remain loadable but cannot inflate collection totals.
 const legacy=data.entries.findIndex(e=>e.entry_id==='dex:charizard:base:dynamax');
 assert.equal(c.dex_record(legacy,2),0);
 const oldSize=c.dex_save(),oldBytes=new Uint8Array(c.memory.buffer,c.dex_input_ptr(),oldSize).slice();
 put(oldBytes);assert.equal(c.dex_load(oldSize),0);assert.equal(c.dex_flags(legacy),3);
 assert.equal(c.dex_total(2),1);assert.equal(query('',11),0);
 console.log('PASS: full catalog C/Wasm ID parity; all category/type filters; Chinese and case-insensitive search; independent Mega progress; research protection; corrupt save atomicity');
})().catch(e=>{console.error(e);process.exitCode=1;});
