/* Real cartridge playback: moving units, independent attack phases, collisions,
 * pause, and continuous raw video/audio for review. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length),ap=m._malloc(8192);m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const n=m._mgbawasm_state_size(),sp=m._malloc(n);let wp=-1,pp=-1,gp=-1;
 function state(){m._mgbawasm_state_save(sp);const b=Buffer.from(m.HEAPU8.buffer,sp,n);if(wp<0)wp=b.indexOf(Buffer.from('4f4d495741523100','hex'));if(pp<0)pp=b.indexOf(Buffer.from('53455250494e4d4f','hex'));if(gp<0)gp=b.indexOf(Buffer.from('544c4150494e4d4f','hex'));assert(wp>=0&&pp>=0&&gp>=0);return {b,tick:b.readUInt32LE(wp+8),count:b.readUInt32LE(wp+12),active:b.readUInt32LE(wp+16),hits:b.readUInt32LE(wp+20),chapter:b.readUInt32LE(pp+52),screen:b.readUInt32LE(gp+8)};}
 function video(){return Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600));}
 function frame(audio){m._mgbawasm_run_frame();let count;while((count=m._mgbawasm_read_audio(ap,2048))>0)if(audio!==undefined)fs.writeSync(audio,Buffer.from(m.HEAPU8.slice(ap,ap+count*4)));}
 function frames(count){while(count--)frame();}
 function key(k){m._mgbawasm_set_keys(k);frames(4);m._mgbawasm_set_keys(0);frames(12);}
 frames(90);key(512);assert.equal(state().screen,14);
 const data=require('../build/pallet/war-terrain.json'),moves=new Set(),fires=new Set(),hit=new Set(),unique=new Set(),samples=[];
 const vf=fs.openSync('build/pallet/war-playback.rgba','w'),af=fs.openSync('build/pallet/war-playback.pcm','w');let f=0,maxActive=0;
 while(state().chapter===0&&f<3600){
  frame(af);const s=state();if(f%4===0)fs.writeSync(vf,video());
  if(f%180===0)fs.writeFileSync(`build/pallet/war-frame-${f}.rgba`,video());
  maxActive=Math.max(maxActive,s.active);assert.equal(s.count,data.actors.length);
  const positions=[];
  for(let i=0;i<s.count;i++){
   const a=data.actors[i],x=s.b.readInt32LE(wp+32+i*16),y=s.b.readInt32LE(wp+36+i*16),action=s.b.readUInt32LE(wp+40+i*16),hurt=s.b.readUInt32LE(wp+44+i*16);
   positions.push([x,y]);if(x!==a.at[0]||y!==a.at[1])moves.add(i);if(action===3)fires.add(i);if(hurt)hit.add(i);
   if(a.layer!==2)for(const [fx,fy] of [[x+2,y-12],[x+13,y-1]]){
    assert(fx>=0&&fy>=0&&fx<data.width*16&&fy<data.height*16);
    assert.equal(data.cells[Math.floor(fy/16)*data.width+Math.floor(fx/16)],a.layer===1?2:0,`Unit ${i} left traversable terrain at ${s.tick}`);
   }
  }
  for(let i=0;i<s.count;i++)for(let j=i+1;j<s.count;j++)if(data.actors[i].layer===data.actors[j].layer)assert(Math.abs(positions[i][0]-positions[j][0])>=12||Math.abs(positions[i][1]-positions[j][1])>=12,`Overlapping units ${i}/${j}`);
  if(f%60===0){samples.push({frame:f,ticks:s.tick,active:s.active,hits:s.hits,positions});unique.add(require('node:crypto').createHash('sha256').update(video()).digest('hex'));}
  f++;
 }
 fs.closeSync(vf);fs.closeSync(af);assert(f<3600);assert(maxActive>=3,'Must have simultaneous attacks');assert.equal(fires.size,data.actors.filter(a=>a.attack).length);assert(hit.size>=16);assert(moves.size>=data.actors.filter(a=>a.at.join()!=a.to.join()).length);assert(unique.size>30);
 // Repeat and pause at the same timeline; unit animation must also freeze.
 key(8);key(1);key(512);frames(240);key(8);assert.equal(state().screen,15);const paused=state().tick;frames(90);assert.equal(state().tick,paused);key(2);frames(20);assert(state().tick>paused);
 fs.writeFileSync('build/pallet/war-playback.json',JSON.stringify({frames:f,fps:59.727500569606/4,actors:data.actors.length,moving_units:moves.size,attackers:fires.size,hit_units:hit.size,max_simultaneous_attacks:maxActive,pause_freezes_units:true,source:'Actual GBA ROM in mGBA, no RAM mutation',samples},null,2));
 console.log(`PASS: ${data.actors.length} units, ${fires.size} attackers, ${hit.size} hit recipients, ${maxActive} simultaneous attacks; ${f} recorded frames, traversability, separation, pause`);
 m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
