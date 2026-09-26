/* Black-box input, framebuffer, hardware timer and audio checks in mGBA. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
(async()=>{
 const storyMode=process.argv.includes('--story'),prefix=storyMode?'story-':'';
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync(storyMode?'build/pallet/omni-story.gba':'build/pallet/omni-pallet.gba'),p=m._malloc(rom.length);m.HEAPU8.set(rom,p);assert(m._mgbawasm_load(p,rom.length,0,0,0,0,1));m._free(p);
 const n=m._mgbawasm_state_size(),sp=m._malloc(n),ap=m._malloc(8192);let go=-1,po=-1;
 function state(){assert(m._mgbawasm_state_save(sp));const b=Buffer.from(m.HEAPU8.buffer,sp,n);if(go<0)go=b.indexOf(Buffer.from('544c4150494e4d4f','hex'));if(po<0)po=b.indexOf(Buffer.from('53455250494e4d4f','hex'));assert(go>=0&&po>=0);return {screen:b.readUInt32LE(go+8),x:b.readUInt32LE(go+16),speed:b.readUInt32LE(po+8),scene:b.readUInt32LE(po+12),ticks:b.readUInt32LE(po+16),music:b.readUInt32LE(po+20),clock:b.readUInt32LE(po+28),cast:b.readUInt32LE(po+32),track:b.readUInt32LE(po+40),block:b.readUInt32LE(po+44),loops:b.readUInt32LE(po+48),chapter:b.readUInt32LE(po+52),letters:b.readUInt32LE(po+56),revealed:b.readUInt32LE(po+60)};}
 let auditing=false,walkFrames=0,lastAudio=null;const observedWalks=new Set(),blockingSamples=[],soundBridges=[];
 const grids=require('../build/pallet/opening-collision.json');
 function auditBlocking(){
  state();const b=Buffer.from(m.HEAPU8.buffer,sp,n),cueIndex=b.readUInt32LE(po+104),cue=cues[cueIndex];
  if(!cue)return;const grid=grids[cue.stage],count=b.readUInt32LE(po+68);
  const currentAudio={chapter:cue.chapter,track:b.readUInt32LE(po+40),block:b.readUInt32LE(po+44),loops:b.readUInt32LE(po+48)};
  if(lastAudio&&lastAudio.chapter!==cue.chapter&&cue.chapter<=3){
   assert.equal(currentAudio.track,4,'Meeting music must bridge the cut');
   assert(currentAudio.loops>lastAudio.loops||currentAudio.block>=lastAudio.block,'Music restarted at a room cut');
   soundBridges.push({before:lastAudio,after:currentAudio});
  }
  lastAudio=currentAudio;
  assert.equal(b.readUInt32LE(po+64),0,`Runtime blocked actor at cue ${cueIndex}`);
  const positions=[];
  for(let i=0;i<count;i++){
   const x=b.readInt32LE(po+72+i*8),y=b.readInt32LE(po+76+i*8);positions.push([x,y]);
   for(const [fx,fy] of [[x+2,y-12],[x+13,y-12],[x+2,y-1],[x+13,y-1]]){
    assert(fx>=0&&fy>=0&&fx<grid.width*16&&fy<grid.height*16,'Actor out of source room');
    assert.equal(grid.cells[Math.floor(fy/16)*grid.width+Math.floor(fx/16)],0,`Furniture overlap: cue ${cueIndex}, actor ${i}, (${x},${y})`);
   }
  }
  for(let i=0;i<count;i++)for(let j=i+1;j<count;j++)assert(Math.abs(positions[i][0]-positions[j][0])>=12||Math.abs(positions[i][1]-positions[j][1])>=12,'Actors overlap');
  if(cue.movement){walkFrames++;observedWalks.add(cueIndex);if(walkFrames%8===0)blockingSamples.push({cue:cueIndex,ticks:b.readUInt32LE(po+108),positions});}
 }
 const chunks=[];function frames(count,record=false){while(count--){m._mgbawasm_run_frame();let size;while((size=m._mgbawasm_read_audio(ap,2048))>0)if(record)chunks.push(Buffer.from(m.HEAPU8.slice(ap,ap+size*4)));if(auditing)auditBlocking();}}
 function press(k){m._mgbawasm_set_keys(k);frames(4);m._mgbawasm_set_keys(0);frames(12);}
 function shot(name){fs.writeFileSync(`build/pallet/${prefix}${name}.rgba`,Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600)));}
 function sram(){m._mgbawasm_sram_save();return Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));}
 frames(90);assert.equal(state().screen,storyMode?0:6);if(!storyMode)press(2);assert.equal(state().screen,0);shot('opening-title');
 const cues=require('../build/pallet/presentation-report.json').cues;
 const script=require('../content/opening/prologue.json');
 const before=sram();press(512);assert.equal(state().screen,14);
 let reveals=0,actions=0;const chapters=new Set();auditing=true;
 for(const cue of cues){
  assert.equal(state().scene,cue.cue,`Missing cue ${cue.cue}`);
  if(cue.dialogue){
   const total=script.scenes[cue.chapter].beats[cue.beat].lines.join('').length;
   const s=state();if(s.letters+6<total){press(1);assert.equal(state().scene,cue.cue,'First A must reveal text, not skip dialogue');++reveals;}
   frames(20);shot('cue-'+cue.cue);chapters.add(cue.chapter);press(1);
  }else{
   if(cue.duration>48){press(1);assert.equal(state().scene,cue.cue,'A must not teleport walking actors');++actions;}
   frames(8);shot('cue-'+cue.cue);
   let safety=cue.duration*2+90;while(state().screen===14&&state().scene===cue.cue&&safety-->0)frames(1);
   assert(safety>0,`Stuck action ${cue.cue}`);
  }
 }
 auditing=false;
 assert.equal(chapters.size,script.scenes.length);assert(reveals>30&&actions>10);assert.equal(state().screen,0);assert(before.equals(sram()),'Replay must not write SRAM');
 assert.equal(observedWalks.size,cues.filter(c=>c.movement).length,'Every walking/camera cue observed in actual ROM');
 assert.equal(soundBridges.length,3,'Three continuous musical scene transitions');
 fs.writeFileSync(`build/pallet/${prefix}opening-blocking-samples.json`,JSON.stringify({walkFrames,cues:[...observedWalks],soundBridges,samples:blockingSamples},null,2));
 press(512);press(8);assert.equal(state().screen,15);const paused=state().ticks;frames(100);assert.equal(state().ticks,paused);press(2);frames(12);assert.equal(state().screen,14,JSON.stringify(state()));press(8);press(1);assert.equal(state().screen,0);
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
  assert(rms>0.003,`BGM silent at ${speed}x`);assert(Math.abs((end.music-start.music)-elapsed*256)<=512,'Audio sample clock tied to accelerated simulation');
  rates.push({speed,hardware_ticks:elapsed,played_samples:end.music-start.music,samples:pcm.length/4,rms});
  if(speed===1)fs.writeFileSync('build/pallet/music-normal.pcm',pcm);
  press(4);
 }
 assert(rates.every(r=>Math.abs(r.played_samples-rates[0].played_samples)<=256),'Tempo differs across speeds');
 assert.equal(state().speed,1);shot('speed-normal');
 /* Record past a full Pallet loop, including every FIFO ring wrap. */
 frames(100);const audioStart=state();chunks.length=0;frames(3600,true);const audioEnd=state();
 assert.equal(audioEnd.track,1);assert(audioEnd.loops>audioStart.loops,'BGM must loop');
 fs.writeFileSync(`build/pallet/${prefix}music-loop.pcm`,Buffer.concat(chunks));
 fs.writeFileSync(`build/pallet/${prefix}music-loop.json`,JSON.stringify({start:audioStart,end:audioEnd,rate:m._mgbawasm_sample_rate()},null,2));
 /* Natural timeout also reaches bedroom; replay does not create a save. */
 m._mgbawasm_reset();go=po=-1;frames(90);if(!storyMode)press(2);press(512);frames(100);chunks.length=0;frames(600,true);fs.writeFileSync('build/pallet/music-opening.pcm',Buffer.concat(chunks));
 const seconds=cues.reduce((sum,c)=>sum+c.duration,0)/64;frames(Math.ceil(seconds*60));assert.equal(state().screen,0,'Automatic acted opening ends at title');
 const report={rom_sha256:crypto.createHash('sha256').update(rom).digest('hex'),scenes:chapters.size,cues:cues.length,text_reveal_checks:reveals,non_skippable_action_checks:actions,portraits:count,skip_cancel:true,replay_preserves_save:true,gallery_preserves_save:true,new_game_after_opening:true,automatic_advance:true,loop_verified:true,movement_tiles_in_12_frames:distances,audio_rate:m._mgbawasm_sample_rate(),speed_audio:rates,scope:'Archived classic source BGM through ADPCM/Direct Sound; independent in-game exploration speed. Arbitrary external emulator turbo is not controlled.'};
 fs.writeFileSync(`build/pallet/${prefix}presentation-test.json`,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
