/* Real ROM input/framebuffer verification. Trial never writes existing SRAM. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length);m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const n=m._mgbawasm_state_size(),sp=m._malloc(n),ap=m._malloc(8192);let gp=-1,tp=-1;
 function state(){m._mgbawasm_state_save(sp);const b=Buffer.from(m.HEAPU8.buffer,sp,n);if(gp<0)gp=b.indexOf(Buffer.from('544c4150494e4d4f','hex'));if(tp<0)tp=b.indexOf(Buffer.from('545241564f4d4e49','hex'));assert(gp>=0&&tp>=0);return {screen:b.readUInt32LE(gp+8),map:b.readUInt32LE(gp+12),x:b.readUInt32LE(gp+16),y:b.readUInt32LE(gp+20),direction:b.readUInt32LE(gp+24),selected:b.readUInt32LE(tp+8),species:b.readUInt32LE(tp+12),visible:b.readUInt32LE(tp+16),mounted:b.readUInt32LE(tp+20),fx:b.readInt32LE(tp+24),fy:b.readInt32LE(tp+28),face:b.readUInt32LE(tp+32),walking:b.readUInt32LE(tp+36),trial:b.readUInt32LE(tp+40),moving:b.readUInt32LE(tp+44),ax:b.readInt32LE(tp+48),ay:b.readInt32LE(tp+52),pose:b.readUInt32LE(tp+60),mountSlot:b.readUInt32LE(tp+64),mountSpecies:b.readUInt32LE(tp+68),mountPose:b.readUInt32LE(tp+72)};}
 let record=false;const captures=[];
 function frames(count){while(count--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(ap,2048)>0){}if(record){const s=state();if(s.moving){const name=`travel-walk-${String(captures.length).padStart(3,'0')}`;shot(name);captures.push({...s,file:name});}}}}
 function press(key){m._mgbawasm_set_keys(key);frames(4);m._mgbawasm_set_keys(0);frames(20);}
 function shot(name){fs.writeFileSync('build/pallet/'+name+'.rgba',Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600)));}
 function sram(){m._mgbawasm_sram_save();return Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));}
 function dismiss(){let budget=10;while(state().screen===7&&budget-->0)press(1);assert.equal(state().screen,1,JSON.stringify(state()));}
 function step(key){const from=state();let ticks=0;m._mgbawasm_set_keys(key);while(state().x===from.x&&state().y===from.y&&ticks++<120)frames(1);m._mgbawasm_set_keys(0);assert(ticks<120,'Blocked step '+JSON.stringify(from));while(state().moving&&ticks++<120)frames(1);frames(4);assert(ticks<120);return ticks;}
 function route(tx,ty){const s=state(),g=require('../build/pallet/scene-audit.json').find(g=>g.id===s.map),queue=[[s.x,s.y,[]]],seen=new Set();while(queue.length){const [x,y,p]=queue.shift(),id=y*g.width+x;if(seen.has(id))continue;seen.add(id);if(x===tx&&y===ty){for(const k of p)step(k);return;}for(const [dx,dy,k] of [[0,1,128],[0,-1,64],[-1,0,32],[1,0,16]]){const nx=x+dx,ny=y+dy;if(nx>=0&&ny>=0&&nx<g.width&&ny<g.height&&(!g.collision[ny*g.width+nx]||(nx===tx&&ny===ty&&(g.warps||[]).some(w=>w.x===nx&&w.y===ny)))&&!g.actors.some(a=>a.x===nx&&a.y===ny)&&(!(g.warps||[]).some(w=>w.x===nx&&w.y===ny)||(nx===tx&&ny===ty)))queue.push([nx,ny,[...p,k]]);}}throw Error('No route');}

 frames(90);const before=sram();press(12);dismiss();
 press(8);press(128);press(1);press(128);press(128);press(8);assert.equal(state().mounted,1);
 const clips=[];
 for(const [name,result] of [['dismount',0],['mount',1]]){
  const start=state(),samples=[];
  for(let i=0;i<28;i++){
   m._mgbawasm_set_keys(i===0?256:0);frames(1);
   const file='rider-'+name+'-'+String(i).padStart(2,'0');shot(file);
   const pixels=fs.readFileSync('build/pallet/'+file+'.rgba');
   samples.push({file,hash:require('node:crypto').createHash('sha256').update(pixels).digest('hex')});
  }
  assert.equal(state().mounted,result);assert.equal(state().x,start.x);assert.equal(state().y,start.y);
  assert(new Set(samples.map(s=>s.hash)).size>=3,'Transition must produce actual intermediate frames');
  clips.push({name,samples});
 }
 assert(before.equals(sram()));
 fs.writeFileSync('build/pallet/rider-transition-review.json',JSON.stringify(clips,null,2));
 console.log('PASS: actual native rider mounting/dismounting intermediate frames; position and SRAM unchanged');
})().catch(e=>{console.error(e);process.exitCode=1;});
