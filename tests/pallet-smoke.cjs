/* Drive the actual ARM cartridge through its normal buttons. The passive EWRAM
 * probe is read from emulator snapshots; this test never writes game state. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const scenes=require('../build/pallet/scene-audit.json');
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length);m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const size=m._mgbawasm_state_size(),sp=m._malloc(size),signature=Buffer.from('544c4150494e4d4f','hex');let probeOffset=-1,buttons=0,stopOnEncounter=false;
 function frames(n){while(n--)m._mgbawasm_run_frame();}
 function state(){assert(m._mgbawasm_state_save(sp));const bytes=Buffer.from(m.HEAPU8.buffer,sp,size);if(probeOffset<0)probeOffset=bytes.indexOf(signature);assert(probeOffset>=0,'Game loop probe not initialized');const v=Array.from({length:18},(_,i)=>bytes.readUInt32LE(probeOffset+8+i*4));return {screen:v[0],map:v[1],x:v[2],y:v[3],direction:v[4],chapter:v[5],starter:v[6],menu:v[7],moving:v[8],hp:v[9],enemy:v[10],turns:v[11],potions:v[12],battles:v[13],party:v[14],events:v[15],balls:v[16],level:v[17]};}
 function press(key){++buttons;m._mgbawasm_set_keys(key);frames(4);m._mgbawasm_set_keys(0);frames(16);return state();}
 function shot(name){const bytes=Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+240*160*4));fs.writeFileSync(`build/pallet/${name}.rgba`,bytes);}
 function dismiss(){for(let i=0;state().screen===7&&i<20;i++)press(1);assert.notEqual(state().screen,7,'Dialogue did not finish');}
 function visible(a,s){return !a.starter||!s.starter;}
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

 frames(90);assert.equal(state().screen,6,'Debug boot still opens Dex');press(2);assert.equal(state().screen,0);shot('title');press(1);dismiss();assert.equal(state().map,3);shot('bedroom');
 press(8);press(1);assert.equal(state().screen,6);press(2);press(2);assert.equal(state().screen,1);
 talkAt(1,2,1);dismiss();assert.equal(state().potions,1);press(1);dismiss();assert.equal(state().potions,1);
 walk(10,2);assert.equal(state().map,2);talkAt(8,5,1);dismiss();walk(4,8);assert.equal(state().map,1);walk(16,13);assert.equal(state().map,5);
 talkAt(6,4,1);dismiss();talkAt(8,5,1);assert.equal(state().screen,9);shot('pikachu-choice');press(1);dismiss();assert.equal(state().starter,4);assert.equal(state().party,1);assert.equal(state().balls,5);shot('pikachu-lab');
 press(8);press(128);press(1);assert.equal(state().screen,3);shot('pikachu-party');press(1);assert.equal(state().screen,6);press(2);press(2);assert.equal(state().screen,3);press(2);press(2);
 press(8);press(128);press(128);press(1);assert.equal(state().screen,4);shot('bag-items');press(16);shot('bag-balls');press(16);shot('bag-key-empty');press(2);press(2);
 walk(6,12);walk(12,0);press(64);assert.equal(state().map,6);shot('route1');
 const route=scenes[5];let pair;
 for(let y=1;y<route.height-1&&!pair;y++)for(let x=1;x<route.width-2;x++)if(route.grass[y*route.width+x]&&route.grass[y*route.width+x+1]&&!route.collision[y*route.width+x]&&!route.collision[y*route.width+x+1]){pair=[[x,y],[x+1,y]];break;}
 assert(pair);stopOnEncounter=true;
 for(let i=0;i<150&&state().screen!==10;i++)walk(...pair[i%2]);assert.equal(state().screen,10);shot('wild-battle');press(1);shot('battle-moves');press(2);press(16);press(1);assert.equal(state().screen,4);shot('battle-bag');press(1);while(state().screen===11)press(1);if(state().screen===7)dismiss();
 for(let i=0;i<5&&state().party===1;i++){press(512);while(state().screen===11)press(1);if(state().screen===7)dismiss();}
 assert.equal(state().party,2,'Capture adds a second partner');shot('caught');stopOnEncounter=false;
 walk(12,0);press(64);assert.equal(state().map,7);shot('viridian');walk(26,26);assert.equal(state().map,8);shot('center');
 talkAt(6,4,1);dismiss();assert(state().events&1);talkAt(10,5,3);dismiss();assert.equal(state().screen,8);press(1);assert.equal(state().screen,10);shot('rocket-battle');
 press(128);press(1);shot('battle-party');press(2);press(128);press(16);press(1);assert.equal(state().screen,4);press(1);assert.equal(state().screen,11,'Trainer capture rejected');press(1);assert.equal(state().screen,10);press(32);
 for(let attempt=0;attempt<4&&!(state().events&2);attempt++){
  for(let t=0;t<90&&(state().screen===10||state().screen===11);t++)press(1);
  if(state().screen===7)dismiss();
  if(!(state().events&2)){assert.equal(state().map,2);walk(4,8);walk(12,0);press(64);walk(12,0);press(64);walk(26,26);talkAt(6,4,1);dismiss();talkAt(10,5,3);dismiss();press(1);}
 }
 assert(state().events&2,'Rocket encounter resolved by winning');shot('rocket-cleared');talkAt(6,4,1);dismiss();walk(7,8);assert.equal(state().map,7);
 walk(36,19);assert.equal(state().map,9);talkAt(4,3,2);dismiss();assert.equal(state().screen,13);assert(state().events&4);const balls=state().balls;press(1);dismiss();assert.equal(state().balls,balls+1);shot('shop');press(2);walk(4,7);assert.equal(state().map,7);
 walk(24,39);press(128);assert.equal(state().map,6);walk(12,39);press(128);assert.equal(state().map,1);walk(16,13);talkAt(6,4,1);dismiss();assert.equal(state().events,15);const rewardBalls=state().balls;press(1);dismiss();assert.equal(state().balls,rewardBalls,'Parcel reward once');shot('parcel-return');
 press(8);for(let i=0;i<4;i++)press(128);press(1);dismiss();press(2);
 m._mgbawasm_sram_save();const saved=Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));fs.writeFileSync('build/pallet/test-game.sav',saved);
 const validGame=require('../adapters/pokedex-preview/pallet-save.js');assert(validGame(saved,scenes));assert(!validGame(Buffer.alloc(32768),scenes));assert(!require('../adapters/pokedex-preview/gba-save.js')(saved));
 m._mgbawasm_reset();probeOffset=-1;frames(90);press(2);press(1);assert.equal(state().starter,4);assert.equal(state().events,15);assert.equal(state().party,2);shot('continued');
 const latest=saved.readUInt32LE(4)>saved.readUInt32LE(16388)?0:16384;saved[latest+60]^=255;const sv=m._malloc(saved.length);m.HEAPU8.set(saved,sv);m._mgbawasm_sram_load(sv,saved.length);m._free(sv);m._mgbawasm_reset();probeOffset=-1;frames(90);press(2);press(1);assert.equal(state().events,15,'Corrupt newest slot falls back');
 let legacy=false;const oldPath='.cache/pallet-before-kanto.sav';
 if(fs.existsSync(oldPath)){const old=fs.readFileSync(oldPath),ver=old.readUInt32LE(40);if(ver===1){assert(validGame(old,scenes));const ptr=m._malloc(old.length);m.HEAPU8.set(old,ptr);m._mgbawasm_sram_load(ptr,old.length);m._free(ptr);m._mgbawasm_reset();probeOffset=-1;frames(90);press(2);press(1);assert(state().starter>=1&&state().starter<=3);assert.equal(state().party,1);legacy=true;}}
 const report={rom_sha256:crypto.createHash('sha256').update(rom).digest('hex'),emulator:'@wasm-gaming/mgba-wasm@0.1.1',maps_visited:8,normal_button_inputs:buttons,pikachu:true,route_connections:true,wild_capture:true,rocket_encounter:true,trainer_capture_rejected:true,shop:true,parcel_once:true,party_and_dex:true,native_battle_commands:true,bag_pockets:true,party_selection:true,save_continue:true,corrupt_slot_fallback:true,legacy_v1_import:legacy,scope:'Opening through Viridian and parcel return; not the completed Kanto first journey'};
 fs.writeFileSync('build/pallet/emulator-report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
