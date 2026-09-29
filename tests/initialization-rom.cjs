/* Drive the actual ARM cartridge through its normal buttons. The passive EWRAM
 * probe is read from emulator snapshots; this test never writes game state. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const scenes=require('../build/pallet/scene-audit.json');for(const m of scenes)m.warps.push(...(m.extra_warps||[]));
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length);m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const size=m._mgbawasm_state_size(),sp=m._malloc(size),signature=Buffer.from('544c4150494e4d4f','hex');let probeOffset=-1,buttons=0,stopOnEncounter=false;
 const audioPtr=m._malloc(8192);function frames(n){while(n--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(audioPtr,2048)>0){}}}
 function state(){assert(m._mgbawasm_state_save(sp));const bytes=Buffer.from(m.HEAPU8.buffer,sp,size);if(probeOffset<0)probeOffset=bytes.indexOf(signature);assert(probeOffset>=0,'Game loop probe not initialized');const v=Array.from({length:35},(_,i)=>bytes.readUInt32LE(probeOffset+8+i*4));return {screen:v[0],map:v[1],x:v[2],y:v[3],direction:v[4],chapter:v[5],starter:v[6],menu:v[7],moving:v[8],hp:v[9],enemy:v[10],turns:v[11],potions:v[12],battles:v[13],party:v[14],events:v[15],balls:v[16],level:v[17],seq:v[18],beat:v[19],gary:v[20],garyX:v[21],garyY:v[22],storage:v[23],page:v[24],cursor:v[25],form:v[26],nature:v[27],spaEV:v[28],speedEV:v[29],enemyLevel:v[30],bond:v[31],opponents:v[32],opponentSlot:v[33],activeSpecies:v[34]};}
 function press(key){++buttons;m._mgbawasm_set_keys(key);frames(4);m._mgbawasm_set_keys(0);frames(16);return state();}
 function shot(name){const bytes=Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+240*160*4));fs.writeFileSync(`build/pallet/${name}.rgba`,bytes);}
 function portraitAt(x,y,index=0){
  const source=fs.readFileSync('build/pallet/cast.bin'),video=m._mgbawasm_video_ptr();let count=0;
  for(let row=0;row<80;row++)for(let col=0;col<80;col++){
   const color=source.readUInt16LE(index*12800+(row*80+col)*2);if(color&0x8000)continue;
   const pixel=video+((y+row)*240+x+col)*4;
   for(let c=0;c<3;c++)assert.equal(m.HEAPU8[pixel+c]>>3,(color>>(c*5))&31,`Portrait pixel ${col},${row},channel ${c}`);
   count++;
  }
  assert(count>500,'Native portrait must actually be visible');
 }
 function dismiss(){for(let i=0;state().screen===7&&i<200;i++)press(1);assert.notEqual(state().screen,7,'Dialogue did not finish');}
 function visible(a,s){if(a.person===3)return !!s.gary;if(a.person===19)return !(s.events&512);return !a.starter||!s.starter;}
 function walkable(map,x,y,s,goal){return x>=0&&y>=0&&x<map.width&&y<map.height&&!map.actors.some(a=>a.x===x&&a.y===y&&visible(a,s))&&(!map.collision[y*map.width+x]||(goal&&map.warps.some(w=>w.x===x&&w.y===y)));}
 function walk(x,y){
  let s=state();assert.equal(s.screen,1);const map=scenes[s.map-1],queue=[[s.x,s.y,[]]],visited=new Set([s.x+','+s.y]),dirs=[[0,1,128],[0,-1,64],[-1,0,32],[1,0,16]];let path;
  while(queue.length){const [cx,cy,p]=queue.shift();if(cx===x&&cy===y){path=p;break;}for(const [dx,dy,key] of dirs){const nx=cx+dx,ny=cy+dy,k=nx+','+ny,goal=nx===x&&ny===y;if(visited.has(k)||!walkable(map,nx,ny,s,goal)||(!goal&&map.warps.some(w=>w.x===nx&&w.y===ny)))continue;visited.add(k);queue.push([nx,ny,[...p,key]]);}}
  assert(path,`No walking path in map ${s.map} from ${s.x},${s.y} to ${x},${y}`);
  for(const key of path){const before=state();m._mgbawasm_set_keys(key);++buttons;let n=0;do{frames(1);s=state();}while(s.x===before.x&&s.y===before.y&&s.map===before.map&&++n<80);m._mgbawasm_set_keys(0);assert(n<80,`Blocked step ${key} from ${JSON.stringify(before)}`);n=0;do{frames(1);s=state();}while(s.moving&&++n<80);assert(n<80,'Walking animation stuck');frames(2);if(state().screen===10){if(stopOnEncounter)return state();press(2);dismiss();s=state();}}
  return state();
 }
 function face(dir){const keys=[128,64,32,16];const before=state();m._mgbawasm_set_keys(keys[dir]);for(let i=0;i<10&&state().direction!==dir;i++)frames(1);m._mgbawasm_set_keys(0);frames(4);assert.equal(state().x,before.x);assert.equal(state().y,before.y);}
 function talkAt(x,y,dir){walk(x,y);face(dir);press(1);}

 let walkSamples=0;const opponentsSeen=new Set();
 function dialogue(){for(let n=0;n<240;n++){const s=state();if(s.screen===7)press(1);else if(s.screen===21){const map=scenes[s.map-1];for(const dx of [2,13])for(const dy of [4,15]){const x=Math.floor((s.garyX+dx)/16),y=Math.floor((s.garyY+dy)/16);assert(!map.collision[y*map.width+x],'Gary walked into map furniture');}walkSamples++;frames(4);}else return;}throw Error('Story did not finish');}
 function battleFight(lose=false,slot=0){for(let n=0;n<1800;n++){const s=state();if(s.map===5&&s.opponents)opponentsSeen.add(s.opponentSlot);if(s.screen===11){press(1);continue;}if(s.screen!==10)return;
   if(lose){press(512);if(state().screen===11)continue;}
   if(s.page===0)press(1);else if(s.page===1){const target=lose?1:(slot===2&&s.activeSpecies!==25?0:slot);if((s.cursor^target)&1)press(16);if((s.cursor^target)&2)press(128);press(1);}else throw Error('Unexpected battle menu');
 }throw Error('Battle exceeded turn budget '+JSON.stringify(state()));}
 function snapshot(){assert(m._mgbawasm_state_save(sp));return Buffer.from(m.HEAPU8.slice(sp,sp+size));}
 function restore(b){m.HEAPU8.set(b,sp);assert(m._mgbawasm_state_load(sp));m._mgbawasm_set_keys(0);frames(2);}
 frames(90);press(256);assert.equal(state().screen,16);portraitAt(12,40);shot('init-ash-gallery');
 const portraits=require('../assets/characters/manifest.json').portraits;
 for(let i=0;i<portraits.length;i++){
  assert.equal(state().screen,16);portraitAt(12,40,i);shot('cast-review-'+portraits[i].actor);
  press(4);shot('cast-credit-'+portraits[i].actor);press(4);press(16);
 }
 portraitAt(12,40);press(2);
 press(2);press(1);press(8);press(1);shot('init-wake');dialogue();assert.equal(state().screen,1);assert(state().events&512);
 press(8);for(let i=0;i<3;i++)press(128);press(1);assert.equal(state().screen,5);portraitAt(148,24);shot('init-ash-trainer');press(2);press(2);assert.equal(state().screen,1);
 walk(10,2);walk(4,8);walk(16,13);assert.equal(state().map,5);
 talkAt(3,10,0);shot('init-paper');dialogue();
 walk(11,2);assert.equal(state().map,10);shot('init-servers');talkAt(1,4,1);shot('init-server-model');dialogue();walk(6,13);assert.equal(state().map,5);
 talkAt(6,4,1);shot('init-oak');dialogue();assert.equal(state().screen,10);assert.equal(state().party,4);assert.equal(state().balls,100);assert.equal(state().form,1);assert.equal(state().bond,1);assert.equal(state().enemyLevel,8);assert.equal(state().opponents,3);shot('init-gary-battle');
 const garyStart=snapshot();battleFight(true);shot('init-gary-loss');dialogue();assert.equal(state().screen,1);assert(state().events&32);assert.equal(state().map,5);
 restore(garyStart);battleFight(false,2);shot('init-gary-win');assert.deepEqual([...opponentsSeen].sort(),[0,1,2]);dialogue();assert.equal(state().screen,1);assert(state().events&32);assert(!state().gary);assert.equal(state().balls,100);
 press(8);press(128);press(1);shot('init-partner-team');press(1);shot('init-partner-dex');press(2);press(2);press(2);press(2);assert.equal(state().screen,1);
 // Gift dialogue cannot duplicate the four partners or the initial 100 balls.
 press(1);dialogue();assert.equal(state().party,4);assert.equal(state().balls,100);
 press(8);press(128);press(128);press(1);for(let i=0;i<4;i++)press(16);shot('init-toolkit');assert.equal(state().screen,4);
 press(128);press(1);assert.equal(state().screen,19);shot('init-mint');press(128);press(1);dialogue();assert.equal(state().screen,19);assert.equal(state().nature,11);press(2);
 press(128);press(128);press(128);press(1);assert.equal(state().screen,19);shot('init-ev');press(128);press(128);press(128);press(4);assert.equal(state().spaEV,0);press(1);assert.equal(state().spaEV,252);press(2);press(2);press(2);
 walk(6,12);assert.equal(state().map,1);walk(12,0);press(64);assert.equal(state().map,6);walk(12,0);press(64);assert.equal(state().map,7);shot('init-viridian');
 talkAt(20,10,1);dialogue();assert.equal(state().screen,18);const oldChoice=snapshot();shot('init-old-choice');
 press(1);dialogue();assert.equal(state().screen,10);assert.equal(state().enemyLevel,3);shot('init-capture-lesson');
 press(16);press(1);assert.equal(state().screen,4);shot('init-tutorial-bag');press(2);press(256);dialogue();assert.equal(state().screen,1);assert(state().events&64);assert.equal(state().party,5);assert.equal(state().balls,100);shot('init-weedle-gift');
 press(1);dialogue();assert.equal(state().party,5);const yesEnd=snapshot();
 restore(oldChoice);press(128);press(1);dialogue();assert.equal(state().screen,10);battleFight();shot('init-old-win');dialogue();assert(state().events&64);assert.equal(state().party,5);assert.equal(state().balls,100);
 restore(yesEnd);
 // Preserve the authored next step: the classic shop parcel, without forcing
 // the withdrawn prototype Rocket encounter into this opening.
 walk(26,26);talkAt(6,4,1);dialogue();assert(state().events&1);walk(7,8);
 walk(36,19);talkAt(4,3,2);dialogue();assert.equal(state().screen,13);assert(state().events&4);press(1);dialogue();assert.equal(state().balls,101);press(2);walk(4,7);
 walk(24,39);press(128);walk(12,39);press(128);walk(16,13);talkAt(6,4,1);dialogue();assert(state().events&8);const parcelBalls=state().balls;press(1);dialogue();assert.equal(state().balls,parcelBalls);
 press(8);for(let i=0;i<4;i++)press(128);press(1);dialogue();press(2);
 m._mgbawasm_sram_save();const saved=Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));fs.writeFileSync('build/pallet/initialization.sav',saved);assert(require('../adapters/pokedex-preview/pallet-save.js')(saved,scenes));
 const legacy=require('./legacy-pallet-save.cjs')(saved);assert(require('../adapters/pokedex-preview/pallet-save.js')(legacy,scenes));fs.writeFileSync('build/pallet/test-game.sav',legacy);
 m._mgbawasm_reset();probeOffset=-1;frames(90);press(2);press(1);frames(20);assert.equal(state().party,5);assert.equal(state().form,1);assert.equal(state().nature,11);assert(state().events&64);shot('init-continued');
 const corrupt=Buffer.from(saved),latest=corrupt.readUInt32LE(4)>corrupt.readUInt32LE(16388)?0:16384;corrupt[latest+60]^=255;const sv=m._malloc(corrupt.length);m.HEAPU8.set(corrupt,sv);m._mgbawasm_sram_load(sv,corrupt.length);m._free(sv);m._mgbawasm_reset();probeOffset=-1;frames(90);press(2);press(1);assert.equal(state().party,5,'Corrupt newest slot falls back');assert.equal(state().form,1);
 const report={pass:true,rom:crypto.createHash('sha256').update(rom).digest('hex'),buttons,nativeAshGallery:true,nativeAshTrainerCard:true,garyWin:true,garyLoss:true,walkSamples,serverRoom:true,partnerExclusiveMove:true,toolPersistence:true,tutorialR:true,oldManDuel:true,onceOnlyGifts:true,parcel:true,saveContinue:true,corruptSlotFallback:true};fs.writeFileSync('build/pallet/initialization-report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
 m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
