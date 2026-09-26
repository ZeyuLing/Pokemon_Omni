const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require(process.env.OMNI_PLAYWRIGHT_PATH||'C:/Users/13758/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage({viewport:{width:1040,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const saved=fs.readFileSync('build/pallet/test-game.sav').toString('base64');
 await page.addInitScript(value=>localStorage.setItem('omni-pallet-sram-v1',value),saved);
 for(const mode of ['opening','cast','dex']){
  await page.goto('http://127.0.0.1:4173/play?'+mode);await page.getByText('运行中 · 真新镇',{exact:true}).waitFor({timeout:30000});await page.waitForTimeout(900);
  await page.screenshot({path:`build/pallet/browser-${mode}.png`,fullPage:true});
  assert.equal(await page.evaluate(()=>localStorage.getItem('omni-pallet-sram-v1')),saved);
  if(mode==='cast'){
   await page.locator('#gba-screen').focus();await page.keyboard.down('Shift');await page.waitForTimeout(120);await page.keyboard.up('Shift');await page.waitForTimeout(250);
   await page.screenshot({path:'build/pallet/browser-cast-credits.png',fullPage:true});
  }
 }
 await page.locator('#gba-audio').click();await page.getByRole('button',{name:'关闭音乐与音效',exact:true}).waitFor();
 await page.locator('#gba-pause').click();await page.getByRole('button',{name:'继续',exact:true}).waitFor();await page.locator('#gba-pause').click();await page.locator('#gba-audio').click();
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 assert.deepEqual(errors,[]);console.log('PASS: opening/cast/dex preview links boot real ROM, saved SRAM preserved, cast credits, music/pause toggles, mobile layout');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
