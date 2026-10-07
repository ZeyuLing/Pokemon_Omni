const assert=require('node:assert/strict');
const {chromium}=require(process.env.OMNI_PLAYWRIGHT_PATH||'C:/Users/13758/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage({viewport:{width:1100,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:4173';
 const range=await page.request.get(base+'/story-playthrough.mp4',{headers:{Range:'bytes=0-1023'}});assert.equal(range.status(),206);assert.equal((await range.body()).length,1024);
 const invalid=await page.request.get(base+'/story-playthrough.mp4',{headers:{Range:'bytes=9007199254740991-'}});assert.equal(invalid.status(),416);
 await page.goto(base+'/story');await page.waitForFunction(()=>document.querySelector('video').readyState>=1);
 await page.waitForFunction(()=>document.querySelectorAll('#chapters button').length===14);
 const metadata=await page.locator('video').evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight}));assert(metadata.duration>840&&metadata.duration<850);assert.equal(metadata.width,720);assert.equal(metadata.height,480);
 await page.locator('video').evaluate(v=>{v.muted=true;return v.play();});await page.waitForFunction(()=>document.querySelector('video').currentTime>1);
 for(const title of ['真新镇：叫醒与出发','友好商店：领取博士包裹与购物','向大木交还博士包裹']){
  await page.getByRole('button',{name:new RegExp(title)}).click();await page.waitForFunction(()=>!document.querySelector('video').seeking&&document.querySelector('video').readyState>=2);await page.waitForTimeout(1200);
  assert.equal(await page.getByRole('button',{name:new RegExp(title)}).getAttribute('aria-current'),'true');
 }
 await page.locator('video').evaluate(v=>v.pause());await page.screenshot({path:'build/pallet/story-playthrough/player-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'build/pallet/story-playthrough/player-mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);console.log(JSON.stringify({pass:true,...metadata,chapters:14,playback:true,seeking:true,byteRanges:true,mobileOverflow:false}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
