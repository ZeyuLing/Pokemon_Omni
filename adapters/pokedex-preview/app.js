const $=id=>document.getElementById(id);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data,core,offset=0,selected=-1,total=0,moveLimit=15;
const encoder=new TextEncoder(),key='omni-pokedex-progress-v1';
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
function input(bytes){new Uint8Array(core.memory.buffer,core.dex_input_ptr(),65536).fill(0);new Uint8Array(core.memory.buffer,core.dex_input_ptr(),bytes.length).set(bytes);}
function saveBytes(){const n=core.dex_save();if(!n)throw Error('无法保存当前记录。');return new Uint8Array(core.memory.buffer,core.dex_input_ptr(),n).slice();}
function persist(){try{const bytes=saveBytes();localStorage.setItem(key,btoa(String.fromCharCode(...bytes)));return true;}catch(e){notice('记录仍在本次预览中，但浏览器未能保存。请导出记录备份。',true);return false;}}
function metrics(){const all=data.entries.length,seen=core.dex_total(1),registered=core.dex_total(2);$('totals').innerHTML=`<div class="metric"><strong>${all.toLocaleString()}</strong><span>档案条目 · 含待核实</span></div><div class="metric"><strong>${seen}</strong><span>已见过</span></div><div class="metric"><strong>${registered}</strong><span>已登记</span></div>`;}
function query(){
 const text=$('search').value.trim();const numeric=/^#?\d{1,4}$/.test(text)?Number(text.replace('#','')):0;
 input(encoder.encode(numeric?'':text));
 total=core.dex_query(+$('category').value,+$('generation').value,+$('type').value,+$('progress').value,$('research').checked?1:0,numeric,offset);
 if(offset>=total&&offset){offset=0;return query();}
 const n=Math.min(40,Math.max(0,total-offset)),indices=Array.from(new Uint16Array(core.memory.buffer,core.dex_result_ptr(),n));
 $('entries').replaceChildren();
 if(!n){const p=document.createElement('p');p.className='empty';p.textContent='没有符合条件的条目。请更换关键词或清除筛选。';$('entries').append(p);}
 for(const index of indices){const e=data.entries[index],b=document.createElement('button');b.className='entry';b.dataset.index=index;b.setAttribute('aria-pressed',String(index===selected));const f=core.dex_flags(index);b.innerHTML=`<span class="number">${e.national_number?String(e.national_number).padStart(4,'0'):'—'}</span><span class="names"><strong>${escape(e.name_zh_hans)}</strong><span class="sub">${escape(e.name_reference)}</span></span><span class="state-dot">${e.research_only?'待核实':f&2?'已登记':f&1?'已见':'○'}</span>`;b.onclick=()=>select(index);$('entries').append(b);}
 $('result-count').textContent=`${total.toLocaleString()} 条结果`;$('page').textContent=total?`${Math.floor(offset/40)+1} / ${Math.ceil(total/40)}`:'0 / 0';$('previous').disabled=!offset;$('next').disabled=offset+40>=total;
 metrics();
}
function categoryName(e){return data.categories[e.category_id-1]?.name||'其他形态';}
function typeName(id){return data.types.find(t=>t.id===id)?.name||id;}
function select(index){
 selected=index;moveLimit=15;const e=data.entries[index];history.replaceState(null,'','#'+encodeURIComponent(e.entry_id));
 for(const b of $('entries').querySelectorAll('button'))b.setAttribute('aria-pressed',String(+b.dataset.index===index));
 const identity=e.identity_evidence||e.species_identity_evidence;
 const abilities=e.abilities.map(a=>`${escape(data.abilities[a.id]?.name_zh||a.id)}${a.slot==='H'?'〔隐藏〕':''}`).join(' / ')||'待核实';
 const stats=e.stats?Object.entries(e.stats).map(([s,v])=>`<div class="stat"><span>${{hp:'HP',atk:'攻击',def:'防御',spa:'特攻',spd:'特防',spe:'速度'}[s]}</span><b>${v}</b><span class="bar"><i style="width:${Math.min(100,v/255*100)}%"></i></span></div>`).join(''):'<p class="muted">该形态数值尚未核实。</p>';
 const related=data.entries.map((v,i)=>({v,i})).filter(({v})=>e.species_id&&v.species_id===e.species_id);
 const relatedHtml=related.map(({v,i})=>`<button data-related="${i}" aria-pressed="${i===index}">${escape(v.name_zh_hans)}</button>`).join('');
 const evol=e.evolutions.map(name=>{const target=data.entries.find(v=>v.name_reference===name);return escape(target?.name_zh_hans||name);}).join('、');
 const prevo=data.entries.find(v=>v.name_reference===e.prevo);
 $('detail').innerHTML=`<div class="detail-heading"><div><p class="kicker">NO. ${e.national_number?String(e.national_number).padStart(4,'0'):'待定'} / ${escape(categoryName(e))}</p><h2>${escape(e.name_zh_hans)}</h2><p class="english">${escape(e.name_reference)}</p></div><span class="badge ${e.research_only?'review':''}">${escape(e.reference_status)}</span></div>
 <div class="portrait-row"><div class="portrait"><span class="image-note">${e.art_reference?.variants.front_default||e.sprite_id?'正在加载参考图…':'形态图待核实'}</span></div><div><div class="types">${e.types.map(t=>`<span class="type">${escape(typeName(t))}</span>`).join('')||'<span class="type">属性待核实</span>'}</div><div class="facts">特性 <b>${abilities}</b><br>身高 <b>${e.height_m??'—'} m</b> · 体重 <b>${e.weight_kg??'—'} kg</b><br>种族值合计 <b>${e.stats?Object.values(e.stats).reduce((a,b)=>a+b,0):'—'}</b></div></div></div>
 ${artControls(e)}<h3 class="stats-title">种族值（不是实战能力值）</h3><div class="stats">${stats}</div>${hpPanel(e)}${e.source_issues?.length?`<p class="note">作者文档疑点：${e.source_issues.includes('Author stated total differs from sum of six stats')?'原文标注总和 '+e.reported_total+'，六项实际相加为 '+Object.values(e.stats).reduce((a,b)=>a+b,0)+'；此处保留原始六项数值。':'原文象牙猪数值行使用了 M 后缀，所在章节为羁绊形态；保留该来源疑点。'}</p>`:''}<p class="note">${escape(e.mechanic_note)}${e.eligibility_evidence?`<br><a href="${escape(e.eligibility_evidence.official_rule)}" target="_blank" rel="noopener">官方极巨化机制说明</a> · <a href="${escape(e.eligibility_evidence.official_compatibility_guidance)}" target="_blank" rel="noopener">官方游戏兼容性核对方法</a>`:''}</p>
 ${identity?`<section class="section" aria-label="官方形态依据"><h3>官方形态依据</h3><p class="facts"><a href="${escape(identity.url)}" target="_blank" rel="noopener">${escape(identity.title||'宝可梦官方图鉴：物种记录')}</a><br>${identity.claims.some(c=>c.includes('family'))?'官方页面确认该形态家族，细分性别／外观由参考表补充；':e.identity_evidence?'官方页面列出对应形态；':'官方页面确认该物种身份；'}这项依据不代表种族值、招式或获取条件已由官方逐项核实。核对日期：${escape(identity.reviewed_at||identity.checked_at)}。${e.research_only?'数值仍待核验，暂不开放登记。':'战斗数值仍采用固定社区参考版本。'}</p></section>`:''}
 ${e.author_evidence?`<section class="section"><h3>作者羁绊资料</h3><p class="facts"><a href="${escape(e.author_evidence.url)}" target="_blank" rel="noopener">Dragonsden 作者发布帖</a> · ${escape(e.author_evidence.document)}。文档未标注精确版本，2.1 对应关系待核实；此处为资料参考。</p></section>`:''}
 <section class="section"><h3>数据核对</h3><p class="facts">${e.stats_status==='two_reference_sources_agree'?'六项种族值：两份固定参考数据逐项一致。':e.stats_status==='author_document_reference'?'六项种族值：作者文档参考。':'六项种族值：固定社区参考。'}${e.ability_status==='turn_based_adaptation_reference'?' 特性：回合制适配候选，尚未核实为官方赋予本形态的特性。':e.ability_status.startsWith('champions_')?' 特性：固定 Champions 数据参考。':''}${e.ability_comparison?' '+escape(e.ability_comparison.explanation_zh):''}${e.ability_evidence?` <a href="${escape(e.ability_evidence.source)}" target="_blank" rel="noopener">2026 年 9 月特性快照</a>。`:''}${e.move_pool_status==='base_species_reference_not_ZA_learnset'?' 招式表为基础物种跨世代参考，不是 Z-A 专属招式表。':''}</p></section>
 <section class="section"><h3>形态与进化</h3><div class="related" role="region" aria-label="同物种形态列表" tabindex="0">${relatedHtml||'<p class="muted">自定义物种：Dun；不占用官方全国编号。</p>'}</div><p class="facts" style="margin-top:10px">${e.prevo?'进化前：'+escape(prevo?.name_zh_hans||e.prevo)+'。 ':''}${e.evolution_reference?.level?'参考进化等级：'+e.evolution_reference.level+'。 ':''}${evol?'后续进化：'+evol+'。 ':''}${e.form_transition_reference?.required_move?'参考必需招式：'+escape(data.moves[e.form_transition_reference.required_move.toLowerCase().replace(/[^a-z0-9]/g,'')]?.name_zh||e.form_transition_reference.required_move)+'。 ':''}${e.required_items.length?'参考所需物品：'+escape((e.required_items_zh||e.required_items).join('、'))+'。 ':''}本项目获取地点与捕捉剧情尚未配置。</p><p class="facts">${escape(e.transition?.summary_zh)}</p>${e.evolution_edges?.length?`<ul class="facts">${e.evolution_edges.map(v=>`<li>${escape(v.name_zh)}：${escape(v.summary_zh)}${v.item_zh?'；'+escape(v.item_zh):''}${v.move_zh?'；'+escape(v.move_zh):''}${v.condition?'；'+escape(v.condition):''}</li>`).join('')}</ul>`:''}</section>
 <section class="section"><h3>图鉴记录</h3><p class="facts">${escape(e.registration_rule)}。特殊形态独立登记，不会自动登记普通形态。</p><div class="progress-buttons"></div>${e.research_only?'<p class="facts">此条目待核实，暂不开放登记。</p>':''}</section>
 <section class="section"><div class="move-toolbar"><h3>招式来源参考 <span id="move-count"></span></h3><label>筛选招式<input id="move-search" type="search" placeholder="招式中文或英文名" maxlength="80"></label></div><p class="facts">含前置进化与基础形态来源；来源并集不代表四个招式可以同时合法使用。数字为世代，L 为升级、M 为机器、T 为教学、E 为蛋招式、S 为活动。</p><div id="moves"></div></section>`;
 renderArt(e);
 for(const id of ['art-shiny','art-female'])if($(id))$(id).onchange=()=>renderArt(e);
 for(const b of $('detail').querySelectorAll('[data-related]'))b.onclick=()=>select(+b.dataset.related);
 progressButtons();moves();$('move-search').oninput=()=>{moveLimit=15;moves();};
 if($('hp-comparison')){for(const id of ['hp-level','hp-iv','hp-ev','hp-dynamax'])$(id).oninput=updateHp;updateHp();}
}
function artProvenance(e){
 const art=e.art_reference;
 if(art?.status==='ai_original_concept')return '<span class="concept-label">AI 原创概念稿 · Omni 设计提案，非官方／火箭队原图</span>';
 const labels={official_game_screenshot:'官方游戏截图 · 非独立精灵图',community_form_illustration:'社区图鉴参考图',author_credited_artwork:'作者致谢对应作品 · 完整图集，2.1 游戏内外观待核对'};
 return labels[art?.status]?`<span>${labels[art.status]}</span><a href="${escape(art.source)}" target="_blank" rel="noopener">图片出处</a>${art.creator?`<span>署名：${escape(art.creator)}</span><a href="${escape(art.credit_evidence)}" target="_blank" rel="noopener">作者致谢依据</a>`:''}`:'';
}
function artControls(e){
 const v=e.art_reference?.variants||{};
 return `<div class="facts art-controls">${v.front_shiny?'<label><input id="art-shiny" type="checkbox"> 异色参考图</label>':''}${v.front_female?'<label><input id="art-female" type="checkbox"> 雌性参考图</label>':''}${e.category==='dynamax'?'<span>图片为极巨化前的对应形态</span>':''}${artProvenance(e)}</div>`;
}
function renderArt(e){
 const portrait=$('detail').querySelector('.portrait'),v=e.art_reference?.variants||{};
 const shiny=$('art-shiny')?.checked,female=$('art-female')?.checked;
 const variant=shiny?(female?'front_shiny_female':'front_shiny'):(female?'front_female':'front_default');
 const url=v[variant]||(!shiny&&!female?(e.art_reference?.fallback_url|| (e.sprite_id?`https://play.pokemonshowdown.com/sprites/gen5/${encodeURIComponent(e.sprite_id)}.png`:null)):null);
 const token={};portrait.artToken=token;
 portrait.classList.toggle('game-screenshot',['official_game_screenshot','community_form_illustration','author_credited_artwork','ai_original_concept'].includes(e.art_reference?.status));
 portrait.classList.toggle('art-sheet',e.art_reference?.status==='author_credited_artwork');
 portrait.innerHTML='<span class="image-note">'+(url?'正在加载参考图…':e.author_evidence?'尚未收录作者的羁绊形态图':'当前来源未收录此形态图片')+'</span>';
 if(!url)return;
 const img=new Image();img.alt=e.name_zh_hans+(shiny?'异色':'')+(female?'雌性':'')+'参考图';img.width=135;img.height=135;img.referrerPolicy='no-referrer';
 const fallback=(slow=false)=>{if(portrait.artToken!==token)return;const note=portrait.querySelector('.image-note');if(note){note.textContent=slow?'参考图加载较慢，仍在尝试…':'参考图暂不可用：远程图片加载失败';if(!slow){const retry=document.createElement('button');retry.textContent='重试图片';retry.onclick=()=>renderArt(e);note.append(document.createElement('br'),retry);}}};
 const timer=setTimeout(()=>fallback(true),5000);
 img.onload=()=>{clearTimeout(timer);if(portrait.artToken===token)portrait.replaceChildren(img);};
 img.onerror=()=>{clearTimeout(timer);fallback();};img.src=url;
}
function hpPanel(e){
 if(!e.stats||!['dynamax','gigantamax'].includes(e.category))return '';
 return `<section class="hp-panel" aria-label="极巨化前后实战 HP 对比"><h3>实战 HP 上限 · 极巨化前后</h3><p class="facts">极巨化／超极巨化不改变种族值。HP 上限按个体培养和极巨化等级计算；其他五项能力不会因极巨化本身提升。</p><div class="hp-inputs"><label>宝可梦等级<input id="hp-level" type="number" min="1" max="100" step="1" value="50"></label><label>HP 个体值<input id="hp-iv" type="number" min="0" max="31" step="1" value="31"></label><label>HP 努力值<input id="hp-ev" type="number" min="0" max="252" step="1" value="0"></label><label>极巨化等级<input id="hp-dynamax" type="number" min="0" max="10" step="1" value="10"></label></div><output id="hp-comparison" aria-live="polite"></output><p class="facts">这是满 HP 上限的计算示例，不会改动个体数据或恢复当前 HP。一般倍率为 1.5＋0.05×极巨化等级，结果向下取整；脱壳忍者维持 1 HP。</p><details><summary>数值依据</summary><p class="facts"><a href="https://www.pokemon.com/uk/features/dynamax-pokemon-battle-strategies-for-pokemon-sword-and-pokemon-shield" target="_blank" rel="noopener">官方战术说明：提升当前 HP 与 HP 上限</a>。官方攻略以翻倍场景说明；0–10 等级公式、取整与脱壳忍者例外按固定 Showdown 0.11.11 的实现交叉核对，未冒充官方网页逐项给出的公式。</p></details></section>`;
}
function updateHp(){
 const ids=['hp-level','hp-iv','hp-ev','hp-dynamax'],ranges=[[1,100],[0,31],[0,252],[0,10]];
 const values=ids.map(id=>$(id).value===''?NaN:Number($(id).value));let valid=true;
 ids.forEach((id,i)=>{const ok=Number.isInteger(values[i])&&values[i]>=ranges[i][0]&&values[i]<=ranges[i][1];$(id).setAttribute('aria-invalid',String(!ok));if(!ok)valid=false;});
 const out=$('hp-comparison');if(!valid){out.textContent='请输入范围内的整数：等级 1–100，HP 个体值 0–31，HP 努力值 0–252，极巨化等级 0–10。';return;}
 const e=data.entries[selected],fixed=e.species_id==='pokemon:shedinja'?1:0;
 const before=core.dex_hp(e.stats.hp,values[0],values[1],values[2],fixed),after=core.dex_max_hp(before,values[3],fixed);
 if(!before||!after){out.textContent='当前参数无法计算。';return;}
 out.innerHTML=`<span>极巨化前 <b>${before}</b></span><span aria-hidden="true">→</span><span>极巨化后 <b>${after}</b></span><small>HP 种族值仍为 ${e.stats.hp}${fixed?' · 固定 1 HP 例外':''}</small>`;
}
function progressButtons(){const e=data.entries[selected],f=core.dex_flags(selected),box=$('detail').querySelector('.progress-buttons');box.replaceChildren();for(const [flag,label] of [[1,'记录见过'],[2,'登记形态'],[4,'标记解锁']]){const b=document.createElement('button');b.textContent=(f&flag?'✓ ':'')+label;b.disabled=e.research_only||!!(f&flag);b.className=f&flag?'done':'';b.onclick=()=>{const result=core.dex_record(selected,flag);if(result){notice('登记未成功，当前条目不满足登记条件。',true);return;}const stored=persist();query();progressButtons();if(stored)notice('已保存此形态的本机预览记录。');};box.append(b);}}
function moves(){const e=data.entries[selected],q=$('move-search').value.toLowerCase().trim(),merged=new Map();for(const pool of e.move_pool_ids)for(const [id,sources] of Object.entries(data.move_pools[pool]||{})){if(!merged.has(id))merged.set(id,new Set());for(const s of sources)merged.get(id).add(s);}const rows=[...merged].filter(([id])=>{const m=data.moves[id];return m&&(m.name_zh.toLowerCase().includes(q)||m.name_en.toLowerCase().includes(q));}).sort((a,b)=>(data.moves[a[0]].name_en).localeCompare(data.moves[b[0]].name_en));$('move-count').textContent=`· ${rows.length}`;if(!rows.length){$('moves').innerHTML='<p class="empty">'+(e.research_only?'该形态招式资料待核实。':'没有匹配的招式。')+'</p>';return;}$('moves').innerHTML=`<table class="moves"><thead><tr><th scope="col">招式 / 来源</th><th scope="col">属性</th><th scope="col">威力</th><th scope="col">命中</th><th scope="col">PP</th></tr></thead><tbody>${rows.slice(0,moveLimit).map(([id,sources])=>{const m=data.moves[id];return `<tr><td>${escape(m.name_zh)}<span class="sources">${escape(m.name_en)} · ${escape([...sources].sort().join(', '))}</span></td><td>${escape(typeName(m.type))}</td><td>${m.power||'—'}</td><td>${m.accuracy===true?'必中':m.accuracy}</td><td>${m.pp}</td></tr>`;}).join('')}</tbody></table>${rows.length>moveLimit?'<button id="more-moves" style="margin-top:12px">再显示 15 个招式</button>':''}`;const more=$('more-moves');if(more)more.onclick=()=>{moveLimit+=15;moves();$('more-moves')?.focus();};}
async function init(){
 try{const responses=await Promise.all([fetch('/catalog.json'),fetch('/pokedex.wasm')]);if(responses.some(r=>!r.ok))throw Error('资料包读取失败');data=await responses[0].json();core=(await WebAssembly.instantiate(await responses[1].arrayBuffer(),{})).instance.exports;
 if(core.dex_count()!==data.entries.length||data.entries.some((e,i)=>(core.dex_id(i)>>>0)!==e.numeric_id))throw Error('资料与图鉴核心版本不一致，请重新构建');
 $('announced-list').innerHTML=data.announced.records.map(r=>`<li><a href="${escape(r.source_zh||data.announced.source)}" target="_blank" rel="noopener">${escape(r.name_zh||r.name_en)}</a>${r.types?' · '+r.types.map(typeName).join('／'):' · 已公布角色外观，尚未确认玩法形态'}${r.ability?' · '+escape(data.abilities[r.ability.toLowerCase()]?.name_zh||r.ability):''}</li>`).join('');
 data.categories.forEach((c,i)=>$('category').add(new Option(c.name,i+1)));data.types.forEach((t,i)=>$('type').add(new Option(t.name,i+1)));for(let i=1;i<=9;i++)$('generation').add(new Option(`第 ${i} 世代`,i));
 try{const stored=localStorage.getItem(key);if(stored){const bytes=Uint8Array.from(atob(stored),c=>c.charCodeAt(0));if(bytes.length>65536)throw Error();input(bytes);if(core.dex_load(bytes.length))throw Error();}}catch{notice('本机旧记录未能读取，未覆盖原记录。可以导入已有备份恢复。',true);}
 for(const id of ['search','category','type','generation','progress','research'])$(id).addEventListener(id==='search'?'input':'change',()=>{offset=0;query();});
 $('clear').onclick=()=>{$('search').value='';for(const id of ['category','type','generation','progress'])$(id).value='0';$('research').checked=true;offset=0;query();$('search').focus();};
 $('previous').onclick=()=>{offset=Math.max(0,offset-40);query();$('entries').scrollTop=0;};$('next').onclick=()=>{offset+=40;query();$('entries').scrollTop=0;};
 $('export').disabled=false;$('import').disabled=false;
 $('export').onclick=()=>{try{const url=URL.createObjectURL(new Blob([saveBytes()],{type:'application/octet-stream'})),a=document.createElement('a');a.href=url;a.download='omni-pokedex.odex';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('图鉴记录已导出。');}catch(e){notice(e.message,true);}};
 $('import').onchange=async()=>{const file=$('import').files[0];if(!file)return;try{if(file.size>65536)throw Error('记录文件过大');const bytes=new Uint8Array(await file.arrayBuffer());input(bytes);if(core.dex_load(bytes.length))throw Error('文件损坏或格式不受支持，当前记录未改变');const stored=persist();query();if(selected>=0)progressButtons();if(stored)notice('图鉴记录已导入。');}catch(e){notice(e.message,true);}finally{$('import').value='';}};
 $('entries').setAttribute('aria-busy','false');query();selectHash();window.addEventListener('hashchange',selectHash);
 }catch(e){notice('图鉴加载失败：'+e.message+'。请确认已运行构建脚本，然后刷新重试。',true);$('entries').setAttribute('aria-busy','false');$('entries').innerHTML='<p class="empty">资料暂不可用。</p>';const b=document.createElement('button');b.textContent='重新加载';b.onclick=()=>location.reload();$('entries').append(b);}
}
function selectHash(){let desired;try{desired=decodeURIComponent(location.hash.slice(1));}catch{desired='';}let i=data.entries.findIndex(e=>e.entry_id===desired);if(i<0&&desired.endsWith(':dynamax')){i=data.entries.findIndex(e=>e.entry_id===desired.slice(0,-8));notice('该极巨化条目缺少剑盾范围内的资格依据，已移除；现显示基础形态。');}select(i>=0?i:0);}
init();
