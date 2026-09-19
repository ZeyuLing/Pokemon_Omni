(async()=>{
 const status=document.getElementById('emulator-status'),canvas=document.getElementById('gba-screen');
 try{
  const romResponse=await fetch('/omni-dex.gba');if(!romResponse.ok)throw Error('请先运行 tools/build_gba.ps1 生成 ROM');
  const m=await createMgbaModule({locateFile:p=>'/emulator/'+p});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
  const rom=new Uint8Array(await romResponse.arrayBuffer()),ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);if(!m._mgbawasm_load(ptr,rom.length,0,0,0,0,1))throw Error('ROM 启动失败');m._free(ptr);
  const storageKey='omni-gba-sram-v1';let persistenceBlocked=false,paused=false,keys=0,last=0,acc=0,saveAt=0;
  function importSave(bytes){if(!omniValidSram(bytes))throw Error('SRAM 缺少有效图鉴存档槽，当前进度保持不变');const p=m._malloc(bytes.length);m.HEAPU8.set(bytes,p);m._mgbawasm_sram_load(p,bytes.length);m._free(p);m._mgbawasm_reset();}
  try{const saved=localStorage.getItem(storageKey);if(saved)importSave(Uint8Array.from(atob(saved),c=>c.charCodeAt(0)));}catch{persistenceBlocked=true;status.textContent='旧浏览器存档无法读取，原记录未覆盖；本次请导出 SRAM。';}
  const ctx=canvas.getContext('2d'),frame=ctx.createImageData(240,160);
  function save(){const n=m._mgbawasm_sram_save();if(!n)return null;const bytes=m.HEAPU8.slice(m._mgbawasm_sram_ptr(),m._mgbawasm_sram_ptr()+n);if(!omniValidSram(bytes))return null;try{if(!persistenceBlocked)localStorage.setItem(storageKey,btoa(String.fromCharCode(...bytes)));}catch{status.textContent='浏览器存储失败，请导出 SRAM 保存本次进度。';}return bytes;}
  function loop(time){if(!last)last=time;acc+=Math.min(time-last,100);last=time;if(!paused){while(acc>=1000/60){m._mgbawasm_run_frame();acc-=1000/60;}frame.data.set(m.HEAPU8.subarray(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+240*160*4));ctx.putImageData(frame,0,0);}else acc=0;if(time-saveAt>5000){save();saveAt=time;}requestAnimationFrame(loop);}
  const codes={ArrowUp:64,ArrowDown:128,ArrowLeft:32,ArrowRight:16,KeyZ:1,KeyX:2,KeyA:512,KeyS:256,ShiftLeft:4,ShiftRight:4,Enter:8};
  function set(bit,down){keys=down?keys|bit:keys&~bit;m._mgbawasm_set_keys(keys);}
  document.addEventListener('keydown',e=>{if(codes[e.code]&&(document.activeElement===canvas||document.activeElement?.hasAttribute('data-key'))){e.preventDefault();set(codes[e.code],true);}});
  document.addEventListener('keyup',e=>{if(codes[e.code])set(codes[e.code],false);});
  window.addEventListener('blur',()=>{keys=0;m._mgbawasm_set_keys(0);save();});window.addEventListener('pagehide',save);
  for(const b of document.querySelectorAll('[data-key]')){const bit=+b.dataset.key;b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);set(bit,true);};b.onpointerup=b.onpointercancel=()=>set(bit,false);b.onkeydown=e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();set(bit,true);}};b.onkeyup=e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();set(bit,false);}};}
  document.getElementById('gba-pause').onclick=e=>{paused=!paused;e.target.textContent=paused?'继续':'暂停';keys=0;m._mgbawasm_set_keys(0);if(paused)save();};
  document.getElementById('gba-export').onclick=()=>{const bytes=save();if(!bytes){status.textContent='尚无保存进度；请先在事件联调菜单登记一次记录。';return;}const url=URL.createObjectURL(new Blob([bytes])),a=document.createElement('a');a.href=url;a.download='omni-dex.sav';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  document.getElementById('gba-import').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size!==32768)throw Error('SRAM 存档必须为 32 KiB');importSave(new Uint8Array(await file.arrayBuffer()));persistenceBlocked=false;save();status.textContent='已载入 SRAM；游戏将验证存档槽。';}catch(error){status.textContent=error.message;}finally{e.target.value='';}};
  if(!persistenceBlocked)status.textContent='运行中 · 真实 GBA ROM / mGBA';requestAnimationFrame(loop);canvas.focus();
 }catch(e){status.textContent='无法启动：'+e.message;}
})();
