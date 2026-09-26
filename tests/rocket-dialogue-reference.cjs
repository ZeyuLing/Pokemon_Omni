/* Normal source-ROM boot/input route. No edited RAM, ROM, or user saves. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const d=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(d,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(d,'mgba.wasm'))});
 m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('assets/imported/rocket-user/rocket-user-modifier.gba'),p=m._malloc(rom.length),ap=m._malloc(8192);
 m.HEAPU8.set(rom,p);assert(m._mgbawasm_load(p,rom.length,0,0,0,0,1));m._free(p);
 function frames(n){while(n--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(ap,2048)>0){}}}
 for(const [key,n] of [[0,360],[1,8],[0,180],[1,8],[0,240],[1,8],[0,180]]){
  m._mgbawasm_set_keys(key);frames(n);m._mgbawasm_set_keys(0);frames(40);
 }
 fs.writeFileSync('build/pallet/reference-rocket-dialogue.rgba',m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600));
 m._mgbawasm_unload();console.log('Captured Rocket dialogue via fresh boot and normal A presses');
})().catch(e=>{console.error(e);process.exitCode=1;});
