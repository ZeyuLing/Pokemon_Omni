/* Capture the archived source via ordinary boot/A; no patched save or RAM. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});
 m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('assets/imported/rocket-user/rocket-user-modifier.gba'),p=m._malloc(rom.length),a=m._malloc(8192);
 m.HEAPU8.set(rom,p);assert(m._mgbawasm_load(p,rom.length,0,0,0,0,1));m._free(p);
 function frames(n){while(n--){m._mgbawasm_run_frame();while(m._mgbawasm_read_audio(a,2048)>0){}}}
 function shot(name){fs.writeFileSync(`build/pallet/reference-start-${name}.rgba`,m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+153600));}
 frames(360);shot('cover');m._mgbawasm_set_keys(1);frames(8);m._mgbawasm_set_keys(0);frames(220);shot('menu');
 m._mgbawasm_unload();console.log('Captured archived Rocket cover and empty save menu through normal input');
})().catch(e=>{console.error(e);process.exitCode=1;});
