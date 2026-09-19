/* Presentation tools use stable entry IDs; gameplay records stay in the shared C core. */
window.OmniFeatures=(()=>{
 const key='omni-dex-workspace-v1',statKeys=['hp','atk','def','spa','spd','spe'],statLabels=['HP','攻击','防御','特攻','特防','速度'];
 const html=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let api,store={favorites:[],compare:[]},planByEntry=new Map(),active,allPlans;
 const $=id=>document.getElementById(id);
 function save(){try{localStorage.setItem(key,JSON.stringify(store));return true;}catch{api.notice('本机空间不足：本次收藏修改尚未保存。',true);return false;}}
 function normalize(value){if(!value||!Array.isArray(value.favorites)||!Array.isArray(value.compare))throw Error('收藏文件格式不正确');const ids=new Set(api.catalog.entries.map(e=>e.entry_id));return {favorites:[...new Set(value.favorites)].filter(id=>ids.has(id)),compare:[...new Set(value.compare)].filter(id=>ids.has(id)).slice(0,4)};}
 function init(options){
  api=options;allPlans=options.plans;
  if(allPlans.records.length!==api.core.training_count()||(api.core.training_hash()>>>0)!==parseInt(allPlans.content_sha256.slice(0,8),16))throw Error('培养方案与核心版本不一致，请重新构建并刷新');
  for(const [index,p] of allPlans.records.entries()){if(!planByEntry.has(p.entry_id))planByEntry.set(p.entry_id,[]);planByEntry.get(p.entry_id).push({...p,index});}
  try{const raw=localStorage.getItem(key);if(raw)store=normalize(JSON.parse(raw));}catch{api.notice('收藏记录无法读取，原记录未被覆盖。',true);}
  $('favorite-only').onchange=api.query;$('sort').onchange=api.query;$('compare-open').onclick=compare;
  $('workspace-export').onclick=()=>download('omni-favorites.json',JSON.stringify(store,null,2));
  $('workspace-import').onchange=async()=>{try{const f=$('workspace-import').files[0];if(!f)return;if(f.size>1000000)throw Error('收藏文件过大');let parsed;try{parsed=JSON.parse(await f.text());}catch{throw Error('收藏文件无法读取，请选择由“导出收藏”生成的 JSON 文件。');}store=normalize(parsed);const saved=save();api.query();if(active)mount(active);if(saved)api.notice('收藏与对比清单已导入。');}catch(e){api.notice(e.message,true);}finally{$('workspace-import').value='';}};
  $('compare-close').onclick=()=>$('comparison').close();
  const c=allPlans.coverage;$('training-coverage').textContent=`培养方案 ${c.plans} 套 · ${c.forms} 个形态有来源 · 未验证为 Omni 最优方案`;
 }
 function transform(indices){let result=indices.filter(i=>!$('favorite-only').checked||store.favorites.includes(api.catalog.entries[i].entry_id));const sort=$('sort').value;
  if(sort!=='catalog')result.sort((a,b)=>{const x=api.catalog.entries[a],y=api.catalog.entries[b];const score=e=>sort==='total'?Object.values(e.stats).reduce((p,v)=>p+v,0):e.stats[sort];return score(y)-score(x)||a-b;});return result;
 }
 function mount(e){active=e;const toolbar=document.createElement('div');toolbar.className='entry-actions';toolbar.innerHTML=`<button id="favorite-toggle" aria-pressed="${store.favorites.includes(e.entry_id)}">${store.favorites.includes(e.entry_id)?'已收藏':'收藏形态'}</button><button id="compare-add">${store.compare.includes(e.entry_id)?'移出对比':'加入对比'}</button><button id="share-entry">复制条目链接</button>`;document.querySelector('#detail .detail-heading').after(toolbar);
  $('favorite-toggle').onclick=()=>{store.favorites=store.favorites.includes(e.entry_id)?store.favorites.filter(id=>id!==e.entry_id):[...store.favorites,e.entry_id];save();$('favorite-toggle').textContent=store.favorites.includes(e.entry_id)?'已收藏':'收藏形态';$('favorite-toggle').setAttribute('aria-pressed',store.favorites.includes(e.entry_id));api.query();};
  $('compare-add').onclick=()=>{if(store.compare.includes(e.entry_id))store.compare=store.compare.filter(id=>id!==e.entry_id);else{if(store.compare.length>=4){api.notice('对比最多四个形态，请先在对比窗口移除一个。',true);return;}store.compare.push(e.entry_id);}save();$('compare-add').textContent=store.compare.includes(e.entry_id)?'移出对比':'加入对比';api.notice(`对比清单：${store.compare.length} / 4`);};
  $('share-entry').onclick=async()=>{try{await navigator.clipboard.writeText(location.href);api.notice('条目链接已复制。');}catch{api.notice('无法访问剪贴板，可直接复制浏览器地址。',true);}};
  const section=document.createElement('section');section.className='section training';section.setAttribute('aria-label','培养方案');section.innerHTML='<h3>培养方案与携带道具</h3>';document.querySelector('#detail .stats').after(section);
  const plans=planByEntry.get(e.entry_id)||[];
  if(!plans.length){section.innerHTML+='<p class="facts">此形态暂无通过检查的参考方案。没有自动套用普通形态或替它编造“最优配装”。</p>';return;}
  const formats=[...new Set(plans.map(p=>p.format))];section.innerHTML+=`<div class="plan-controls"><label>来源赛制<select id="plan-format">${formats.map(f=>`<option>${html(f)}</option>`).join('')}</select></label><label>方案<select id="plan-choice"></select></label></div><div id="plan-content"></div>`;
  function choices(){const rows=plans.filter(p=>p.format===$('plan-format').value);$('plan-choice').innerHTML=rows.map(p=>`<option value="${p.index}">${html(p.role+' · '+p.label)}</option>`).join('');renderPlan();}
  $('plan-format').onchange=choices;$('plan-choice').onchange=renderPlan;choices();
 }
 function renderPlan(){const p=allPlans.records[+$('plan-choice').value],index=+$('plan-choice').value;const gate=api.core.training_status(index,p.generation,p.battle_kind,0,0);
  $('plan-content').innerHTML=`<p class="plan-status">${p.battle_kind===2?'双打':'单打'} · 来源赛制个体组合检查通过 · ${gate===3?'剧情获取尚未配置':'状态待复核'}</p><div class="plan-item"><strong>${html(p.item.name_zh||'无携带道具')}</strong><p>${html(p.item.effect)}</p></div><p class="facts">特性：<b>${html(p.ability.name_zh)}</b> · 性格：<b>${html(p.nature_zh)}</b> · 参考等级：${p.level}${p.tera_type?' · 太晶属性：'+html(api.catalog.types.find(t=>t.id===p.tera_type)?.name||p.tera_type):''}</p><div class="plan-moves">${p.moves.map(m=>`<span>${html(m.name_zh)}</span>`).join('')}</div><p class="facts">努力值：${statKeys.map((k,i)=>`${statLabels[i]} ${p.evs[k]}`).join(' / ')}<br>个体值：${statKeys.map((k,i)=>`${statLabels[i]} ${p.ivs[k]}`).join(' / ')}</p>${p.alternative_items.length?'<p class="facts">替代携带道具（相同四招重新检查）：'+p.alternative_items.map(x=>html(x.name)).join('、')+'</p>':''}${p.strategy_notes?.length?'<ul class="facts">'+p.strategy_notes.map(note=>'<li>'+html(note)+'</li>').join('')+'</ul>':''}<p class="facts">${html(p.usage_note)} 每只宝可梦只能携带一个道具；Mega 石和 Z 纯晶同样占用道具栏。</p><div class="entry-actions"><button id="plan-export">导出配招文本</button><a href="${html(p.source)}" target="_blank" rel="noopener">方案快照来源</a></div>`;
  $('plan-export').onclick=()=>{const s=p.export_text;download(`${s.species}-${p.format}.txt`,`${s.species}${s.item?' @ '+s.item:''}\nAbility: ${s.ability}\nLevel: ${s.level}\n${s.teraType?'Tera Type: '+s.teraType+'\n':''}EVs: ${statKeys.filter(k=>p.evs[k]).map(k=>p.evs[k]+' '+({hp:'HP',atk:'Atk',def:'Def',spa:'SpA',spd:'SpD',spe:'Spe'}[k])).join(' / ')}\n${s.nature} Nature\nIVs: ${statKeys.map(k=>p.ivs[k]+' '+({hp:'HP',atk:'Atk',def:'Def',spa:'SpA',spd:'SpD',spe:'Spe'}[k])).join(' / ')}\n${s.moves.map(m=>'- '+m).join('\n')}\n`);};
 }
 function compare(){const entries=store.compare.map(id=>api.catalog.entries.find(e=>e.entry_id===id));const body=$('comparison-body');body.innerHTML=entries.length?`<div class="comparison-scroll" tabindex="0"><table class="moves"><caption>形态基础数据对比（种族值并非实战能力）</caption><thead><tr><th>项目</th>${entries.map(e=>`<th>${html(e.name_zh_hans)}<button data-remove="${html(e.entry_id)}" aria-label="移除${html(e.name_zh_hans)}">移除</button></th>`).join('')}</tr></thead><tbody>${[['属性',e=>e.types.map(t=>api.catalog.types.find(x=>x.id===t).name).join('/')],...statKeys.map((k,i)=>[statLabels[i],e=>e.stats[k]]),['合计',e=>Object.values(e.stats).reduce((s,v)=>s+v,0)],['方案数',e=>(planByEntry.get(e.entry_id)||[]).length]].map(([label,fn])=>`<tr><th>${label}</th>${entries.map(e=>`<td>${html(fn(e))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<p>先在形态详情中选择“加入对比”，最多四个。</p>';
  for(const b of body.querySelectorAll('[data-remove]'))b.onclick=()=>{store.compare=store.compare.filter(id=>id!==b.dataset.remove);save();compare();$('compare-close').focus();if(active)$('compare-add').textContent=store.compare.includes(active.entry_id)?'移出对比':'加入对比';};
  if(!$('comparison').open)$('comparison').showModal();
 }
 function download(name,text){const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 return {init,mount,transform};
})();
