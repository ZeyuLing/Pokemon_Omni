/* Exercise the embedded Dex using buttons only. Read-only RAM probes describe
 * navigation; image pixels are checked against the source atlas decoder. */
const fs=require('node:fs'),assert=require('node:assert/strict');
module.exports=function checkDex(m,press,shot){
 const size=m._mgbawasm_state_size(),ptr=m._malloc(size),signature=Buffer.from('50584544494e4d4f','hex');
 const state=()=>{assert(m._mgbawasm_state_save(ptr));const b=Buffer.from(m.HEAPU8.buffer,ptr,size),at=b.indexOf(signature);assert(at>=0);const v=Array.from({length:10},(_,i)=>b.readUInt32LE(at+8+i*4));return {screen:v[0],page:v[1],entry:v[2],scroll:v[3],lines:v[4],move:v[5],image:v[6],plan:v[7]};};
 function page(n){let s=state();assert.equal(s.screen,1);press(4);assert.equal(state().screen,6);for(let i=0;i<(n-s.page+15)%15;i++)press(128);press(1);assert.equal(state().page,n);assert.equal(state().screen,1);}
 function readToEnd(){const n=state().lines;assert(n>0);for(let i=0;i<n+2;i++)press(128);assert.equal(state().scroll,Math.max(0,n-6));}
 const report=require('../build/gba/asset-report.json'),atlas=fs.readFileSync('build/gba/art.bin'),catalog=require('../content/pokedex/catalog.json');
 function pixels(variant){const s=state(),url=catalog.entries[s.entry].art_reference.variants[variant];assert(url);const row=report.images.find(r=>r.url===url);let at=row.offset,mode=atlas.readUInt16LE(at);at+=2;const values=[];while(values.length<4096){let n=1;if(mode){n=atlas.readUInt16LE(at);at+=2;}const c=atlas.readUInt16LE(at);at+=2;for(let i=0;i<n;i++)values.push(c);}const v=m._mgbawasm_video_ptr();for(let i=0;i<4096;i++){const c=values[i]&0x8000?31|(31<<5)|(30<<10):values[i],p=v+((44+(i>>6))*240+88+i%64)*4;assert.equal(m.HEAPU8[p]>>3,c&31);assert.equal(m.HEAPU8[p+1]>>3,(c>>5)&31);assert.equal(m.HEAPU8[p+2]>>3,(c>>10)&31);}}
 assert.equal(state().page,0);assert.equal(state().entry,0);
 // No normal Dynamax in same-species forms, and R follows the visible order.
 page(4);press(128);press(1);assert.equal(state().entry,0);
 press(256);assert.equal(catalog.entries[state().entry].entry_id,'dex:ivysaur:base');
 press(512);assert.equal(state().entry,0);
 page(7);shot('dex-evolution');readToEnd();
 page(6);assert(state().lines>6);readToEnd();shot('dex-ability-end');
 page(1);press(1);assert.equal(state().move,1);press(1);assert.equal(state().move,2);readToEnd();press(1);assert.equal(state().move,3);readToEnd();shot('dex-learning-sources');press(2);
 page(13);pixels('front_default');press(128);pixels('back_default');press(128);pixels('front_shiny');shot('dex-shiny');
 page(14);press(1);press(8);shot('dex-hp');
 // Venusaur is the first source-validated plan in national order.
 const venusaur=catalog.entries.findIndex(e=>e.entry_id==='dex:venusaur:base');
 page(9);for(let i=0;i<2;i++)press(256);assert.equal(state().entry,venusaur);assert(state().lines>1);readToEnd();shot('dex-held-item');
 page(10);assert(state().lines>6);readToEnd();shot('dex-strategy');
 page(11);readToEnd();page(12);readToEnd();
 // Restore starting page/entry so surrounding game tests retain their flow.
 for(let i=0;i<2;i++)press(512);page(0);m._free(ptr);
 return {page_directory:true,long_text_to_end:true,evolution:true,move_effect_and_decoded_sources:true,held_item_and_strategy:true,front_back_shiny_pixels:true,hp_calculator_controls:true};
};
