/* Isolated SRAM fixture; normal buttons verify item targets and party swaps. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const hash=b=>{let h=2166136261;for(const v of b)h=Math.imul(h^v,16777619)>>>0;return h;};
(async()=>{
 const d=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(d,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(d,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length);m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const ap=m._malloc(8192),sp=m._malloc(m._mgbawasm_state_size());
 function frames(n){while(n--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(ap,2048)>0){}}}
 function press(k){m._mgbawasm_set_keys(k);frames(4);m._mgbawasm_set_keys(0);frames(20);}
 function screen(){m._mgbawasm_state_save(sp);const b=Buffer.from(m.HEAPU8.buffer,sp,m._mgbawasm_state_size()),at=b.indexOf(Buffer.from('544c4150494e4d4f','hex'));assert(at>=0);return b.readUInt32LE(at+8);}
 function adventure(){m._mgbawasm_sram_save();const b=Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768)),base=b.readUInt32LE(4)>b.readUInt32LE(16388)?0:16384;return b.subarray(base+36,base+36+916);}
 frames(90);
 const fixture=Buffer.from(fs.readFileSync('build/pallet/initialization.sav'));
 for(const base of [0,16384]){const a=base+36,n=fixture.readUInt32LE(base+8);fixture.writeUInt16LE(5,a+18);fixture.writeUInt16LE(1,a+36);fixture.writeUInt16LE(1,a+52);fixture.writeUInt32LE(hash(fixture.subarray(a,a+912)),a+912);fixture.writeUInt32LE(hash(fixture.subarray(base+20,base+20+n)),base+12);fixture.writeUInt32LE(hash(fixture.subarray(base,base+16)),base+16);}
 assert(require('../adapters/pokedex-preview/pallet-save.js')(fixture,require('../build/pallet/scene-audit.json')));
 const p=m._malloc(fixture.length);m.HEAPU8.set(fixture,p);m._mgbawasm_sram_load(p,fixture.length);m._free(p);m._mgbawasm_reset();frames(90);press(2);press(1);assert.equal(screen(),1);
 press(8);press(128);press(128);press(1);assert.equal(screen(),4);
 press(1);press(2);assert.equal(screen(),4);assert.equal(adventure().readUInt16LE(18),5,'Cancel must not consume the item');
 press(1);press(1);assert.equal(screen(),3);press(128);press(1);for(let i=0;i<8&&screen()===7;i++)press(1);assert.equal(screen(),4);
 const healed=adventure();assert.equal(healed.readUInt16LE(18),4);assert.equal(healed.readUInt16LE(36),1,'First mon must remain injured');assert(healed.readUInt16LE(52)>1,'Chosen second mon must be healed');
 press(2);press(64);press(1);assert.equal(screen(),3);press(1);press(128);press(1);press(128);press(128);press(1);
 const swapped=adventure();assert.equal(swapped.readUInt16LE(32),healed.readUInt16LE(64));assert.equal(swapped.readUInt16LE(64),healed.readUInt16LE(32));assert.equal(swapped.readUInt16LE(68),1);
 console.log('PASS: real ROM source party menu, item cancellation, selected-target healing, arbitrary slot exchange and v6 save transport');
})().catch(e=>{console.error(e);process.exitCode=1;});
