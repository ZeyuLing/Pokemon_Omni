/* Black-box input, framebuffer, hardware timer and audio checks in mGBA. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
(async()=>{
 const storyMode=process.argv.includes('--story'),prefix=storyMode?'story-':'';
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync(storyMode?'build/pallet/omni-story.gba':'build/pallet/omni-pallet.gba'),p=m._malloc(rom.length);m.HEAPU8.set(rom,p);assert(m._mgbawasm_load(p,rom.length,0,0,0,0,1));m._free(p);
 const n=m._mgbawasm_state_size(),sp=m._malloc(n),ap=m._malloc(8192);let go=-1,po=-1;
 function state(){assert(m._mgbawasm_state_save(sp));const b=Buffer.from(m.HEAPU8.buffer,sp,n);if(go<0)go=b.indexOf(Buffer.from('544c4150494e4d4f','hex'));if(po<0)po=b.indexOf(Buffer.from('53455250494e4d4f','hex'));assert(go>=0&&po>=0);return {screen:b.readUInt32LE(go+8),x:b.readUInt32LE(go+16),speed:b.readUInt32LE(po+8),scene:b.readUInt32LE(po+12),ticks:b.readUInt32LE(po+16),music:b.readUInt32LE(po+20),clock:b.readUInt32LE(po+28),cast:b.readUInt32LE(po+32)};}
 const chunks=[];function frames(count,record=false){while(count--){m._mgbawasm_run_frame();let size;while((size=m._mgbawasm_read_audio(ap,2048))>0)if(record)chunks.push(Buffer.from(m.HEAPU8.slice(ap,ap+size*4)));}}
 function press(k){m._mgbawasm_set_keys(k);frames(4);m._mgbawasm_set_keys(0);frames(12);}
 function shot(name){fs.writeFileSync(`build/pallet/${prefix}${name}.rgba`,Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600)));}
 function sram(){m._mgbawasm_sram_save();return Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));}
 frames(90);assert.equal(state().screen,storyMode?0:6);if(!storyMode)press(2);assert.equal(state().screen,0);shot('opening-title');
 const before=sram();press(512);assert.equal(state().screen,14);frames(30);shot('opening-war');
 for(let i=1;i<11;i++){press(1);frames(20);assert.equal(state().scene,i);shot('opening-'+i);}
 press(1);assert.equal(state().screen,0);assert(before.equals(sram()),'Replay must not write SRAM');
 press(512);press(8);assert.equal(state().screen,15);const paused=state().ticks;frames(100);assert.equal(state().ticks,paused);press(2);assert.equal(state().screen,14);press(8);press(1);assert.equal(state().screen,0);
 press(256);assert.equal(state().screen,16);const count=require('../assets/characters/manifest.json').portraits.length;const unique=new Set();
 for(let i=0;i<count;i++){assert.equal(state().cast,i);shot('cast-'+i);unique.add(crypto.createHash('sha256').update(Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600))).digest('hex'));press(16);}
 assert.equal(unique.size,count);assert.equal(state().cast,0);press(32);assert.equal(state().cast,count-1);press(2);assert(before.equals(sram()),'Gallery must not write SRAM');
 press(1);assert.equal(state().screen,14);press(8);press(1);assert.equal(state().screen,7);press(1);assert.equal(state().screen,1);assert(!before.equals(sram()),'New game commits only after opening');
 frames(60);assert(m._mgbawasm_state_save(sp));const startState=Buffer.from(m.HEAPU8.slice(sp,sp+n));const distances=[];
 for(const speed of [1,2,4]){
  m.HEAPU8.set(startState,sp);assert(m._mgbawasm_state_load(sp));m._mgbawasm_set_keys(0);
  if(speed>=2)press(4);if(speed===4)press(4);frames(110);const x=state().x;
  m._mgbawasm_set_keys(16);frames(12);m._mgbawasm_set_keys(0);distances.push(state().x-x);
 }
 assert(distances[1]>distances[0]&&distances[2]>distances[1],`Exploration speed ineffective: ${distances}`);
 m.HEAPU8.set(startState,sp);assert(m._mgbawasm_state_load(sp));m._mgbawasm_set_keys(0);frames(20);
 const rates=[];
 for(const speed of [1,2,4]){
  assert.equal(state().speed,speed);frames(40);const start=state();chunks.length=0;frames(600,true);const end=state(),pcm=Buffer.concat(chunks);
  let energy=0;for(let i=0;i<pcm.length;i+=2){const a=pcm.readInt16LE(i)/32768;energy+=a*a;}
  const rms=Math.sqrt(energy/(pcm.length/2)),elapsed=(end.clock-start.clock)&65535;
  assert(rms>0.003,`BGM silent at ${speed}x`);assert(Math.abs((end.music-start.music)-elapsed/20)<=1,'Tempo tied to accelerated simulation');
  rates.push({speed,hardware_ticks:elapsed,music_steps:end.music-start.music,samples:pcm.length/4,rms});
  if(speed===1)fs.writeFileSync('build/pallet/music-normal.pcm',pcm);
  press(4);
 }
 assert(rates.every(r=>Math.abs(r.music_steps-rates[0].music_steps)<=1),'Tempo differs across speeds');
 assert.equal(state().speed,1);shot('speed-normal');
 /* Natural timeout also reaches bedroom; replay does not create a save. */
 m._mgbawasm_reset();go=po=-1;frames(90);press(2);press(512);frames(100);chunks.length=0;frames(600,true);fs.writeFileSync('build/pallet/music-opening.pcm',Buffer.concat(chunks));frames(5100);assert.equal(state().screen,0,'Automatic montage ends at title');
 const report={rom_sha256:crypto.createHash('sha256').update(rom).digest('hex'),scenes:11,portraits:count,skip_cancel:true,replay_preserves_save:true,gallery_preserves_save:true,new_game_after_opening:true,automatic_advance:true,movement_tiles_in_12_frames:distances,audio_rate:m._mgbawasm_sample_rate(),speed_audio:rates,scope:'PSG BGM and in-game exploration speed. Arbitrary external emulator turbo is not controlled.'};
 fs.writeFileSync(`build/pallet/${prefix}presentation-test.json`,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
