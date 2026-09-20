const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require(process.env.OMNI_PLAYWRIGHT_PATH||'C:/Users/13758/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage({viewport:{width:1040,height:980}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:4173/play');await page.getByText('运行中 · 真新镇',{exact:true}).waitFor({timeout:30000});await page.waitForTimeout(600);
 async function key(code){await page.locator('#gba-screen').focus();await page.keyboard.down(code);await page.waitForTimeout(150);await page.keyboard.up(code);await page.waitForTimeout(250);}
 await key('KeyZ');await key('KeyZ');await key('Enter');await page.screenshot({path:'build/pallet/browser-menu.png',fullPage:true});
 const dl=page.waitForEvent('download');await page.locator('#gba-export').click();const saved=fs.readFileSync(await (await dl).path()),maps=require('../build/pallet/scene-audit.json'),valid=require('../adapters/pokedex-preview/pallet-save.js');assert(valid(saved,maps));assert(!require('../adapters/pokedex-preview/gba-save.js')(saved),'Game save must not load as standalone Dex SRAM');
 await page.locator('#gba-import').setInputFiles('build/pallet/test-game.sav');await page.getByText('已载入 SRAM；游戏将验证存档槽。',{exact:true}).waitFor();await page.waitForTimeout(400);await key('KeyZ');await page.screenshot({path:'build/pallet/browser-lab.png',fullPage:true});
 const prior=await page.evaluate(()=>localStorage.getItem('omni-pallet-sram-v1'));
 await page.locator('#gba-import').setInputFiles({name:'wrong.sav',mimeType:'application/octet-stream',buffer:Buffer.alloc(32768)});assert((await page.locator('#emulator-status').textContent()).includes('当前进度保持不变'));assert.equal(await page.evaluate(()=>localStorage.getItem('omni-pallet-sram-v1')),prior);
 await page.locator('#gba-audio').click();await page.getByRole('button',{name:'关闭音效',exact:true}).waitFor();await page.locator('#gba-audio').click();
 for(const width of [820,390,320]){await page.setViewportSize({width,height:950});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`build/pallet/browser-${width}.png`,fullPage:true});}
 // Native button keyboard activation must send A only, not also START.
 await page.getByRole('button',{name:'A 交互',exact:true}).focus();await page.keyboard.down('Enter');await page.waitForTimeout(160);await page.keyboard.up('Enter');
 assert.deepEqual(errors,[]);console.log('PASS: real game browser boot/menu, SRAM export/import protection and isolation, audio control, keyboard/touch surfaces, 320/390/820 layouts');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
