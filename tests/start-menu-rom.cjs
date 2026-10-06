/* Compare the compiled menu to an actual archived Rocket menu framebuffer.
 * Reference state is the pre-Dex inspection save, without flag patching.
 * Neither ROM nor emulated memory is patched by this test. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});
 m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const ap=m._malloc(8192);let sp;
 function load(file){const b=fs.readFileSync(file),p=m._malloc(b.length);m.HEAPU8.set(b,p);assert(m._mgbawasm_load(p,b.length,0,0,0,0,1));m._free(p);return b;}
 function frames(n){while(n--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(ap,2048)>0){}}}
 function press(k){m._mgbawasm_set_keys(k);frames(4);m._mgbawasm_set_keys(0);frames(80);}
 function capture(name){const b=Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600));fs.writeFileSync('build/pallet/'+name+'.rgba',b);return b;}
 function rect(b,x,y,w,h){const rows=[];for(let j=y;j<y+h;j++)rows.push(b.subarray((j*240+x)*4,(j*240+x+w)*4));return Buffer.concat(rows);}
 const referenceRom=load('assets/imported/rocket-user/rocket-user-modifier.gba');
 sp=m._malloc(m._mgbawasm_state_size());
 const referenceState=fs.readFileSync('.cache/rocket-before-dex.state');m.HEAPU8.set(referenceState,sp);assert(m._mgbawasm_state_load(sp));frames(5);press(2);press(8);press(128);
 const reference=capture('start-menu-source');m._mgbawasm_unload();
 const rom=load('build/pallet/omni-pallet.gba');
 function screen(){m._mgbawasm_state_save(sp);const b=Buffer.from(m.HEAPU8.buffer,sp,m._mgbawasm_state_size()),i=b.indexOf(Buffer.from('544c4150494e4d4f','hex'));assert(i>=0);return b.readUInt32LE(i+8);}
 frames(90);press(12);for(let i=0;i<10&&screen()===7;i++)press(1);assert.equal(screen(),1);press(8);assert.equal(screen(),2);
 const first=capture('start-menu-fixed-0');
 assert.deepEqual(rect(first,184,49,24,16),rect(reference,184,17,24,16),'Bag glyphs, spacing, foreground and shadow must match the running source ROM');
 assert.deepEqual(rect(first,184,81,24,16),rect(reference,184,49,24,16),'Save glyphs must match the source ROM');
 const cursor=rect(reference,176,17,8,16);
 assert.deepEqual(rect(first,176,17,8,16),cursor,'Native cursor, including its shadow');
 assert.deepEqual(rect(first,170,2,68,6),rect(reference,170,2,68,6),'Top frame');
 assert.deepEqual(rect(first,170,120,68,6),rect(reference,170,104,68,6),'Bottom frame and action-count-dependent height');
 for(let row=1;row<6;row++){press(128);const b=capture('start-menu-fixed-'+row);assert.deepEqual(rect(b,176,17+row*16,8,16),cursor);for(let old=0;old<row;old++)assert(rect(b,176,17+old*16,8,16).every(v=>v===255),'Old cursor erased');}
 press(128);assert.deepEqual(rect(capture('start-menu-wrap'),168,2,72,126),rect(first,168,2,72,126));
 press(64);press(1);assert.equal(screen(),1,'Last entry closes menu');press(8);press(2);assert.equal(screen(),1,'B closes menu');press(8);press(8);assert.equal(screen(),1,'START closes menu');
 for(const [row,target] of [[1,3],[2,4],[3,5]]){press(8);for(let i=0;i<row;i++)press(128);press(1);assert.equal(screen(),target);press(2);assert.equal(screen(),2);press(2);}
 const report={rom_sha256:sha(rom),reference_rom_sha256:sha(referenceRom),reference_state_sha256:sha(referenceState),reference:'Archived pre-Dex state; B, START, DOWN; no memory/flag patches in this test',checks:['source Bag/Save glyph pixels','source shadowed cursor','source top/bottom frame','six cursor rows','up/down wrap','B/START/return close','party/bag/trainer entry and return'],menu:{outer:[168,0,72,128],text:[184,17],cursor:[176,17],row_step:16}};
 fs.writeFileSync('build/pallet/start-menu-verification.json',JSON.stringify(report,null,2)+'\n');m._mgbawasm_unload();console.log('PASS: source-ROM START typography/cursor/frame pixels, all six rows and menu navigation');
})().catch(e=>{console.error(e);process.exitCode=1;});
