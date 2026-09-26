/* Exercise the actual cartridge, including legacy SRAM and held-key boundaries. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const valid=require('../adapters/pokedex-preview/pallet-save.js'),maps=require('../build/pallet/scene-audit.json');
const hash=b=>{let h=2166136261;for(const c of b)h=Math.imul(h^c,16777619)>>>0;return h;};
function legacyV2(source){
 const out=Buffer.alloc(32768,255);
 for(const slot of [0,16384]){
  const p=slot+20,a=p+16,n=source.readUInt32LE(slot+8),dex=source.subarray(p+156,p+n);
  const payload=Buffer.alloc(148+dex.length);source.copy(payload,0,p,p+148);
  payload.writeUInt32LE(1,4);payload.writeUInt32LE(2,20);
  payload.writeUInt32LE(hash(payload.subarray(16,144)),144);dex.copy(payload,148);
  const header=Buffer.from(source.subarray(slot,slot+20));header.writeUInt32LE(payload.length,8);
  header.writeUInt32LE(hash(payload),12);header.writeUInt32LE(hash(header.subarray(0,16)),16);
  header.copy(out,slot);payload.copy(out,p);
 }
 return out;
}
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});
 m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const debug=process.argv.includes('--debug');
 const rom=fs.readFileSync(debug?'build/pallet-debug/omni-pallet.gba':'build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length),ap=m._malloc(8192);
 m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const n=m._mgbawasm_state_size(),sp=m._malloc(n);let offset=-1;
 function frames(n){while(n--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(ap,2048)>0){}}}
 function state(){assert(m._mgbawasm_state_save(sp));const b=Buffer.from(m.HEAPU8.buffer,sp,n);if(offset<0)offset=b.indexOf(Buffer.from('544c4150494e4d4f','hex'));assert(offset>=0);return {screen:b.readUInt32LE(offset+8),cursor:b.readUInt32LE(offset+36),events:b.readUInt32LE(offset+68)};}
 function press(k){m._mgbawasm_set_keys(k);frames(4);m._mgbawasm_set_keys(0);frames(28);return state();}
 function pixels(){return Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600));}
 function shot(name){fs.writeFileSync(`build/pallet/start-${name}.rgba`,pixels());}
 function sram(){m._mgbawasm_sram_save();return Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));}
 function reset(save){if(save){const p=m._malloc(save.length);m.HEAPU8.set(save,p);m._mgbawasm_sram_load(p,save.length);m._free(p);}m._mgbawasm_set_keys(0);m._mgbawasm_reset();offset=-1;frames(90);if(debug){assert.equal(state().screen,6);press(2);}assert.equal(state().screen,17);}
 frames(90);if(debug){assert.equal(state().screen,6);press(2);}assert.equal(state().screen,17);const empty=sram();
 // Capture both real blinking prompt phases, leaving art unchanged.
 const title=fs.readFileSync('build/pallet/title.bin');
 const [tx,ty,tw,th]=require('../assets/source/title-screen.json').prompt_layout;
 const rgba=c=>[c&31,(c>>5)&31,(c>>10)&31].map(v=>(v<<3)|(v>>2)).concat(255);
 const off=Buffer.alloc(240*160*4);
 for(let i=0;i<240*160;i++)off.set(rgba(title.readUInt16LE(i*2)),i*4);
 const on=Buffer.from(off);
 for(let y=0;y<th;y++)for(let x=0;x<tw;x++){
  const c=title.readUInt16LE(240*160*2+(y*tw+x)*2);
  if(!(c&0x8000))on.set(rgba(c),((ty+y)*240+tx+x)*4);
 }
 assert(!on.equals(off),'Prompt must be visible against new cover');
 let lit=null,dark=null;
 for(let i=0;i<130;i++){
  frames(1);const b=pixels();
  assert(b.equals(on)||b.equals(off),'Cover must match compiled art with only the prompt blinking');
  if(b.equals(on))lit=b;else dark=b;
 }
 assert(lit&&dark,'Both prompt phases must occur');
 fs.writeFileSync('build/pallet/start-cover.rgba',lit);
 for(const key of [1,2,8]){
  press(key);assert.equal(state().screen,0);shot('empty');assert(empty.equals(sram()));
  press(2);assert.equal(state().screen,17);
 }
 // A held from the cover must never select New Game in the next screen.
 m._mgbawasm_set_keys(1);frames(150);assert.equal(state().screen,0);m._mgbawasm_set_keys(0);frames(20);assert(empty.equals(sram()));
 press(1);assert.equal(state().screen,14);assert(empty.equals(sram()));
 press(8);press(1);assert.equal(state().screen,7);assert(valid(sram(),maps));press(1);assert.equal(state().screen,1);
 frames(130);press(8);for(let i=0;i<4;i++)press(128);press(1);press(1);press(2);
 const timed=sram();let newest=timed.readUInt32LE(4)>timed.readUInt32LE(16388)?0:16384;
 assert(timed.readUInt32LE(newest+20+16+128)>=2,'Real play time is serialized');
 const modern=fs.readFileSync('build/pallet/test-game.sav'),old=legacyV2(modern);assert(valid(old,maps));
 fs.writeFileSync('build/pallet/test-game-v2.sav',old);
 for(const save of [modern,old]){
  reset(save);press(2);assert.equal(state().screen,0);assert.equal(state().cursor,0);shot('continue');
  press(128);assert.equal(state().cursor,1);shot('new');press(1);assert.equal(state().screen,12);shot('overwrite');
  press(2);assert.equal(state().screen,0);assert(save.equals(sram()),'Cancelled overwrite must preserve both save slots');
  press(2);assert.equal(state().screen,17);press(1);assert.equal(state().cursor,0);press(1);assert.equal(state().screen,1);assert.equal(state().events,15);
 }
 reset(modern);press(4);assert.equal(state().screen,6);shot('debug-dex');press(2);assert.equal(state().screen,17);assert(modern.equals(sram()));
 m._mgbawasm_set_keys(4);frames(150);m._mgbawasm_set_keys(0);frames(20);
 press(2);assert.equal(state().screen,17,'Holding the shortcut must not open the Dex filter');
 const invalid=Buffer.alloc(32768);reset(invalid);press(1);assert.equal(state().screen,0);press(128);assert.equal(state().cursor,0);
 console.log('PASS: native cover blink, A/B/START, held-key guard, empty/valid/invalid saves, v2 migration, real play clock, overwrite cancel, direct debug Dex');
 m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
