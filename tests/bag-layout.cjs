/* Isolated SRAM fixtures exercise display limits. They are never installed in
 * the user's browser save. Every screen is reached through normal ROM buttons. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const valid=require('../adapters/pokedex-preview/pallet-save.js');
const maps=require('../build/pallet/scene-audit.json');
const hash=b=>{let h=2166136261;for(const v of b)h=Math.imul(h^v,16777619)>>>0;return h;};
function fixture(quantity,parcel){
 const bytes=Buffer.from(fs.readFileSync('build/pallet/test-game.sav'));
 for(const base of [0,16384]){
  const p=base+20,a=p+16,n=bytes.readUInt32LE(base+8);
  bytes.writeUInt16LE(quantity,a+18);bytes.writeUInt16LE(quantity,a+20);
  bytes.writeUInt16LE(parcel?4:12,a+22);bytes.writeUInt32LE(999999,a+24);
  const checksumOffset=bytes.readUInt32LE(a+4)===3?136:128;
  bytes.writeUInt32LE(hash(bytes.subarray(a,a+checksumOffset)),a+checksumOffset);
  bytes.writeUInt32LE(hash(bytes.subarray(p,p+n)),base+12);
  bytes.writeUInt32LE(hash(bytes.subarray(base,base+16)),base+16);
 }
 assert(valid(bytes,maps),'Fixture must pass the same transport validation as a real save');return bytes;
}
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});
 m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length);
 m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const audioPtr=m._malloc(8192);
 const frames=n=>{while(n--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(audioPtr,2048)>0){}}};
 const press=k=>{m._mgbawasm_set_keys(k);frames(4);m._mgbawasm_set_keys(0);frames(16);};
 const stateSize=m._mgbawasm_state_size(),statePtr=m._malloc(stateSize),signature=Buffer.from('544c4150494e4d4f','hex');
 function checkBag(quantity){assert(m._mgbawasm_state_save(statePtr));const bytes=Buffer.from(m.HEAPU8.buffer,statePtr,stateSize),probe=bytes.indexOf(signature);assert(probe>=0);assert.equal(bytes.readUInt32LE(probe+8),4,'Normal buttons must reach the bag');assert.equal(bytes.readUInt32LE(probe+56),quantity,'SRAM fixture must be loaded, not a fresh adventure');assert.equal(bytes.readUInt32LE(probe+72),quantity);}
 function shot(name){fs.writeFileSync(`build/pallet/${name}.rgba`,m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+240*160*4));}
 // Let mGBA detect/initialize this cartridge's SRAM before importing fixtures.
 frames(90);
 for(const quantity of [9,99,999,0]){
  const save=fixture(quantity,quantity>0),p=m._malloc(save.length);m.HEAPU8.set(save,p);m._mgbawasm_sram_load(p,save.length);m._free(p);m._mgbawasm_reset();frames(90);
  press(2);press(1);press(8);press(128);press(128);press(1);
  checkBag(quantity);
  shot(`bag-layout-items-${quantity}`);
  if(quantity){press(128);shot(`bag-layout-close-${quantity}`);press(64);}
  press(16);shot(`bag-layout-balls-${quantity}`);
  press(16);shot(`bag-layout-tms-${quantity}`);press(16);shot(`bag-layout-berries-${quantity}`);
  press(16);shot(`bag-layout-key-${quantity}`);
  press(16);shot(`bag-layout-wrap-${quantity}`);press(32);shot(`bag-layout-back-${quantity}`);
 }
 m._mgbawasm_unload();console.log('PASS: bag layout fixtures rendered in real ROM (0/9/99/999, five pockets, wrap/back, parcel, close; balance must remain invisible)');
})().catch(e=>{console.error(e);process.exitCode=1;});
