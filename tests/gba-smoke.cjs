/* Run the actual ARM ROM in mGBA's WebAssembly core, without a browser UI. */
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto'),path=require('node:path');
const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
const create=require(path.join(dir,'mgba.cjs'));
(async()=>{
 const m=await create({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});
 m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/gba/omni-dex.gba'),ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
 assert(m._mgbawasm_load(ptr,rom.length,0,0,0,0,1));m._free(ptr);
 const frames=(n=30)=>{for(let i=0;i<n;i++)m._mgbawasm_run_frame();};
 const press=(key)=>{m._mgbawasm_set_keys(key);frames(8);m._mgbawasm_set_keys(0);frames(20);};
 const shot=name=>{const ptr=m._mgbawasm_video_ptr(),w=m._mgbawasm_video_width(),h=m._mgbawasm_video_height();assert.equal(w,240);assert.equal(h,160);const bytes=Buffer.from(m.HEAPU8.slice(ptr,ptr+w*h*4));fs.writeFileSync('build/gba/'+name+'.rgba',bytes);return crypto.createHash('sha256').update(bytes).digest('hex');};
 frames(60);const boot=shot('boot');press(1);const detail=shot('detail');assert.notEqual(detail,boot);
 press(16);shot('moves');press(16);shot('training');press(2);
 press(8);press(4);press(256);shot('event-captured');
 const size=m._mgbawasm_sram_save();assert.equal(size,32768);let saved=Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+size));
 assert.equal(saved.subarray(0,3).toString(),'ODG');assert.equal(saved.subarray(20,24).toString(),'ODEX');assert.equal(saved.readUInt32LE(28),1);assert.equal(saved[36],3);
 fs.writeFileSync('build/gba/test-captured.sav',saved);
 press(512);const size2=m._mgbawasm_sram_save();saved=Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+size2));assert.equal(saved[16384+36],7);
 m._mgbawasm_reset();frames(60);shot('reload');
 // Corrupt the newest slot: the next boot must select the prior valid slot.
 saved[16384+20]^=255;const sp=m._malloc(saved.length);m.HEAPU8.set(saved,sp);m._mgbawasm_sram_load(sp,saved.length);m._free(sp);m._mgbawasm_reset();frames(60);shot('recovered');
 press(8);press(4);press(1);m._mgbawasm_sram_save();const recovered=Buffer.from(m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+32768));assert.equal(recovered[16384+36],3,'Fallback retained captured flag, rather than the invalid unlocked slot');
 press(2);press(4);for(let i=0;i<6;i++)press(16);press(1);shot('filtered-charizard');press(1);press(16);press(1);shot('move-detail');press(2);press(16);shot('charizard-plan');press(16);shot('charizard-evs');press(16);press(128);press(1);shot('charizard-form');
 const validate=require('../adapters/pokedex-preview/gba-save.js');assert(validate(recovered));assert(!validate(new Uint8Array(32768)));assert(!validate(new Uint8Array(10)));
 // Pixel regression against the independent pinned font, not generated offsets.
 const font=new Map(require('node:zlib').gunzipSync(fs.readFileSync('.cache/toolchains/unifont-16.0.04.hex.gz')).toString().trim().split('\n').map(l=>{const [a,b]=l.split(':');return [parseInt(a,16),Buffer.from(b.trim(),'hex')];}));
 const pixels=fs.readFileSync('build/gba/charizard-plan.rgba');let x=5;
 for(const c of '培养与携带道具'){const bits=font.get(c.codePointAt(0));for(let y=0;y<16;y++)for(let col=0;col<16;col++){const lit=!!(bits[y*2+(col>>3)]&(128>>(col&7)));assert.equal(pixels[((y+2)*240+x+col)*4]>245,lit,`Wrong ROM font pixel for ${c}`);}x+=16;}
 press(2);const listBefore=shot('list-before-close');press(2);assert.notEqual(shot('closed'),listBefore);press(1);assert.equal(shot('reopened'),listBefore);
 fs.writeFileSync('build/gba/emulator-report.json',JSON.stringify({emulator:'@wasm-gaming/mgba-wasm@0.1.1',rom_sha256:crypto.createHash('sha256').update(rom).digest('hex'),boot:true,navigation:true,capture_save:true,reload:true,corrupt_newest_slot_fallback:true,training_and_form_pages:true,chinese_font_pixels:true,close_and_reopen:true,frames:m._mgbawasm_frame_counter()},null,2));
 m._mgbawasm_unload();console.log('PASS: actual GBA ROM boots in mGBA, pages respond, capture/unlock persist, newest corrupt SRAM slot falls back');
})().catch(e=>{console.error(e);process.exitCode=1;});
