/* Render the source ROM's own m4a engine in mGBA; no MIDI re-orchestration. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const [romPath,out,seconds='90',timingPath]=process.argv.slice(2);
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});
 m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync(romPath),p=m._malloc(rom.length);m.HEAPU8.set(rom,p);assert(m._mgbawasm_load(p,rom.length,0,0,0,0,1));m._free(p);
 const ap=m._malloc(8192),chunks=[];let rate=m._mgbawasm_sample_rate();
 const timing=timingPath?JSON.parse(fs.readFileSync(timingPath)):null,marks={};
 const stateSize=timing?m._mgbawasm_state_size():0,sp=timing?m._malloc(stateSize):0;let playerOffset=-1,previousClock=0,previousSamples=0;
 let samples=0;
 while(samples<+seconds*rate){
  m._mgbawasm_run_frame();rate=m._mgbawasm_sample_rate();let n;
  while((n=m._mgbawasm_read_audio(ap,2048))>0){chunks.push(Buffer.from(m.HEAPU8.slice(ap,ap+n*4)));samples+=n;}
  if(timing){
   assert(m._mgbawasm_state_save(sp));const state=Buffer.from(m.HEAPU8.buffer,sp,stateSize);
   if(playerOffset<0){const signature=Buffer.alloc(4);signature.writeUInt32LE(timing.header);let p=-1;
    while((p=state.indexOf(signature,p+1))>=0){if(p+56<state.length&&state.readUInt32LE(p+52)===0x68736d53){playerOffset=p;break;}}
   }
   if(playerOffset>=0){const clock=state.readUInt32LE(playerOffset+12);
    for(const [key,tick] of Object.entries(timing.targets))if(marks[key]===undefined&&clock>=tick){marks[key]=Math.round(previousSamples+(samples-previousSamples)*(tick-previousClock)/Math.max(1,clock-previousClock));}
    previousClock=clock;previousSamples=samples;
   }
  }
 }
 const pcm=Buffer.concat(chunks),head=Buffer.alloc(44);head.write('RIFF');head.writeUInt32LE(pcm.length+36,4);head.write('WAVEfmt ',8);head.writeUInt32LE(16,16);head.writeUInt16LE(1,20);head.writeUInt16LE(2,22);head.writeUInt32LE(rate,24);head.writeUInt32LE(rate*4,28);head.writeUInt16LE(4,32);head.writeUInt16LE(16,34);head.write('data',36);head.writeUInt32LE(pcm.length,40);
 fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,Buffer.concat([head,pcm]));
 let energy=0,peak=0;for(let i=0;i<pcm.length;i+=2){let a=pcm.readInt16LE(i);energy+=a*a;peak=Math.max(peak,Math.abs(a));}
 const rms=Math.sqrt(energy/(pcm.length/2))/32768;assert(rms>0.002,'Source soundtrack is silent');
 const report={out,rate,seconds:pcm.length/rate/4,rms,peak:peak/32768,marks};
 fs.writeFileSync(out+'.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
