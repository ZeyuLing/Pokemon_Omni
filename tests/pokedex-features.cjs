const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require(process.env.OMNI_PLAYWRIGHT_PATH||'C:/Users/13758/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await b.newPage({viewport:{width:1440,height:1050}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:4173/#dex%3Acharizard%3Abase');await p.locator('#plan-choice').waitFor();
 assert((await p.locator('#plan-content').textContent()).includes('剧情获取尚未配置'));
 const downloadPromise=p.waitForEvent('download');await p.locator('#plan-export').click();const download=await downloadPromise;const saved=await download.path();const txt=fs.readFileSync(saved,'utf8');assert(txt.includes('Ability:'));assert(txt.includes('Nature'));assert(txt.includes('@'));
 await p.locator('#favorite-toggle').click();await p.locator('#favorite-only').check();assert.equal(await p.locator('#entries .entry').count(),1);
 await p.reload();await p.locator('#favorite-toggle').waitFor();assert.equal(await p.locator('#favorite-toggle').getAttribute('aria-pressed'),'true');
 await p.locator('#compare-add').click();await p.goto('http://127.0.0.1:4173/#dex%3Avenusaur%3Abase');await p.locator('#compare-add').click();await p.locator('#compare-open').click();assert(await p.locator('#comparison').isVisible());assert.equal(await p.locator('[data-remove]').count(),2);await p.keyboard.press('Escape');assert(!(await p.locator('#comparison').isVisible()));
 for(const species of ['blastoise','bulbasaur','charmander']){await p.goto(`http://127.0.0.1:4173/#dex%3A${species}%3Abase`);await p.locator('#compare-add').click();}
 assert((await p.locator('#notice').textContent()).includes('最多四个'));await p.locator('#compare-open').click();assert.equal(await p.locator('[data-remove]').count(),4);await p.keyboard.press('Escape');
 await p.goto('http://127.0.0.1:4173/#dex%3Avenusaur%3Abase');await p.locator('#move-kind').waitFor();
 await p.locator('#move-kind').selectOption('Special');await p.locator('#move-type').selectOption('Grass');await p.locator('#move-gen').selectOption('9');assert(await p.locator('#moves tbody tr').count()>0);
 await p.locator('#workspace-import').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{invalid')});assert((await p.locator('#notice').textContent()).length>0);
 await p.locator('#favorite-only').check();assert.equal(await p.locator('#entries .entry').count(),1);
 await p.locator('#clear').click();await p.locator('#sort').selectOption('total');const first=await p.locator('#entries .entry').first().getAttribute('data-index');const cat=require('../content/pokedex/catalog.json');assert.equal(Object.values(cat.entries[+first].stats).reduce((a,c)=>a+c,0),Math.max(...cat.entries.map(e=>Object.values(e.stats).reduce((a,c)=>a+c,0))));
 await p.screenshot({path:'build/pokedex/training-desktop.png',fullPage:true});
 for(const width of [820,390,320]){await p.setViewportSize({width,height:950});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await p.screenshot({path:`build/pokedex/training-${width}.png`,fullPage:true});}
 await p.goto('http://127.0.0.1:4173/gba');await p.getByText('运行中 · 真实 GBA ROM / mGBA',{exact:true}).waitFor({timeout:30000});await p.waitForTimeout(1000);await p.locator('#gba-screen').focus();await p.keyboard.down('KeyZ');await p.waitForTimeout(160);await p.keyboard.up('KeyZ');await p.waitForTimeout(500);await p.screenshot({path:'build/gba/browser-mobile.png',fullPage:true});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await p.locator('#gba-export').click();assert((await p.locator('#emulator-status').textContent()).includes('尚无保存进度'));assert.equal(await p.evaluate(()=>localStorage.getItem('omni-gba-sram-v1')),null);
 for(const bit of ['8','1']){await p.locator(`[data-key="${bit}"]`).click({delay:180});await p.waitForTimeout(200);}
 const gbaDownload=p.waitForEvent('download');await p.locator('#gba-export').click();const gbaSaved=fs.readFileSync(await (await gbaDownload).path());assert(require('../adapters/pokedex-preview/gba-save.js')(gbaSaved));
 const before=await p.evaluate(()=>localStorage.getItem('omni-gba-sram-v1'));await p.locator('#gba-import').setInputFiles({name:'bad.sav',mimeType:'application/octet-stream',buffer:Buffer.alloc(32768)});assert((await p.locator('#emulator-status').textContent()).includes('当前进度保持不变'));assert.equal(await p.evaluate(()=>localStorage.getItem('omni-gba-sram-v1')),before);
 assert.deepEqual(errors,[]);console.log('PASS: training exports, favorites persistence, four-form comparison, sorting, move filters, invalid import, 320/390/820 widths, actual ROM browser player');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
