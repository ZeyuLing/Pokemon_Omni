(async()=>{
 const pallet=document.body.dataset.game==='pallet';
 const status=document.getElementById('emulator-status'),canvas=document.getElementById('gba-screen');
 try{
  const maps=pallet?await (await fetch('/pallet-scene.json')).json():null;
  const validate=bytes=>pallet?omniValidPalletSram(bytes,maps):omniValidSram(bytes);
  const romResponse=await fetch(pallet?'/omni-pallet.gba':'/omni-dex.gba');if(!romResponse.ok)throw Error(pallet?'请先运行 tools/build_pallet.ps1 生成游戏':'请先运行 tools/build_gba.ps1 生成 ROM');
  const m=await createMgbaModule({locateFile:p=>'/emulator/'+p});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
  const rom=new Uint8Array(await romResponse.arrayBuffer()),ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);if(!m._mgbawasm_load(ptr,rom.length,0,0,0,0,1))throw Error('ROM 启动失败');m._free(ptr);
  const storageKey=pallet?'omni-pallet-sram-v1':'omni-gba-sram-v1';let persistenceBlocked=false,paused=false,keys=0,last=0,acc=0,saveAt=0;
  function importSave(bytes){if(!validate(bytes))throw Error('SRAM 缺少匹配的有效存档槽，当前进度保持不变');const p=m._malloc(bytes.length);m.HEAPU8.set(bytes,p);m._mgbawasm_sram_load(p,bytes.length);m._free(p);m._mgbawasm_reset();}
  try{const saved=localStorage.getItem(storageKey);if(saved)importSave(Uint8Array.from(atob(saved),c=>c.charCodeAt(0)));}catch{persistenceBlocked=true;status.textContent='旧浏览器存档无法读取，原记录未覆盖；本次请导出 SRAM。';}
  const ctx=canvas.getContext('2d'),frame=ctx.createImageData(240,160);
  function save(){const n=m._mgbawasm_sram_save();if(!n)return null;const bytes=m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+n);if(!validate(bytes))return null;try{if(!persistenceBlocked)localStorage.setItem(storageKey,btoa(String.fromCharCode(...bytes)));}catch{status.textContent='浏览器存储失败，请导出 SRAM 保存本次进度。';}return bytes;}
  const audioPtr=m._malloc(8192);let audioContext=null,audioOn=false,audioAt=0;const audioSources=new Set();
  function stopAudio(){for(const src of audioSources){try{src.stop();}catch{}}audioSources.clear();audioAt=0;}
  function drainAudio(){let count;while((count=m._mgbawasm_read_audio(audioPtr,2048))>0){if(paused||!audioOn||!audioContext||audioContext.state!=='running')continue;const buffer=audioContext.createBuffer(2,count,m._mgbawasm_sample_rate()),start=audioPtr>>1;for(let ch=0;ch<2;ch++){const out=buffer.getChannelData(ch);for(let i=0;i<count;i++)out[i]=m.HEAP16[start+i*2+ch]/32768;}const src=audioContext.createBufferSource();src.buffer=buffer;src.connect(audioContext.destination);audioSources.add(src);src.onended=()=>audioSources.delete(src);audioAt=Math.max(audioAt,audioContext.currentTime);if(audioAt>audioContext.currentTime+0.25)audioAt=audioContext.currentTime;src.start(audioAt);audioAt+=count/buffer.sampleRate;}}
  const audioButton=document.getElementById('gba-audio');if(audioButton)audioButton.onclick=async()=>{try{if(!audioContext)audioContext=new AudioContext();await audioContext.resume();audioOn=!audioOn;if(!audioOn)stopAudio();audioButton.textContent=audioOn?'关闭音乐与音效':'开启音乐与音效';}catch{status.textContent='此浏览器无法播放音效，游戏可继续运行。';}};
  const frameMs=1000*280896/16777216;
  function loop(time){if(!last)last=time;acc+=Math.min(time-last,100);last=time;if(!paused){while(acc>=frameMs){m._mgbawasm_run_frame();drainAudio();acc-=frameMs;}frame.data.set(m.HEAPU8.subarray(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+240*160*4));ctx.putImageData(frame,0,0);}else acc=0;if(time-saveAt>5000){save();saveAt=time;}requestAnimationFrame(loop);}
  const codes={ArrowUp:64,ArrowDown:128,ArrowLeft:32,ArrowRight:16,KeyZ:1,KeyX:2,KeyA:512,KeyS:256,ShiftLeft:4,ShiftRight:4,Enter:8};
  function set(bit,down){keys=down?keys|bit:keys&~bit;m._mgbawasm_set_keys(keys);}
  document.addEventListener('keydown',e=>{if(codes[e.code]&&document.activeElement===canvas){e.preventDefault();set(codes[e.code],true);}});
  document.addEventListener('keyup',e=>{if(codes[e.code])set(codes[e.code],false);});
  window.addEventListener('blur',()=>{keys=0;m._mgbawasm_set_keys(0);save();});window.addEventListener('pagehide',save);
  for(const b of document.querySelectorAll('[data-key]')){const bit=+b.dataset.key;b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);set(bit,true);};b.onpointerup=b.onpointercancel=()=>set(bit,false);b.onkeydown=e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();set(bit,true);}};b.onkeyup=e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();set(bit,false);}};}
  document.getElementById('gba-pause').onclick=e=>{paused=!paused;e.target.textContent=paused?'继续':'暂停';keys=0;m._mgbawasm_set_keys(0);if(paused){stopAudio();save();}};
  document.getElementById('gba-export').onclick=()=>{const bytes=save();if(!bytes){status.textContent=pallet?'尚无游戏进度；请先开始新的冒险。':'尚无保存进度；请先在事件联调菜单登记一次记录。';return;}const url=URL.createObjectURL(new Blob([bytes])),a=document.createElement('a');a.href=url;a.download=pallet?'omni-pallet.sav':'omni-dex.sav';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  document.getElementById('gba-import').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size!==32768)throw Error('SRAM 存档必须为 32 KiB');importSave(new Uint8Array(await file.arrayBuffer()));persistenceBlocked=false;save();status.textContent='已载入 SRAM；游戏将验证存档槽。';}catch(error){status.textContent=error.message;}finally{e.target.value='';}};
  // Explicit preview links use normal ROM buttons. SRAM stays untouched.
  if(pallet){const params=new URLSearchParams(location.search);if(params.has('opening')||params.has('cast')){
   const run=n=>{while(n--)m._mgbawasm_run_frame();};
   const tap=key=>{m._mgbawasm_set_keys(key);run(8);m._mgbawasm_set_keys(0);run(24);};
   run(90);tap(2);tap(params.has('opening')?512:256);drainAudio();
  }}
  if(!persistenceBlocked)status.textContent=pallet?'运行中 · 真新镇':'运行中 · 真实 GBA ROM / mGBA';requestAnimationFrame(loop);canvas.focus();
 }catch(e){status.textContent='无法启动：'+e.message;}
})();
