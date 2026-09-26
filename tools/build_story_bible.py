"""Validate editorial records and render a local atlas / story bible.

No game logic: portable C remains the runtime authority. Reference media stays in
ignored build output; hashes and original source URLs are committed separately.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/story-bible'
DOCS = ROOT / 'docs/story'
STATUS = {'adopted':'已采用', 'candidate':'候选', 'placeholder':'身份待定', 'proposed_scene':'场景提案'}
EVENT_STATUS = {'written':'正文已写', 'established':'背景已确定／场景未写', 'prototype':'原型已有／演出未完整'}


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def validate(world, people, atlas, media):
    def ids(records):
        keys=[r['id'] for r in records]
        assert len(keys)==len(set(keys)), 'Duplicate ID'
        assert all(re.fullmatch(r'[a-z][a-z0-9-]*', k) for k in keys), 'Invalid ID'
        return set(keys)
    actors=ids(people); event_ids=ids(world['events']); media_ids=ids(media); ids(atlas['regions'])
    event_map={e['id']:e for e in world['events']}
    ids(world['phases'])
    phases={p['id']:p['order'] for p in world['phases']}
    assert len(set(phases.values()))==len(phases), 'Duplicate phase order'
    if world['calendar']['mainline_year_status']=='undetermined':
        assert world['calendar']['epoch_year'] is None, 'Undetermined mainline year was fixed'
        assert all(e['date'] is None for e in world['events'] if e['phase']=='first-journey'), 'Undetermined mainline event was dated'
    for e in world['events']:
        assert set(e['participants'])<=actors, 'Unregistered event participant'
        assert e['status'] in EVENT_STATUS
        assert e['phase'] in phases and e['visibility'] in ('authoring','author_only')
        assert e['date'] is None or re.fullmatch(r'\d{4}(-\d{2})?(-\d{2})?',e['date'])
    for c in people:
        assert c['status'] in STATUS
        assert c['appearance']['reference_media'] is None or c['appearance']['reference_media'] in media_ids
        assert all(r['other'] in actors for r in c['relationships'])
        death=c['death_event']
        if death:
            assert death in event_ids and c['id'] in event_map[death]['participants']
            limit=event_map[death]['date']
            for e in world['events']:
                if c['id'] in e['participants']:
                    assert phases[e['phase']]<=phases[event_map[death]['phase']], f"Post-death appearance: {c['id']} / {e['id']}"
                    if e['date'] and limit:
                        assert e['date']<=limit, f"Post-death appearance: {c['id']} / {e['id']}"
        for e in world['events']:
            if c['id'] in e['participants'] and e['date'] and c['birth_year']:
                assert int(e['date'][:4])>=c['birth_year'], 'Appearance before birth'
        if c['status'] in ('candidate','placeholder','proposed_scene'):
            assert not any(c['id'] in e['participants'] for e in world['events']), 'Proposal became biography without adoption'
        if c['kind']=='ai_trainer':
            assert c['birth_year'] is None, 'AI appearance silently became biological birth year'
    ids(world['secrets']); ids(world['factions'])
    for secret in world['secrets']:
        assert set(secret['known_by'])<=actors and secret['subject'] in actors, 'Unregistered secret knower'
        assert secret['visibility']=='author_only'
        assert secret['subject_knows']==(secret['subject'] in secret['known_by']), 'Secret knowledge contradicts subject state'
        assert secret['reveal_event'] is None or secret['reveal_event'] in event_ids
    ash_secret=next(s for s in world['secrets'] if s['id']=='ash-ai-identity')
    assert ash_secret['known_by']==['oak'] and not ash_secret['subject_knows'], 'Opening AI identity is known only to Oak'
    assert all(f['leader'] is None or f['leader'] in actors for f in world['factions'])
    executive=world['institutions']['world_federation']['executive']
    assert executive['member_count']==4 and executive['includes_champion'], 'World executive includes champion within four members'
    for obj in people+world['events']:
        assert all((ROOT/p).is_file() for p in obj['source_docs']), 'Missing source document'
    for r in atlas['regions']:
        if r['global_coordinates'] is not None:
            xy=r['global_coordinates']; review=r.get('placement_review',{})
            assert isinstance(xy,list) and len(xy)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in xy), 'Global coordinates must be a finite 2D position'
            assert review.get('status')=='reviewed' and review.get('basis')=='omni_authored', 'Global coordinates need a documented compatibility review'
            document=review.get('document','')
            path=(ROOT/document).resolve()
            assert document and path.is_relative_to(ROOT) and path.is_file(), 'Missing placement review document'
        assert r['media_id'] in media_ids
    assert set(r['id'] for r in atlas['regions'])=={'kanto','johto','hoenn','sinnoh','unova','kalos','alola','galar','paldea','hisui'}
    assert all(x['text'] is None for x in world['unwritten']), 'Unwritten event silently filled'
    for m in media:
        assert re.fullmatch(r'[0-9a-f]{64}',m['sha256']), f"Unpinned media: {m['id']}"
        assert m['local_name']==Path(m['local_name']).name, 'Unsafe filename'
        assert m['image_url'].startswith('https://') and m['page_url'].startswith('https://')
    scenes=read('content/pallet-town/scene.json')['maps']
    expected={(s['key'],i,a['person']) for s in scenes for i,a in enumerate(s['actors']) if a.get('person')}
    bindings=[(b['scene'],b['actor_index'],b['person_id']) for c in people for b in c['runtime_bindings']]
    assert len(bindings)==len(set(bindings)) and set(bindings)==expected, 'Runtime actor coverage drift'


def fetch_media(media):
    ctx=ssl.create_default_context()
    # Windows performs intermediate-chain discovery for native HTTPS; urllib
    # needs locally installed intermediate CAs added explicitly. Verification stays on.
    if hasattr(ssl,'enum_certificates'):
        certs=[ssl.DER_cert_to_PEM_cert(c) for c,encoding,_ in ssl.enum_certificates('CA') if encoding=='x509_asn']
        if certs: ctx.load_verify_locations(cadata='\n'.join(certs))
    def fetch(m):
        target=OUT/'media'/m['local_name']
        data=target.read_bytes() if target.exists() else urllib.request.urlopen(m['image_url'],context=ctx,timeout=30).read()
        assert hashlib.sha256(data).hexdigest()==m['sha256'], f"Reference changed: {m['id']}"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(fetch,media))


def page(title,body,active,prefix=''):
    nav=''.join(f'<a href="{prefix}{url}"'+(' aria-current="page"' if active==key else '')+f'>{label}</a>' for key,url,label in [('atlas','index.html','世界地图'),('timeline','timeline.html','故事世界线'),('people','characters.html','人物档案')])
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)} · Pokémon Omni</title><link rel="stylesheet" href="{prefix}style.css"><body><a class="skip" href="#main">跳到正文</a><header><div class="brand">POKÉMON OMNI<small>世界与人物设定集 · 2026.09 · 含编剧剧透</small></div><nav aria-label="设定集导航">{nav}</nav></header><main id="main">{body}<p class="foot">Omni 编剧档案，含未向玩家公开的真相；不是游戏内图鉴或公开宣传页。空白表示尚未创作。此阅读页不是游戏存档或已实装剧情。</p></main><script src="{prefix}filter.js" defer></script></body></html>'''


def source_link(path,prefix=''):
    return f'<a href="{prefix}sources/{h(path.replace("/","--"))}">{h(Path(path).name)}</a>'


def portrait(m,prefix=''):
    evidence={'official_anime':'动画官网','community_hosted_anime_frame':'动画截图（社区转载）'}[m['evidence']]
    return f'<figure class="portrait"><img src="{prefix}media/{h(m["local_name"])}" alt="{h(m["label"])}动画参考"><figcaption>{h(m["version"])}<br><a href="{h(m["page_url"])}">参考图来源</a> · {evidence}</figcaption></figure>'


def event_date(e):
    return e['date'] or e.get('time_label','日期未定，见正文')


def secret_badge(e):
    return '<span class="badge">编剧秘密 · 非角色已知</span>' if e['visibility']=='author_only' else ''


def institution_summary(federation):
    eligibility=federation['eligibility']; executive=federation['executive']; legislature=federation['legislature']
    return (f'每 {federation["tournament_cycle_years"]} 年举办世界赛；实力资格须有{eligibility["record_authority"]}认可的以下任一记录：'
            +'、'.join(eligibility['any_of'])+f'。{executive["head"]}任行政首领；{executive["members"]}（包含冠军），共 {executive["member_count"]} 人，担任{executive["title"]}。'
            +'设'+ '、'.join(legislature['chambers'])+'。'+('冠军地区享有更多议员席位。' if legislature['champion_region_extra_seats'] else ''))


def render(world,people,atlas,media):
    mm={m['id']:m for m in media}; cc={c['id']:c for c in people}
    outputs={}
    body='<p class="eyebrow">World atlas / 原作地区图册</p><h1>我们将要走过的世界</h1><p class="intro">九个现代地区，及神奥的古代时代——洗翠。每幅保留来源地图的地貌与构图，点击地图查看原尺寸参考。各幅独立比例，按世代排列；版面位置不代表全球方位。</p><p class="notice"><strong>统一大陆地图尚未定稿。</strong> 本页是全目标地区的分幅图册，不是 1943 年政治版图，也不证明全部场景已经可玩。</p><div class="relations"><span><strong>城都（西） ↔ 关都（东）</strong>　原作陆路相连</span><span><strong>洗翠 → 神奥</strong>　同一地区的不同时代</span><span>其余全球落位：由 Omni 设计，保留已知地区地形</span></div><div class="atlas" id="atlas-grid">'
    policy=atlas['geography_policy']
    body=body.replace('<div class="atlas" id="atlas-grid">', '<section aria-labelledby="geography-policy"><h2 id="geography-policy">世界拼接规则：已知地理不冲突，未知区域可创作</h2><ul>'+''.join(f'<li>{h(rule)}</li>' for rule in policy['rules'])+'</ul><p>以下仍是制作底图使用的地区参考，统一地图正在按这些规则设计；本轮未完成全球落位。</p></section><div class="atlas" id="atlas-grid">')
    def map_panel(r,index):
        m=mm[r['media_id']]
        provenance='官方网站' if m['evidence']=='official' else '原作地图 · 社区转载'
        return f'<figure class="map" id="{r["id"]}"><a class="image" href="media/{h(m["local_name"])}" aria-label="放大{h(r["name"])}地图"><img src="media/{h(m["local_name"])}" alt="{h(r["name"])}来源地区地图"></a><figcaption><h3><span class="num">{index:02}</span>{h(r["name"])}</h3><div class="meta">{h(r["version"])}</div><footer><a href="{h(m["page_url"])}">{provenance}</a><a href="media/{h(m["local_name"])}">查看原图</a></footer></figcaption></figure>'
    for i,r in enumerate(atlas['regions'][:9],1): body+=map_panel(r,i)
    body+='</div><h2>历史时代 · 洗翠</h2><p>它后来被称为神奥，不是第十块现代大陆；历史时期设施与现代地貌分别核对。</p><div class="historical">'+map_panel(atlas['regions'][9],10)+'</div><h2>扩展地区</h2><p>七之岛、北上乡、蓝莓学园、铠之孤岛和冠之雪原仍保留在项目范围内；完整分幅与连接尚待补入。</p><h2>进入游戏前的地图依据</h2><p>原作地区插画用于宏观对照；实际道路、洞窟、入口和碰撞由相应版本地图数据确认。关都当前以火红格位为准，不将 Let’s Go 插画直接当作火红关卡数据。游戏场景与图册须分别验收。</p>'
    outputs[OUT/'index.html']=page('世界地图',body,'atlas')
    intro=world['calendar']['epoch']+'。主线年份未定，距红莲事件已经过去几十年。已确定背景、成篇正文与开发原型分别标记；同一未定区间内的排列不代表精确先后。'
    body='<p class="eyebrow">Worldline / 编剧主线</p><h1>故事世界线</h1><p class="intro">'+h(intro)+'</p><p class="notice">含小智身份等核心剧透，仅供创作使用；事件中的参与者不等于知道事件全部真相。</p><p>当前一周目基线：'+source_link('docs/32-first-journey-world-premise.md')+'</p>'
    md='# 故事世界线\n\n由 content/story/worldline.json 生成。请修改源数据后运行构建器，不直接编辑本文件。\n\n'+intro+'\n\n**编剧档案，含核心剧透。参与事件不等于知晓全部真相。**\n'
    federation_text=institution_summary(world['institutions']['world_federation'])
    body+='<h2>世界赛与联邦构想</h2><p>'+h(federation_text)+'</p><p class="meta">倡议地区、正式生效日期、比赛届次、任期及席位公式未定。世界级职位不改变地区级冠军与四天王结构。</p><h2>当代势力</h2><ul>'
    md+='\n## 世界赛与联邦构想\n\n'+federation_text+'倡议地区、生效日期、届次与具体细则未定。\n\n## 当代势力\n\n'
    for f in world['factions']:
        body+=f'<li><strong>{h(f["name"])}</strong>：{h(f["current_goal"])}</li>'
        md+=f'- **{f["name"]}**：{f["current_goal"]}\n'
    body+='</ul><h2>身份秘密与知情边界</h2>'
    md+='\n## 身份秘密与知情边界\n\n'
    for s in world['secrets']:
        knowledge='、'.join(cc[id]['name'] for id in s['known_by'])
        text=s['truth']+' 一周目开始时仅'+knowledge+'知晓；'+cc[s['subject']]['name']+('知晓。' if s['subject_knows'] else '本人不知。')+'揭露节点未定。'
        body+=f'<p class="notice">{h(text)}</p>';md+=text+'\n'
    body+='<h2>已登记的历史、背景与原型</h2><div class="timeline">'
    for e in world['events']:
        members='、'.join(f'<a href="people/{id}.html">{h(cc[id]["name"])}</a>' for id in e['participants'])
        date=event_date(e)
        body+=f'<article class="event" id="{e["id"]}"><time>{h(date)}</time><h2>{h(e["title"])} <span class="badge">{EVENT_STATUS[e["status"]]}</span>{secret_badge(e)}</h2><div class="meta">{h(e["location"])}</div><p>{h(e["summary"])}</p><p>{members}</p><div class="meta">依据：'+', '.join(source_link(s) for s in e['source_docs'])+'</div></article>'
        md+=f'\n## {date} · {e["title"]}\n\n状态：{EVENT_STATUS[e["status"]]}；地点：{e["location"]}。\n\n{e["summary"]}\n\n'
        if e['visibility']=='author_only':md+='**编剧秘密，非角色已知信息。**\n\n'
        for id,text in e['participants'].items():md+=f'- [{cc[id]["name"]}](characters/{id}.md)：{text}\n'
    body+='</div><h2>尚未创作</h2><table class="blank-table"><caption>空白保持为空；年龄坐标不是已经发生的事件。</caption><tbody>'
    md+='\n## 尚未创作\n\n| 节点 | 日期 | 事件正文 |\n|---|---|---|\n'
    for x in world['unwritten']:
        body+=f'<tr><th>{h(x["label"])}</th><td aria-label="尚未创作"></td></tr>'
        md+=f'| {x["label"]} | | |\n'
    body+='</tbody></table><h2>连续性约束</h2><ul>'+''.join(f'<li>{h(r)}</li>' for r in world['continuity_rules'])+'</ul>'
    md+='\n## 连续性约束\n\n'+''.join(f'- {r}\n' for r in world['continuity_rules'])
    outputs[OUT/'timeline.html']=page('故事世界线',body,'timeline');outputs[DOCS/'worldline.md']=md
    body=f'<p class="eyebrow">People / 人物与伙伴</p><h1>人物档案</h1><p class="intro">{len(people)} 位已采用角色、无名角色与候选人物。包括有独立剧情作用的宝可梦个体。原作经历不会自动成为 Omni 生平；每一条已写经历都关联世界线事件。</p><div class="toolbar"><div><label for="query">查找姓名或职责</label><input id="query" type="search" placeholder="例如：坂木、研究、火箭队"></div><div><label for="status">创作状态</label><select id="status"><option value="">全部角色</option>'+''.join(f'<option value="{s}">{label}</option>' for s,label in STATUS.items())+'</select></div><p id="count" role="status" aria-live="polite"></p></div><div class="people">'
    for c in people:body+=f'<a class="person-link" data-status="{c["status"]}" href="people/{c["id"]}.html"><span class="name">{h(c["name"])}</span><span class="badge">{STATUS[c["status"]]}</span><span class="role">{h(c["role"])}</span></a>'
    body+='</div><p class="empty" id="empty" hidden>没有匹配的角色。可以清空关键词或选择全部状态。</p>'
    outputs[OUT/'characters.html']=page('人物档案',body,'people')
    index='# 人物档案索引\n\n由 content/story/characters.json 和 worldline.json 生成；空白为尚未创作。\n\n| 人物 | 状态 | 当前职责 |\n|---|---|---|\n'
    for c in people:
        index+=f'| [{c["name"]}](characters/{c["id"]}.md) | {STATUS[c["status"]]} | {c["role"]} |\n'
        image_id=c['appearance']['reference_media']; name=c['name']; a=c['appearance']
        aside=portrait(mm[image_id],'../') if image_id else '<div class="empty">参考图尚未归档。形象信息见本页说明；不使用随机生成肖像补齐。</div>'
        body=f'<p class="eyebrow">Character dossier / {c["id"]}</p><h1>{h(name)} <span class="badge">{STATUS[c["status"]]}</span></h1><p class="intro">{h(c["role"])}</p><div class="person-layout"><aside>{aside}<p class="meta">出生工作年：{c["birth_year"] or "未定"}<br>{h(c["birth_basis"] or "")}</p></aside><div class="reading"><h2>人物形象</h2><p>{h(a["anime_identity"] or "具体形象尚未创作／核对。")}</p><p class="notice">参考图用于辨认原作设计，不是本作各年龄阶段已经完成的立绘。新版服饰、身高比例和像素／3D 资产另行制作。</p><h2>已写生平</h2>'
        md=f'# {name}\n\n<!-- GENERATED: edit content/story/characters.json and worldline.json -->\n\nID：`{c["id"]}`；状态：{STATUS[c["status"]]}。\n\n{c["role"]}\n\n出生工作年：{c["birth_year"] or ""}。{c["birth_basis"] or ""}\n\n## 人物形象\n\n{a["anime_identity"] or ""}\n\n'
        if image_id:md+=f'动画参考：[来源页面]({mm[image_id]["page_url"]})；媒体 ID：`{image_id}`。本地原图经哈希锁定，不作为游戏成品立绘。\n\n'
        md+=f'年龄阶段设计：{a["era_design"] or ""}\n\n最终立绘／像素／3D 资产：{a["production_art"] or ""}\n\n## 已写生平\n\n'
        design='<table class="blank-table"><caption>本作各年龄形象与成品资产，未完成处留空。</caption><tbody>'
        for key,label in [('era_design','年龄阶段设计'),('production_art','立绘／像素／3D 资产')]:
            design+=f'<tr><th>{label}</th><td aria-label="{label}">{h(a[key] or "")}</td></tr>'
        design+='</tbody></table>'
        body=body.replace('<h2>已写生平</h2>',design+'<h2>已写生平</h2>')
        life=[e for e in world['events'] if c['id'] in e['participants']]
        if not life:body+='<div class="blank" aria-label="尚未创作生平"></div>'
        for e in life:
            date=event_date(e)
            body+=f'<article class="event"><time>{h(date)}</time><h3><a href="../timeline.html#{e["id"]}">{h(e["title"])}</a>{secret_badge(e)}</h3><p>{h(e["participants"][c["id"]])}</p><span class="meta">{EVENT_STATUS[e["status"]]}</span></article>'
            private='；编剧秘密' if e['visibility']=='author_only' else ''
            md+=f'- **{date} · {e["title"]}**（{EVENT_STATUS[e["status"]]}{private}）：{e["participants"][c["id"]]} 事件 ID：`{e["id"]}`。\n'
        body+='<h2>生平阶段与留白</h2><table class="blank-table"><caption>留空表示尚未创作，不代表该段人生不存在。</caption><tbody>'
        md+='\n## 完整生平的留白\n\n| 阶段 | 正文 |\n|---|---|\n'
        for k,label in [('childhood','童年与成长'),('before_first_event','首次登场以前'),('unwritten_intervals','已知事件之间的空白'),('later_life','后续人生'),('ending','结局')]:
            text=c['biography'][k] or ''
            body+=f'<tr><th>{label}</th><td'+(' aria-label="尚未创作"' if not text else '')+f'>{h(text)}</td></tr>'
            md+=f'| {label} | {text} |\n'
        body+='</tbody></table><h2>人物关系</h2><ul>'
        md+='\n## 人物关系\n\n'
        for r in c['relationships']:
            body+=f'<li><a href="{r["other"]}.html">{h(cc[r["other"]]["name"])}</a>：{h(r["relationship"])}</li>'
            md+=f'- [{cc[r["other"]]["name"]}]({r["other"]}.md)：{r["relationship"]}。\n'
        body+='</ul><h2>创作依据</h2><p class="source-list">'+' · '.join(source_link(s,'../') for s in c['source_docs'])+'</p></div></div>'
        md+='\n## 创作依据\n\n'+''.join(f'- [{Path(s).name}](../../../{s})\n' for s in c['source_docs'])
        outputs[OUT/'people'/f'{c["id"]}.html']=page(name,body,'people','../');outputs[DOCS/'characters'/f'{c["id"]}.md']=md
    outputs[DOCS/'characters.md']=index
    return outputs


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--fetch-media',action='store_true');args=parser.parse_args()
    world=read('content/story/worldline.json');people=read('content/story/characters.json')['characters'];atlas=read('content/story/atlas.json');media=read('research/narrative/reference-media.json')['media']
    validate(world,people,atlas,media)
    if args.fetch_media:fetch_media(media)
    for path,content in render(world,people,atlas,media).items():
        if args.check:
            if DOCS in path.parents:assert path.exists() and path.read_text(encoding='utf-8')==content, f'Stale generated document: {path}'
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8',newline='\n')
    if not args.check:
        for name in ['style.css','filter.js']:shutil.copyfile(ROOT/'tools/story_bible'/name,OUT/name)
        for src in {s for obj in people+world['events'] for s in obj['source_docs']}:
            dest=OUT/'sources'/src.replace('/','--');dest.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/src,dest)
    missing=[m['id'] for m in media if not (OUT/'media'/m['local_name']).exists()]
    print(f'PASS: {len(people)} characters, {len(world["events"])} events, 10 regional references; runtime actors covered; documents {"checked" if args.check else "rendered"}')
    if missing:print('Reference images missing locally; run --fetch-media: '+', '.join(missing))


if __name__=='__main__':main()
