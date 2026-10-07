/* Record a continuous new-game story route using ordinary buttons only.
 * Isolated emulator SRAM; never imports or overwrites the browser save. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const scenes=require('../build/pallet/scene-audit.json');for(const m of scenes)m.warps.push(...(m.extra_warps||[]));
(async()=>{
 const dir=path.resolve('.cache/toolchains/mgba-wasm/dist/mgba');
 if(!fs.existsSync(path.join(dir,'mgba.cjs')))fs.copyFileSync(path.join(dir,'mgba.js'),path.join(dir,'mgba.cjs'));
 const m=await require(path.join(dir,'mgba.cjs'))({wasmBinary:fs.readFileSync(path.join(dir,'mgba.wasm'))});m._mgbawasm_init();m._mgbawasm_set_log_level(0);
 const rom=fs.readFileSync('build/pallet/omni-pallet.gba'),rp=m._malloc(rom.length);m.HEAPU8.set(rom,rp);assert(m._mgbawasm_load(rp,rom.length,0,0,0,0,1));m._free(rp);
 const size=m._mgbawasm_state_size(),sp=m._malloc(size),signature=Buffer.from('544c4150494e4d4f','hex');let probeOffset=-1,buttons=0,stopOnEncounter=false;
 const out=path.resolve('build/pallet/story-playthrough');fs.mkdirSync(out,{recursive:true});
 const video=fs.openSync(path.join(out,'story.rgba'),'w'),audio=fs.openSync(path.join(out,'story.pcm'),'w');
 const hardwareFps=16777216/280896;let ticks=0,videoFrames=0,audioSamples=0;const chapters=[];
 const audioPtr=m._malloc(8192);
 function frames(n){while(n--){m._mgbawasm_run_frame();let samples;while((samples=m._mgbawasm_read_audio(audioPtr,2048))>0){fs.writeSync(audio,Buffer.from(m.HEAPU8.buffer,audioPtr,samples*4));audioSamples+=samples;}if(ticks%4===0){fs.writeSync(video,Buffer.from(m.HEAPU8.buffer,m._mgbawasm_video_ptr(),153600));videoFrames++;}ticks++;}}
 function chapter(title){const entry={title,seconds:ticks/hardwareFps,state:state()};chapters.push(entry);console.log(JSON.stringify({chapter:title,seconds:Math.round(entry.seconds)}));fs.writeFileSync(path.join(out,'progress.json'),JSON.stringify(chapters,null,2));}

 function state(){assert(m._mgbawasm_state_save(sp));const bytes=Buffer.from(m.HEAPU8.buffer,sp,size);if(probeOffset<0)probeOffset=bytes.indexOf(signature);assert(probeOffset>=0,'Game loop probe not initialized');const v=Array.from({length:35},(_,i)=>bytes.readUInt32LE(probeOffset+8+i*4));return {screen:v[0],map:v[1],x:v[2],y:v[3],direction:v[4],chapter:v[5],starter:v[6],menu:v[7],moving:v[8],hp:v[9],enemy:v[10],turns:v[11],potions:v[12],battles:v[13],party:v[14],events:v[15],balls:v[16],level:v[17],seq:v[18],beat:v[19],gary:v[20],garyX:v[21],garyY:v[22],storage:v[23],page:v[24],cursor:v[25],form:v[26],nature:v[27],spaEV:v[28],speedEV:v[29],enemyLevel:v[30],bond:v[31],opponents:v[32],opponentSlot:v[33],activeSpecies:v[34]};}
 function press(key){const current=state().screen;if(current===7)frames(240);else if(current===11)frames(110);else if([0,2,3,4,10,13,18,19].includes(current))frames(42);++buttons;m._mgbawasm_set_keys(key);frames(4);m._mgbawasm_set_keys(0);frames(16);return state();}
 function shot(name){const bytes=Buffer.from(m.HEAPU8.slice(m._mgbawasm_video_ptr(),m._mgbawasm_video_ptr()+240*160*4));fs.writeFileSync(`build/pallet/${name}.rgba`,bytes);}
 function dismiss(){for(let i=0;state().screen===7&&i<200;i++)press(1);assert.notEqual(state().screen,7,'Dialogue did not finish');}
 function visible(a,s){if(a.person===3)return !!s.gary;if(a.person===19)return !(s.events&512);return !a.starter||!s.starter;}
 function walkable(map,x,y,s,goal){return x>=0&&y>=0&&x<map.width&&y<map.height&&!map.actors.some(a=>a.x===x&&a.y===y&&visible(a,s))&&(!map.collision[y*map.width+x]||(goal&&map.warps.some(w=>w.x===x&&w.y===y)));}
 function walk(x,y){
  let s=state();assert.equal(s.screen,1);const map=scenes[s.map-1],queue=[[s.x,s.y,[]]],visited=new Set([s.x+','+s.y]),dirs=[[0,1,128],[0,-1,64],[-1,0,32],[1,0,16]];let path;
  while(queue.length){const [cx,cy,p]=queue.shift();if(cx===x&&cy===y){path=p;break;}for(const [dx,dy,key] of dirs){const nx=cx+dx,ny=cy+dy,k=nx+','+ny,goal=nx===x&&ny===y;if(visited.has(k)||!walkable(map,nx,ny,s,goal)||(!goal&&map.warps.some(w=>w.x===nx&&w.y===ny)))continue;visited.add(k);queue.push([nx,ny,[...p,key]]);}}
  assert(path,`No walking path in map ${s.map} from ${s.x},${s.y} to ${x},${y}`);
  for(const key of path){const before=state();m._mgbawasm_set_keys(key);++buttons;let n=0;do{frames(1);s=state();}while(s.x===before.x&&s.y===before.y&&s.map===before.map&&++n<80);m._mgbawasm_set_keys(0);assert(n<80,`Blocked step ${key} from ${JSON.stringify(before)}`);n=0;do{frames(1);s=state();}while(s.moving&&++n<80);assert(n<80,'Walking animation stuck');frames(2);if(state().screen===10){if(stopOnEncounter)return state();press(2);dismiss();s=state();}}
  return state();
 }
 function face(dir){const keys=[128,64,32,16];const before=state();m._mgbawasm_set_keys(keys[dir]);for(let i=0;i<10&&state().direction!==dir;i++)frames(1);m._mgbawasm_set_keys(0);frames(4);assert.equal(state().x,before.x);assert.equal(state().y,before.y);}
 function talkAt(x,y,dir){walk(x,y);face(dir);press(1);}

 let walkSamples=0;const opponentsSeen=new Set();
 function dialogue(){for(let n=0;n<240;n++){const s=state();if(s.screen===7)press(1);else if(s.screen===21){const map=scenes[s.map-1];for(const dx of [2,13])for(const dy of [4,15]){const x=Math.floor((s.garyX+dx)/16),y=Math.floor((s.garyY+dy)/16);assert(!map.collision[y*map.width+x],'Gary walked into map furniture');}walkSamples++;frames(4);}else return;}throw Error('Story did not finish');}
 function battleFight(lose=false,slot=0){for(let n=0;n<1800;n++){const s=state();if(s.map===5&&s.opponents)opponentsSeen.add(s.opponentSlot);if(s.screen===11){press(1);continue;}if(s.screen!==10)return;
   if(lose){press(512);if(state().screen===11)continue;}
   if(s.page===0)press(1);else if(s.page===1){const target=lose?1:(slot===2&&s.activeSpecies!==25?0:slot);if((s.cursor^target)&1)press(16);if((s.cursor^target)&2)press(128);press(1);}else throw Error('Unexpected battle menu');
 }throw Error('Battle exceeded turn budget '+JSON.stringify(state()));}
 frames(120);chapter('新游戏');press(2);press(1);assert.equal(state().screen,14);
 chapter('战争、停战会谈与各方布局');
 let introBudget=60*900;while(state().screen===14&&introBudget>0){frames(30);introBudget-=30;}assert(introBudget>0,'Opening stalled');assert.equal(state().screen,7);
 chapter('真新镇：叫醒与出发');dialogue();assert.equal(state().screen,1);assert(state().events&512);
 walk(10,2);walk(4,8);walk(16,13);assert.equal(state().map,5);
 chapter('大木研究所与机房');talkAt(3,10,0);dialogue();walk(11,2);assert.equal(state().map,10);talkAt(1,4,1);dialogue();walk(6,13);
 chapter('大木赠礼：四只伙伴与培养工具');talkAt(6,4,1);dialogue();assert.equal(state().screen,10);assert.equal(state().party,4);assert.equal(state().balls,100);
 chapter('小茂首战');battleFight(false,2);dialogue();assert.equal(state().screen,1);assert(state().events&32);assert(!state().gary);
 chapter('查看伙伴与工具包');press(8);press(128);press(1);frames(180);press(2);press(2);
 press(8);press(128);press(128);press(1);for(let i=0;i<4;i++)press(16);frames(210);press(2);press(2);
 chapter('沿一号道路前往常青市');walk(6,12);walk(12,0);press(64);assert.equal(state().map,6);walk(12,0);press(64);assert.equal(state().map,7);
 chapter('老人捕捉教学与独角虫赠礼');talkAt(20,10,1);dialogue();assert.equal(state().screen,18);frames(150);press(1);dialogue();assert.equal(state().screen,10);
 press(16);press(1);assert.equal(state().screen,4);frames(120);press(2);press(256);dialogue();assert.equal(state().screen,1);assert(state().events&64);assert.equal(state().party,5);
 chapter('常青市宝可梦中心');walk(26,26);talkAt(6,4,1);dialogue();assert(state().events&1);walk(7,8);
 chapter('友好商店：领取博士包裹与购物');walk(36,19);talkAt(4,3,2);dialogue();assert.equal(state().screen,13);assert(state().events&4);
 const beforeBuy=state().balls;frames(180);press(1);dialogue();assert.equal(state().balls,beforeBuy+1);press(2);walk(4,7);
 chapter('携包裹返回真新镇');walk(24,39);press(128);walk(12,39);press(128);walk(16,13);
 chapter('向大木交还博士包裹');talkAt(6,4,1);dialogue();assert(state().events&8);
 chapter('保存：本段剧情结束');press(8);for(let i=0;i<4;i++)press(128);press(1);dialogue();press(2);frames(240);
 fs.closeSync(video);fs.closeSync(audio);
 const report={rom_sha256:crypto.createHash('sha256').update(rom).digest('hex'),source:'Continuous actual GBA ROM, new game, ordinary input only; no state restore or progress injection',route:'Gary battle; accept old-man capture lesson; heal; receive parcel; buy a ball; return parcel; save',scope:'One continuous branch; alternate mutually exclusive branches remain separately tested',fps:hardwareFps/4,ticks,videoFrames,audioSamples,audioRate:32768,seconds:ticks/hardwareFps,buttons,chapters,final:state()};
 fs.writeFileSync(path.join(out,'story.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pass:true,seconds:report.seconds,frames:videoFrames,buttons,parcel:!!(state().events&8)}));m._mgbawasm_unload();
})().catch(e=>{console.error(e);process.exitCode=1;});
