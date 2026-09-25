"""Validate editorial records and render a local atlas / story bible.

No game logic: portable C remains the runtime authority. Reference media stays in
ignored build output; hashes and original source URLs are committed separately.
"""
import argparse
import hashlib
import json
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
EVENT_STATUS = {'written':'正文已写', 'prototype':'原型已有／演出未完整'}


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
    for e in world['events']:
        assert set(e['participants'])<=actors, 'Unregistered event participant'
        assert e['status'] in EVENT_STATUS
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
                if c['id'] in e['participants'] and e['date']:
                    assert e['date']<=limit, f"Post-death appearance: {c['id']} / {e['id']}"
        for e in world['events']:
            if c['id'] in e['participants'] and e['date'] and c['birth_year']:
                assert int(e['date'][:4])>=c['birth_year'], 'Appearance before birth'
        if c['status'] in ('candidate','placeholder','proposed_scene'):
            assert not any(c['id'] in e['participants'] for e in world['events']), 'Proposal became biography without adoption'
    for obj in people+world['events']:
        assert all((ROOT/p).is_file() for p in obj['source_docs']), 'Missing source document'
    for r in atlas['regions']:
        assert r['global_coordinates'] is None, 'Global coordinates need independent evidence review'
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
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)} · Pokémon Omni</title><link rel="stylesheet" href="{prefix}style.css"><body><a class="skip" href="#main">跳到正文</a><header><div class="brand">POKÉMON OMNI<small>世界与人物设定集 · 2026.09</small></div><nav aria-label="设定集导航">{nav}</nav></header><main id="main">{body}<p class="foot">Omni 创作档案 · 原作资料与本作经历分别记录 · 空白表示尚未创作。此阅读页不是游戏存档或已实装剧情。</p></main><script src="{prefix}filter.js" defer></script></body></html>'''


def source_link(path,prefix=''):
    return f'<a href="{prefix}sources/{h(path.replace("/","--"))}">{h(Path(path).name)}</a>'


def portrait(m,prefix=''):
    evidence={'official_anime':'动画官网','community_hosted_anime_frame':'动画截图（社区转载）'}[m['evidence']]
    return f'<figure class="portrait"><img src="{prefix}media/{h(m["local_name"])}" alt="{h(m["label"])}动画参考"><figcaption>{h(m["version"])}<br><a href="{h(m["page_url"])}">参考图来源</a> · {evidence}</figcaption></figure>'


def render(world,people,atlas,media):
    mm={m['id']:m for m in media}; cc={c['id']:c for c in people}
    outputs={}
    body='<p class="eyebrow">World atlas / 原作地区图册</p><h1>我们将要走过的世界</h1><p class="intro">九个现代地区，及神奥的古代时代——洗翠。每幅保留来源地图的地貌与构图，点击地图查看原尺寸参考。各幅独立比例，按世代排列；版面位置不代表全球方位。</p><p class="notice"><strong>统一大陆地图尚未定稿。</strong> 本页是全目标地区的分幅图册，不是 1943 年政治版图，也不证明全部场景已经可玩。</p><div class="relations"><span><strong>城都（西） ↔ 关都（东）</strong>　原作陆路相连</span><span><strong>洗翠 → 神奥</strong>　同一地区的不同时代</span><span>其余跨地区距离与全球落位：未定</span></div><div class="atlas" id="atlas-grid">'
    def map_panel(r,index):
        m=mm[r['media_id']]
        provenance='官方网站' if m['evidence']=='official' else '原作地图 · 社区转载'
        return f'<figure class="map" id="{r["id"]}"><a class="image" href="media/{h(m["local_name"])}" aria-label="放大{h(r["name"])}地图"><img src="media/{h(m["local_name"])}" alt="{h(r["name"])}来源地区地图"></a><figcaption><h3><span class="num">{index:02}</span>{h(r["name"])}</h3><div class="meta">{h(r["version"])}</div><footer><a href="{h(m["page_url"])}">{provenance}</a><a href="media/{h(m["local_name"])}">查看原图</a></footer></figcaption></figure>'
    for i,r in enumerate(atlas['regions'][:9],1): body+=map_panel(r,i)
    body+='</div><h2>历史时代 · 洗翠</h2><p>它后来被称为神奥，不是第十块现代大陆；历史时期设施与现代地貌分别核对。</p><div class="historical">'+map_panel(atlas['regions'][9],10)+'</div><h2>扩展地区</h2><p>七之岛、北上乡、蓝莓学园、铠之孤岛和冠之雪原仍保留在项目范围内；完整分幅与连接尚待补入。</p><h2>进入游戏前的地图依据</h2><p>原作地区插画用于宏观对照；实际道路、洞窟、入口和碰撞由相应版本地图数据确认。关都当前以火红格位为准，不将 Let’s Go 插画直接当作火红关卡数据。游戏场景与图册须分别验收。</p>'
    outputs[OUT/'index.html']=page('世界地图',body,'atlas')
    body='<p class="eyebrow">Worldline / 编剧主线</p><h1>故事世界线</h1><p class="intro">T=0 对应本作 1967 年，小智 10 岁出发。公历为 Omni 工作纪年。已写正文、当前原型与未创作区间分别保留；未来结局不自动填入。</p><div class="timeline">'
    md='# 故事世界线\n\n由 content/story/worldline.json 生成。请修改源数据后运行构建器，不直接编辑本文件。\n\n公历属于 Omni 工作纪年。\n'
    for e in world['events']:
        members='、'.join(f'<a href="people/{id}.html">{h(cc[id]["name"])}</a>' for id in e['participants'])
        date=e['date'] or '跨年区间，见正文'
        body+=f'<article class="event" id="{e["id"]}"><time>{h(date)}</time><h2>{h(e["title"])} <span class="badge">{EVENT_STATUS[e["status"]]}</span></h2><div class="meta">{h(e["location"])}</div><p>{h(e["summary"])}</p><p>{members}</p><div class="meta">依据：'+', '.join(source_link(s) for s in e['source_docs'])+'</div></article>'
        md+=f'\n## {date} · {e["title"]}\n\n状态：{EVENT_STATUS[e["status"]]}；地点：{e["location"]}。\n\n{e["summary"]}\n\n'
        for id,text in e['participants'].items():md+=f'- [{cc[id]["name"]}](characters/{id}.md)：{text}\n'
    body+='</div><h2>尚未创作</h2><table class="blank-table"><caption>空白保持为空；年龄坐标不是已经发生的事件。</caption><tbody>'
    md+='\n## 尚未创作\n\n| 节点 | 日期 | 事件正文 |\n|---|---|---|\n'
    for x in world['unwritten']:
        body+=f'<tr><th>{h(x["label"])}</th><td aria-label="尚未创作"></td></tr>'
        md+=f'| {x["label"]} | | |\n'
    body+='</tbody></table><h2>连续性约束</h2><ul>'+''.join(f'<li>{h(r)}</li>' for r in world['continuity_rules'])+'</ul>'
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
            date=e['date'] or '跨年区间'
            body+=f'<article class="event"><time>{h(date)}</time><h3><a href="../timeline.html#{e["id"]}">{h(e["title"])}</a></h3><p>{h(e["participants"][c["id"]])}</p><span class="meta">{EVENT_STATUS[e["status"]]}</span></article>'
            md+=f'- **{date} · {e["title"]}**（{EVENT_STATUS[e["status"]]}）：{e["participants"][c["id"]]} 事件 ID：`{e["id"]}`。\n'
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
