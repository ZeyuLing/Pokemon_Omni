/* Drive the actual ARM cartridge through its normal buttons. The passive EWRAM
 * probe is read from emulator snapshots; this test never writes game state. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const scenes=require('../build/pallet/scene-audit.json');
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length);m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const size=m._mgbawasm_state_size(),sp=m._malloc(size),signature=Buffer.from('544c4150494e4d4f','hex');let probeOffset=-1,buttons=0;
 function frames(n){while(n--)m._mgbawasm_run_frame();}
 function state(){assert(m._mgbawasm_state_save(sp));const bytes=Buffer.from(m.HEAPU8.buffer,sp,size);if(probeOffset<0)probeOffset=bytes.indexOf(signature);assert(probeOffset>=0,'Game loop probe not initialized');const v=Array.from({length:14},(_,i)=>bytes.readUInt32LE(probeOffset+8+i*4));return {screen:v[0],map:v[1],x:v[2],y:v[3],direction:v[4],chapter:v[5],starter:v[6],menu:v[7],moving:v[8],hp:v[9],enemy:v[10],turns:v[11],potions:v[12],battles:v[13]};}
 function press(key){++buttons;m._mgbawasm_set_keys(key);frames(4);m._mgbawasm_set_keys(0);frames(16);return state();}
 function shot(name){const bytes=Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+240*160*4));fs.writeFileSync(`build/pallet/${name}.rgba`,bytes);}
 function dismiss(){for(let i=0;state().screen===7&&i<20;i++)press(1);assert.notEqual(state().screen,7,'Dialogue did not finish');}
 function visible(a,s){return !a.starter||!s.starter||(a.starter!==s.starter&&a.starter!==s.starter%3+1);}
 function walkable(map,x,y,s,goal){return x>=0&&y>=0&&x<map.width&&y<map.height&&!map.actors.some(a=>a.x===x&&a.y===y&&visible(a,s))&&(!map.collision[y*map.width+x]||(goal&&map.warps.some(w=>w.x===x&&w.y===y)));}
 function walk(x,y){
  let s=state();assert.equal(s.screen,1);const map=scenes[s.map-1],queue=[[s.x,s.y,[]]],visited=new Set([s.x+','+s.y]),dirs=[[0,1,128],[0,-1,64],[-1,0,32],[1,0,16]];let path;
  while(queue.length){const [cx,cy,p]=queue.shift();if(cx===x&&cy===y){path=p;break;}for(const [dx,dy,key] of dirs){const nx=cx+dx,ny=cy+dy,k=nx+','+ny,goal=nx===x&&ny===y;if(visited.has(k)||!walkable(map,nx,ny,s,goal)||(!goal&&map.warps.some(w=>w.x===nx&&w.y===ny)))continue;visited.add(k);queue.push([nx,ny,[...p,key]]);}}
  assert(path,`No walking path in map ${s.map} from ${s.x},${s.y} to ${x},${y}`);
  for(const key of path){const before=state();m._mgbawasm_set_keys(key);++buttons;let n=0;do{frames(1);s=state();}while(s.x===before.x&&s.y===before.y&&s.map===before.map&&++n<80);m._mgbawasm_set_keys(0);assert(n<80,`Blocked step ${key} from ${JSON.stringify(before)}`);n=0;do{frames(1);s=state();}while(s.moving&&++n<80);assert(n<80,'Walking animation stuck');frames(2);}
  return state();
 }
 function face(dir){const keys=[128,64,32,16];const before=state();m._mgbawasm_set_keys(keys[dir]);for(let i=0;i<10&&state().direction!==dir;i++)frames(1);m._mgbawasm_set_keys(0);frames(4);assert.equal(state().x,before.x);assert.equal(state().y,before.y);}
 function talkAt(x,y,dir){walk(x,y);face(dir);press(1);}
 frames(90);assert.equal(state().screen,0);shot('title');press(1);shot('intro');dismiss();assert.equal(state().map,3);shot('bedroom');
 // Open the real menu before receiving the Dex; its gate must hold.
 press(8);press(1);assert.equal(state().screen,7);dismiss();press(2);assert.equal(state().screen,1);
 talkAt(1,2,1);dismiss();assert.equal(state().potions,1);press(1);dismiss();assert.equal(state().potions,1,'PC reward cannot be repeated');
 walk(10,2);assert.equal(state().map,2);shot('home');talkAt(8,5,1);assert.equal(state().screen,7);dismiss();
 walk(4,8);assert.equal(state().map,1);shot('town');walk(16,13);assert.equal(state().map,5);shot('lab');
 talkAt(6,4,1);assert.equal(state().chapter,1);dismiss();talkAt(8,5,1);assert.equal(state().screen,9);shot('starter-choice');press(1);assert.equal(state().starter,1);assert.equal(state().potions,4);dismiss();
 press(8);press(128);press(1);assert.equal(state().screen,3);shot('party');press(1);assert.equal(state().screen,6);shot('in-game-dex');press(2);press(2);assert.equal(state().screen,3);press(2);press(2);
 talkAt(5,5,1);dismiss();assert.equal(state().screen,8);press(1);assert.equal(state().screen,10);shot('battle');
 for(let i=0;i<30&&state().battles===0;i++){if(state().screen===10)press(1);while(state().screen===11)press(1);}
 assert.equal(state().battles,1);assert.equal(state().chapter,3);shot('battle-result');dismiss();
 // Save from START, reset the emulator and continue: game and Dex travel together.
 press(8);for(let i=0;i<4;i++)press(128);press(1);assert.equal(state().screen,7);dismiss();press(2);
 m._mgbawasm_sram_save();const saved=Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));fs.writeFileSync('build/pallet/test-game.sav',saved);
 const validGame=require('../adapters/pokedex-preview/pallet-save.js');assert(validGame(saved,scenes));assert(!validGame(Buffer.alloc(32768),scenes));assert(!require('../adapters/pokedex-preview/gba-save.js')(saved));
 m._mgbawasm_reset();probeOffset=-1;frames(90);assert.equal(state().screen,0);press(1);assert.equal(state().map,5);assert.equal(state().chapter,3);assert.equal(state().starter,1);assert.equal(state().battles,1);shot('continued');
 // Return outdoors, enter the rival home, then home and upstairs; all warps work.
 walk(6,12);assert.equal(state().map,1);walk(15,7);assert.equal(state().map,4);shot('rival-home');talkAt(10,7,1);dismiss();walk(4,8);assert.equal(state().map,1);walk(6,7);assert.equal(state().map,2);walk(10,2);assert.equal(state().map,3);
 // Latest committed slot corrupted -> previous real game checkpoint remains usable.
 const latest=saved.readUInt32LE(4)>saved.readUInt32LE(16388)?0:16384;saved[latest+60]^=255;const sv=m._malloc(saved.length);m.HEAPU8.set(saved,sv);m._mgbawasm_sram_load(sv,saved.length);m._free(sv);m._mgbawasm_reset();probeOffset=-1;frames(90);press(1);assert.equal(state().starter,1);assert.equal(state().chapter,3);
 const report={rom_sha256:crypto.createHash('sha256').update(rom).digest('hex'),emulator:'@wasm-gaming/mgba-wasm@0.1.1',maps_visited:5,normal_button_inputs:buttons,starter_acquisition:true,menu_dex_gate:true,party_and_integrated_dex:true,practice_battle:true,save_continue:true,corrupt_newest_slot_fallback:true};
 fs.writeFileSync('build/pallet/emulator-report.json',JSON.stringify(report,null,2)+'\n');console.log('PASS: playable Pallet opening, five maps/warps, NPCs, starter, party + in-game Dex, battle, save/continue and corrupt-slot fallback');m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
