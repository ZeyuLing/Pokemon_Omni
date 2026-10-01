const assert=require('node:assert/strict');
const {chromium}=require(process.env.OMNI_PLAYWRIGHT_PATH||'C:/Users/13758/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage({viewport:{width:1120,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:4173/play?travel');await page.getByText('运行中 · 真新镇',{exact:true}).waitFor({timeout:30000});
 await page.locator('#gba-screen').screenshot({path:'build/pallet/travel-browser-intro.png'});
 for(let i=0;i<2;i++){await page.keyboard.down('KeyZ');await page.waitForTimeout(180);await page.keyboard.up('KeyZ');await page.waitForTimeout(220);}
 await page.screenshot({path:'build/pallet/travel-browser.png',fullPage:true});assert.deepEqual(errors,[]);
 console.log('PASS: browser travel deep link, live emulator canvas, input, no page errors');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
