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
from datetime import date as CalendarDate
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/story-bible'
DOCS = ROOT / 'docs/story'
STATUS = {'adopted':'已采用', 'candidate':'候选', 'placeholder':'身份待定', 'proposed_scene':'场景提案'}
EVENT_STATUS = {'written':'正文已写', 'established':'背景已确定／场景未写', 'prototype':'原型已有／演出未完整', 'scheduled':'已定日程／情节未写'}
EVIDENCE_STATUS = {'official':'官方网站', 'official_search_text':'官网检索正文', 'game_transcript_secondary':'游戏台词社区转录', 'secondary_episode_reference':'社区角色／剧集整理', 'licensed_episode_synopsis':'授权发行平台简介', 'official_with_secondary_name_index':'官方介绍及社区名称索引', 'official_with_secondary_animation_index':'官方介绍及社区动画索引'}


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def calendar_date(value):
    assert isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value), 'Invalid story date format'
    try:
        return CalendarDate.fromisoformat(value)
    except ValueError as error:
        raise AssertionError('Invalid calendar date') from error


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
    calendar=world['calendar']
    assert calendar['mainline_year_status'] in ('undetermined','adopted_working_calendar')
    epoch=calendar_date(calendar['epoch_date']) if calendar['epoch_date'] else None
    if calendar['mainline_year_status']=='undetermined':
        assert epoch is None and calendar['epoch_year'] is None, 'Undetermined mainline year was fixed'
        assert all(e['date'] is None for e in world['events'] if e['phase']=='first-journey'), 'Undetermined mainline event was dated'
    else:
        assert epoch and epoch.year==calendar['epoch_year'], 'Epoch year/date mismatch'
        assert event_map['ash-departure']['date']==epoch.isoformat(), 'Departure/epoch date mismatch'
    for e in world['events']:
        assert set(e['participants'])<=actors, 'Unregistered event participant'
        assert e['status'] in EVENT_STATUS
        assert e['phase'] in phases and e['visibility'] in ('authoring','author_only')
        assert e['date_status'] in ('assigned','undetermined')
        if e['date_status']=='undetermined':
            assert e['date'] is None and e.get('end_date') is None, 'Undetermined event was dated'
        else:
            start=calendar_date(e['date']); end=calendar_date(e['end_date']) if e.get('end_date') else start
            assert start<=end, 'Reversed event window'
        assert e['date_role'] in ('event','window','snapshot','scheduled')
    # Editorial display order is not a chronology. Only adopted prerequisites
    # constrain undated events; do not derive dates from their list positions.
    successors={id:[] for id in event_ids}
    for constraint in world['chronology_constraints']:
        assert constraint['earlier'] in event_ids and constraint['later'] in event_ids, 'Unknown chronology reference'
        assert constraint['relation']=='ends_before_or_same_day'
        earlier=event_map[constraint['earlier']]; later=event_map[constraint['later']]
        assert phases[earlier['phase']]<=phases[later['phase']], 'Chronology phase prerequisite violated'
        if earlier['date'] and later['date']:
            assert (earlier.get('end_date') or earlier['date'])<=later['date'], 'Chronology prerequisite violated'
        successors[earlier['id']].append(later['id'])
    visiting=set(); visited=set()
    def visit(id):
        assert id not in visiting, 'Chronology cycle'
        if id in visited:return
        visiting.add(id)
        for later in successors[id]:visit(later)
        visiting.remove(id);visited.add(id)
    for id in event_ids:visit(id)
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
            activation=c['activation_event']
            assert activation in event_ids and c['id'] in event_map[activation]['participants'], 'Missing AI activation event'
            if event_map[activation]['date'] and epoch:
                assert calendar_date(event_map[activation]['date'])<epoch, 'AI activation must precede opening'
    future_designs=world.get('future_designs',[])
    future_ids=ids(future_designs)
    assert not (future_ids & event_ids), 'Future direction became an occurred event'
    actor_map={c['id']:c for c in people}
    for design in future_designs:
        assert design['status']=='direction_adopted_scene_unwritten' and design['visibility']=='author_only'
        assert all(design[k] is None for k in ('date','location','chapter','scene_text')), 'Unwritten future direction was scheduled or filled'
        assert set(design['after_events'])<=event_ids, 'Unknown future prerequisite'
        assert set(design['participants'])<=actors and set(design['candidate_actors'])<=actors, 'Unregistered future actor'
        assert design['actor_slot'] in design['participants'] and actor_map[design['actor_slot']]['status']=='placeholder', 'Future actor slot must remain unassigned'
        assert design['selected_actor'] is None, 'Unassigned future role was chosen'
        assert design['recommended_actor'] in design['candidate_actors'] and design['recommendation_status']=='advisory_only', 'Future recommendation is not casting'
    ash=actor_map['ash']; profile=ash['body_profile']
    assert profile['scope']=='before_human_body' and profile['aging']=='does_not_grow_up' and profile['ordinary_human_function'], 'Ash body baseline drift'
    assert profile['transition_design_id'] in future_ids, 'Missing human-body direction'
    assert profile['after_transition']['aging']=='natural_growth' and profile['after_transition']['story_stages']==['少年','青年','中年'], 'Ash future growth drift'
    ids(world['secrets']); ids(world['factions'])
    for secret in world['secrets']:
        assert set(secret['known_by'])<=actors and secret['subject'] in actors, 'Unregistered secret knower'
        assert secret['visibility']=='author_only'
        assert secret['subject_knows']==(secret['subject'] in secret['known_by']), 'Secret knowledge contradicts subject state'
        assert secret['reveal_event'] is None or secret['reveal_event'] in event_ids
    ash_secret=next(s for s in world['secrets'] if s['id']=='ash-ai-identity')
    assert ash_secret['known_by']==['oak'] and not ash_secret['subject_knows'], 'Opening AI identity is known only to Oak'
    assert all(f['leader'] is None or f['leader'] in actors for f in world['factions'])
    program=world['rival_program']; faction_ids=ids(world['factions'])
    assert program['trigger_event'] in event_ids and program['background_event'] in event_ids
    ids(program['casting_groups'])
    cast=[id for group in program['casting_groups'] for id in group['actors']]
    assert len(cast)==len(set(cast)) and set(cast)<=actors, 'Unregistered or duplicate rival candidate'
    assert set(program['adopted_rivals'])<=set(cast) and all(actor_map[id]['status']=='adopted' for id in program['adopted_rivals'])
    assert set(program['recurring_adversaries'])<=actors
    for c in people:
        if c.get('source_identity'):
            source=c['source_identity']
            assert source['evidence_level'] in EVIDENCE_STATUS and source['facts'] and source['continuity']
            assert source['sources'] and all(url.startswith('https://') for url in source['sources']), 'Missing rival evidence source'
        if c.get('rival_design'):
            proposal=c['rival_design']
            assert c['id'] in cast and any(c['id'] in group['actors'] and group['id']==proposal['pool'] for group in program['casting_groups'])
            assert proposal['status']=='advisory_only' and proposal['selected_faction'] is None, 'Rival proposal silently became affiliation'
            assert set(proposal['proposed_factions'])<=faction_ids
            assert all(proposal[k] is None for k in ('first_meeting','qualification_event','arc_outcome')), 'Rival proposal silently became biography'
    for f in program['faction_proposals']:
        assert f['faction'] in faction_ids and set(f['candidates'])<=set(cast), 'Unregistered faction candidate'
        assert set(f['already_assigned'])<=actors and all(actor_map[id]['status']=='adopted' for id in f['already_assigned'])
    assert all(value is None for value in program['open_details'].values()), 'Rival arc gaps were filled'
    executive=world['institutions']['world_federation']['executive']
    assert executive['member_count']==4 and executive['includes_champion'], 'World executive includes champion within four members'
    federation=world['institutions']['world_federation']
    cases=federation['eligibility']['known_cases']
    assert len({c['actor'] for c in cases})==len(cases) and all(c['actor'] in actors for c in cases)
    for case in cases:
        assert actor_map[case['actor']]['competition_status']=={k:v for k,v in case.items() if k!='actor'}, 'Competition dossier drift'
    giovanni_case=next(c for c in cases if c['actor']=='giovanni')
    assert giovanni_case['strength_record_qualified'] and giovanni_case['entry_intent'] and giovanni_case['legal_status']=='revoked' and giovanni_case['registration_completed'] is False and giovanni_case['restoration'] is None, 'Giovanni eligibility obstacle drift'
    assert federation['tournament_cycle_years']==4, 'Tournament cycle drift'
    assert federation['calendar_status'] in ('undetermined','assigned')
    if federation['calendar_status']=='undetermined':
        fields=('proposal_date','enactment_date','qualification_deadline','first_tournament_date','first_tournament_end','first_executive_date','opening_edition')
        assert all(federation[k] is None for k in fields) and not federation['tournament_schedule'] and not federation['calendar_events'], 'Undetermined institution calendar was fixed'
    for field,event_id in federation['calendar_events'].items():
        assert event_id in event_ids and federation[field]==event_map[event_id]['date'], 'Institution date drift'
    previous=None
    for edition in federation['tournament_schedule']:
        begin=calendar_date(edition['start']); end=calendar_date(edition['end']); taking_office=calendar_date(edition['executive_start'])
        assert begin<=end<taking_office, 'Tournament/office date order'
        if previous:
            assert edition['edition']==previous['edition']+1, 'Tournament edition sequence'
            assert begin.year==calendar_date(previous['start']).year+federation['tournament_cycle_years'], 'Tournament cycle drift'
            if executive['term_years'] is not None:
                assert taking_office.year==calendar_date(previous['executive_start']).year+executive['term_years'], 'Executive term drift'
        else:
            assert edition['edition']==1
            assert edition['start']==federation['first_tournament_date'] and edition['end']==federation['first_tournament_end'] and edition['executive_start']==federation['first_executive_date'], 'First tournament schedule drift'
        previous=edition
    ids(world['unwritten'])
    for item in world['unwritten']:
        assert set(item['anchor_events'])<=event_ids, 'Unknown unwritten event anchor'
        assert item['date'] is None, 'Unwritten history was dated'
        assert isinstance(item['questions'],list) and all(isinstance(q,str) for q in item['questions'])
    for obj in people+world['events']+future_designs+[program]:
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
    opening=read('content/opening/prologue.json')
    expected={(opening['id'],s['id'],a) for s in opening['scenes'] for a in s['actors']}
    actual=[(b['sequence'],b['scene'],c['id']) for c in people for b in c.get('presentation_bindings',[])]
    assert len(actual)==len(set(actual)) and set(actual)==expected, 'Opening actor coverage drift'
    assert {x[2] for x in expected}<=actors, 'Unregistered opening actor'
    assert set(world['opening_presentation']['actors'])=={x[2] for x in expected}, 'Opening worldline drift'
    assert world['opening_presentation']['date'] is None, 'Opening montage was dated'
    assert world['opening_presentation']['scene_count']==len(opening['scenes']), 'Opening scene count drift'
    for scene in opening['scenes']:
        assert 'opening-narrator' not in scene['actors'], 'Narration is not an acted scene'
        assert {c['actor'] for c in scene['cast']}<=set(scene['actors']), 'Unregistered opening cast'
        for beat in scene['beats']:
            if beat.get('speaker'):
                assert beat.get('actor') in scene['actors'] or (beat['speaker']=='屏幕' and beat.get('actor') is None), 'Unregistered opening speaker'
    cast=read('assets/characters/manifest.json')['portraits']
    assert len({p['actor'] for p in cast})==len(cast), 'Duplicate cast art'
    covered={c['id'] for c in people if c.get('game_assets',{}).get('portrait_actor')==c['id']}
    assert {p['actor'] for p in cast}==covered, 'Cast dossier coverage drift'


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
    nav=''.join(f'<a href="{prefix}{url}"'+(' aria-current="page"' if active==key else '')+f'>{label}</a>' for key,url,label in [('atlas','index.html','世界地图'),('timeline','timeline.html','故事世界线'),('people','characters.html','人物档案'),('rivals','rivals.html','劲敌选角')])
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)} · Pokémon Omni</title><link rel="stylesheet" href="{prefix}style.css"><body><a class="skip" href="#main">跳到正文</a><header><div class="brand">POKÉMON OMNI<small>世界与人物设定集 · 2026.09 · 含编剧剧透</small></div><nav aria-label="设定集导航">{nav}</nav></header><main id="main">{body}<p class="foot">Omni 编剧档案，含未向玩家公开的真相；不是游戏内图鉴或公开宣传页。空白表示尚未创作。此阅读页不是游戏存档或已实装剧情。</p></main><script src="{prefix}filter.js" defer></script></body></html>'''


def source_link(path,prefix=''):
    return f'<a href="{prefix}sources/{h(path.replace("/","--"))}">{h(Path(path).name)}</a>'


def portrait(m,prefix=''):
    evidence={'official_anime':'动画官网','community_hosted_anime_frame':'动画截图（社区转载）'}[m['evidence']]
    return f'<figure class="portrait"><img src="{prefix}media/{h(m["local_name"])}" alt="{h(m["label"])}动画参考"><figcaption>{h(m["version"])}<br><a href="{h(m["page_url"])}">参考图来源</a> · {evidence}</figcaption></figure>'


def event_date(e):
    return (e['date'] or e.get('time_label','日期未定'))+(' 至 '+e['end_date'] if e.get('end_date') else '')+('（开场状态）' if e.get('date_role')=='snapshot' else '')


def secret_badge(e):
    return '<span class="badge">编剧秘密 · 非角色已知</span>' if e['visibility']=='author_only' else ''


def institution_summary(federation):
    eligibility=federation['eligibility']; executive=federation['executive']; legislature=federation['legislature']
    return (f'每 {federation["tournament_cycle_years"]} 年举办世界赛；实力资格须有{eligibility["record_authority"]}认可的以下任一记录：'
            +'、'.join(eligibility['any_of'])+f'。{executive["head"]}任行政首领；{executive["members"]}（包含冠军），共 {executive["member_count"]} 人，担任{executive["title"]}。'
            +'设'+ '、'.join(legislature['chambers'])+'。'+('冠军地区享有更多议员席位。' if legislature['champion_region_extra_seats'] else ''))


def institution_calendar(federation):
    if federation['calendar_status']=='undetermined':
        return '倡议日期、制度生效、赛事届次、资格截止、比赛与就职日期均未定。四年比赛周期不自动决定行政任期；倡议地区、谈判经过、席位公式与赛果留空。'
    return (f'方案提出：{federation["proposal_date"]}；过渡框架生效：{federation["enactment_date"]}；'
            f'首届资格截止：{federation["qualification_deadline"]}；首届比赛：{federation["first_tournament_date"]} 至 {federation["first_tournament_end"]}；'
            f'首届行政就职：{federation["first_executive_date"]}。常规任期 {federation["executive"]["term_years"]} 年。倡议地区、谈判经过、席位公式与赛果留空。')


def competition_summary(case):
    return ('实力履历已满足。' if case['strength_record_qualified'] else '实力履历未确定。')+('本人已决定争取参赛。' if case['entry_intent'] else '')+case['reason']


def rival_catalog(world,people):
    cc={c['id']:c for c in people}; program=world['rival_program']; factions={f['id']:f['name'] for f in world['factions']}
    body='<p class="eyebrow">Rivals / 劲敌选角</p><h1>关都的多位劲敌</h1><p class="intro">'+h(program['summary'])+'</p><p class="notice">多劲敌方向已采用。人物的原作关系、Omni 选角建议和已写经历分别记录；候选不等于已选阵营，含编剧秘密。</p>'
    md='# 关都劲敌选角\n\n<!-- GENERATED: edit content/story/characters.json and worldline.json -->\n\n'+program['summary']+'\n\n候选不等于已选阵营，来源事实不等于本作经历；含编剧秘密。\n'
    body+='<h2>当代强者的参赛状态</h2>';md+='\n## 当代强者的参赛状态\n\n'
    for case in world['institutions']['world_federation']['eligibility']['known_cases']:
        text=competition_summary(case)
        body+=f'<section id="entry-{case["actor"]}"><h3>{h(cc[case["actor"]]["name"])}</h3><p>{h(text)}</p></section>'
        md+=f'- **{cc[case["actor"]]["name"]}**：{text}\n'
    body+='<h2>培养与资助关系提案</h2>';md+='\n## 培养与资助关系提案\n\n'
    for f in program['faction_proposals']:
        candidates='、'.join(cc[id]['name'] for id in f['candidates'])
        body+=f'<section><h3>{h(factions[f["faction"]])}</h3><p>待讨论人选：{h(candidates)}。{h(f["note"])}</p></section>'
        md+=f'- **{factions[f["faction"]]}**：待讨论人选 {candidates}。{f["note"]}\n'
    for group in program['casting_groups']:
        body+=f'<h2 id="{group["id"]}">{h(group["title"])}</h2>';md+=f'\n## {group["title"]}\n\n'
        for id in group['actors']:
            c=cc[id]; source=c.get('source_identity'); proposal=c['rival_design']
            body+=f'<section class="rival-card" id="rival-{id}"><h3><a href="people/{id}.html">{h(c["name"])}</a> <span class="badge">{STATUS[c["status"]]}</span></h3>'
            if c.get('game_assets'):
                body+=f'<img src="cast/{id}.png" width="160" height="160" style="image-rendering:pixelated" alt="{h(c["name"])}的 GBA 立绘初版"><p class="meta">已编入人物画册；完整行走与战斗动画尚未完成。</p>'
            md+=f'\n### [{c["name"]}](characters/{id}.md) · {STATUS[c["status"]]}\n\n'
            if source:
                body+=f'<p class="meta">来源版本：{h(source["continuity"])}；证据：{EVIDENCE_STATUS[source["evidence_level"]]}。</p><ul>'+''.join(f'<li>{h(fact)}</li>' for fact in source['facts'])+'</ul>'
                md+=f'来源版本：{source["continuity"]}；证据：{EVIDENCE_STATUS[source["evidence_level"]]}。\n\n'+''.join(f'- {fact}\n' for fact in source['facts'])
            body+=f'<p><strong>改编建议：</strong>{h(proposal["proposal"])}</p><p class="meta">具体阵营、遇见节点、资格取得与结局未定。</p></section>'
            md+=f'\n改编建议：{proposal["proposal"]}\n\n具体阵营、遇见节点、资格取得与结局未定。\n'
    body+='<h2>完整研究与证据</h2><p>'+' · '.join(source_link(p) for p in program['source_docs'])+'</p>'
    md+='\n## 完整研究与证据\n\n'+''.join(f'- [{Path(p).name}](../../{p})\n' for p in program['source_docs'])
    return body,md


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
    intro=world['calendar']['epoch']+'。'+world['calendar']['prehistory_dates']+' 未写历史不预定日期或内部顺序；列表位置不代表未定事件的精确先后。'
    body='<p class="eyebrow">Worldline / 编剧主线</p><h1>故事世界线</h1><p class="intro">'+h(intro)+'</p><p class="notice">含小智身份等核心剧透，仅供创作使用；事件中的参与者不等于知道事件全部真相。</p><p>当前一周目基线：'+source_link('docs/32-first-journey-world-premise.md')+'</p>'
    md='# 故事世界线\n\n由 content/story/worldline.json 生成。请修改源数据后运行构建器，不直接编辑本文件。\n\n'+intro+'\n\n**编剧档案，含核心剧透。参与事件不等于知晓全部真相。**\n'
    body+='<p>小智身体与认知设定：'+source_link('docs/33-ash-ai-design.md')+'。身份与身体规则已采用，具体技术组合为研究提案。</p>'
    md+='\n小智身体与认知：[AI 训练家设计提案](../33-ash-ai-design.md)。技术提案不自动成为生平。\n'
    federation_text=institution_summary(world['institutions']['world_federation'])
    season_text=institution_calendar(world['institutions']['world_federation'])
    body+='<h2>世界赛与联邦构想</h2><p>'+h(federation_text)+'</p><p class="meta">'+h(season_text)+'</p><h2>当代势力</h2><ul>'
    md+='\n## 世界赛与联邦构想\n\n'+federation_text+'\n\n'+season_text+'\n\n## 当代势力\n\n'
    for f in world['factions']:
        body+=f'<li><strong>{h(f["name"])}</strong>：{h(f["current_goal"])}</li>'
        md+=f'- **{f["name"]}**：{f["current_goal"]}\n'
    program=world['rival_program']
    body+='</ul><section id="multi-rival-program"><h2>世界赛消息与下一代竞争</h2><p>'+h(program['summary'])+'</p><p><a href="rivals.html">查看劲敌候选、原作关系与阵营建议</a></p></section>'
    md+='\n## 世界赛消息与下一代竞争\n\n'+program['summary']+'\n\n[劲敌候选、原作关系与阵营建议](rivals.md)。\n'
    for case in world['institutions']['world_federation']['eligibility']['known_cases']:
        text=cc[case['actor']]['name']+'：'+competition_summary(case)
        body+='<p>'+h(text)+'</p>';md+='\n'+text+'\n'
    body+='<h2>身份秘密与知情边界</h2>'
    md+='\n## 身份秘密与知情边界\n\n'
    for s in world['secrets']:
        knowledge='、'.join(cc[id]['name'] for id in s['known_by'])
        text=s['truth']+' 一周目开始时仅'+knowledge+'知晓；'+cc[s['subject']]['name']+('知晓。' if s['subject_knows'] else '本人不知。')+'揭露节点未定。'
        body+=f'<p class="notice">{h(text)}</p>';md+=text+'\n'
    if world.get('future_designs'):
        body+='<h2>已确认的后续方向</h2><p>方向已经采用，场景尚未创作；不计入已发生事件或已写生平。</p>'
        md+='\n## 已确认的后续方向\n\n方向已采用，场景未写；不是已发生事件或已写生平。\n'
        for d in world['future_designs']:
            candidates='、'.join(cc[id]['name'] for id in d['candidate_actors'])
            casting=f'执行者未定。首选建议：{cc[d["recommended_actor"]]["name"]}；候选：{candidates}。建议不等于角色已选定。'
            body+=f'<section class="future-design" id="future-{d["id"]}"><h3>{h(d["title"])}</h3><p>{h(d["summary"])}</p><p>{h(casting)}</p><p>日期、地区、篇章与场景正文未定。</p><ul>'+''.join(f'<li>{h(point)}</li>' for point in d['established_points'])+'</ul><p>'+source_link(d['source_docs'][0])+'</p></section>'
            md+=f'\n### {d["title"]}\n\n{d["summary"]}\n\n{casting}\n\n日期、地区、篇章与场景正文未定。\n\n'+''.join(f'- {point}\n' for point in d['established_points'])+f'\n依据：[{Path(d["source_docs"][0]).name}](../../{d["source_docs"][0]})。\n'
    body+='<h2>已登记的历史、背景与原型</h2><div class="timeline">'
    for e in world['events']:
        members='、'.join(f'<a href="people/{id}.html">{h(cc[id]["name"])}</a>' for id in e['participants'])
        date=event_date(e)
        body+=f'<article class="event" id="{e["id"]}"><time>{h(date)}</time><h2>{h(e["title"])} <span class="badge">{EVENT_STATUS[e["status"]]}</span>{secret_badge(e)}</h2><div class="meta">{h(e["location"])}</div><p>{h(e["summary"])}</p><p>{members}</p><div class="meta">依据：'+', '.join(source_link(s) for s in e['source_docs'])+'</div></article>'
        md+=f'\n## {date} · {e["title"]}\n\n状态：{EVENT_STATUS[e["status"]]}；地点：{e["location"]}。\n\n{e["summary"]}\n\n'
        if e['visibility']=='author_only':md+='**编剧秘密，非角色已知信息。**\n\n'
        for id,text in e['participants'].items():md+=f'- [{cc[id]["name"]}](characters/{id}.md)：{text}\n'
    body+='</div><h2>尚未创作</h2><table class="blank-table"><caption>相关节点仅供查阅，不规定这些历史线的顺序与日期；正文保持空白。</caption><tbody>'
    md+='\n## 尚未创作\n\n相关节点仅供查阅，不为留白定年或排序。\n\n| 节点 | 相关已知记录 | 事件正文 |\n|---|---|---|\n'
    for x in world['unwritten']:
        anchors=[next(e for e in world['events'] if e['id']==id) for id in x['anchor_events']]
        links='；'.join(f'<a href="#{e["id"]}">{h(e["title"])}</a>' for e in anchors)
        body+=f'<tr><th>{h(x["label"])}</th><td>{links}</td><td aria-label="尚未创作"></td></tr>'
        md+=f'| {x["label"]} | '+ '；'.join(e['title'] for e in anchors)+' | |\n'
    body+='</tbody></table><h2>待展开的历史线</h2><p>下面记录边界与创作问题，不是已经写出的事件经过。</p>'
    md+='\n## 待展开的历史线\n\n边界与问题不是已写生平。\n'
    for x in world['unwritten']:
        if not x['established_boundary'] and not x['questions']:continue
        body+=f'<section id="unwritten-{x["id"]}"><h3>{h(x["label"])}</h3><p>{h(x["established_boundary"] or "")}</p><ul>'+''.join(f'<li>{h(q)}</li>' for q in x['questions'])+'</ul></section>'
        md+=f'\n### {x["label"]}\n\n{x["established_boundary"] or ""}\n\n'+''.join(f'- {q}\n' for q in x['questions'])
    body+='<h2>连续性约束</h2><ul>'+''.join(f'<li>{h(r)}</li>' for r in world['continuity_rules'])+'</ul>'
    md+='\n## 连续性约束\n\n'+''.join(f'- {r}\n' for r in world['continuity_rules'])
    opening=world.get('opening_presentation')
    if opening:
        summary=f'《未竟的和平》：{opening["scene_count"]} 场战争末期剧情，由世界赛提案、各方会议和下一代的选择连续展开。日期未定；对白与匿名配角为开场稿，未补写红莲之后的空白历史。玩家脚本与编剧秘密独立维护。'
        body+='<h2>已实装的开场演出</h2><p>'+h(summary)+'</p><p>'+source_link(opening['source_docs'][0])+' · <a href="http://127.0.0.1:4173/play?opening">在 GBA 运行器中观看</a></p>'
        md+='\n## 已实装的开场演出\n\n'+summary+'[逐场剧本](../37-acted-opening-screenplay.md)，[实现与验证](../36-playable-opening-and-cast.md)。玩家文本见 `content/opening/prologue.json`。\n'
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
        if c.get('game_assets',{}).get('portrait_actor'):
            art=f'cast/{c["id"]}.png'
            design+=f'<figure><img src="../{art}" width="160" height="160" style="image-rendering:pixelated" alt="{h(name)}的 GBA 人物立绘初版"><figcaption>已编入 ROM 的人物立绘初版；不是完整行走、投球、背面或 3D 套件。</figcaption></figure>'
            md+=f'游戏立绘记录：[资产清单](../../../assets/characters/manifest.json)，角色键 `{c["id"]}`。\n\n'
        if c.get('presentation_bindings'):
            labels='、'.join(b['scene'] for b in c['presentation_bindings'])
            design+=f'<p>开场演出绑定：{h(labels)}。既定背景的演绎稿；不补写未定的人生经历或日期。</p>'
        if c.get('opening_scene_note'):
            note=c['opening_scene_note']
            design+='<section class="opening-role"><h2>开场中的演绎</h2><p>'+h(note)+'</p><p>'+source_link('docs/37-acted-opening-screenplay.md','../')+'</p></section>'
            md=md.replace('## 已写生平','## 开场中的演绎\n\n'+note+'\n\n[逐场剧本](../../37-acted-opening-screenplay.md)。\n\n## 已写生平')
        body=body.replace('<h2>已写生平</h2>',design+'<h2>已写生平</h2>')
        if c.get('body_profile'):
            profile=c['body_profile']
            note='转变前后的身体实现、日期和身份揭露顺序未定；青年、中年经历尚未创作。'
            body=body.replace('<h2>已写生平</h2>','<h2>身体设定</h2><p>'+h(profile['summary'])+'</p><p>'+note+'</p><h2>已写生平</h2>')
            md=md.replace('## 已写生平','## 身体设定\n\n'+profile['summary']+note+'\n\n## 已写生平')
        notes='';notes_md=''
        if c.get('source_identity'):
            s=c['source_identity']
            notes+='<section class="source-identity"><h2>原作身份参考（不计入本作生平）</h2><p>'+h(s['continuity'])+'</p><ul>'+''.join(f'<li>{h(fact)}</li>' for fact in s['facts'])+'</ul><p class="meta">证据：'+EVIDENCE_STATUS[s['evidence_level']]+'。'+h(s['boundary'])+'</p><p>'+ ' · '.join(f'<a href="{h(url)}">来源 {i}</a>' for i,url in enumerate(s['sources'],1))+'</p></section>'
            notes_md+='## 原作身份参考（不计入本作生平）\n\n'+s['continuity']+'\n\n'+''.join(f'- {fact}\n' for fact in s['facts'])+'\n证据：'+EVIDENCE_STATUS[s['evidence_level']]+'。'+s['boundary']+'\n\n'+' · '.join(f'[来源 {i}]({url})' for i,url in enumerate(s['sources'],1))+'\n\n'
        if c.get('rival_design'):
            text=c['rival_design']['proposal']
            notes+='<section class="rival-proposal"><h2>劲敌／关联人物提案</h2><p>'+h(text)+'</p><p>具体阵营、遇见节点、资格取得与结局未定。</p><p><a href="../rivals.html#rival-'+c['id']+'">查看选角研究</a></p></section>'
            notes_md+='## 劲敌／关联人物提案\n\n'+text+'\n\n具体阵营、遇见节点、资格取得与结局未定。[选角研究](../rivals.md)。\n\n'
        if c.get('competition_status'):
            text=competition_summary(c['competition_status'])
            notes+='<h2>当前参赛状态</h2><p>'+h(text)+'</p>'
            notes_md+='## 当前参赛状态\n\n'+text+'\n\n'
        body=body.replace('<h2>已写生平</h2>',notes+'<h2>已写生平</h2>')
        md=md.replace('## 已写生平',notes_md+'## 已写生平')
        life=[e for e in world['events'] if c['id'] in e['participants']]
        if not life:body+='<div class="blank" aria-label="尚未创作生平"></div>'
        for e in life:
            date=event_date(e)
            body+=f'<article class="event"><time>{h(date)}</time><h3><a href="../timeline.html#{e["id"]}">{h(e["title"])}</a>{secret_badge(e)}</h3><p>{h(e["participants"][c["id"]])}</p><span class="meta">{EVENT_STATUS[e["status"]]}</span></article>'
            private='；编剧秘密' if e['visibility']=='author_only' else ''
            md+=f'- **{date} · {e["title"]}**（{EVENT_STATUS[e["status"]]}{private}）：{e["participants"][c["id"]]} 事件 ID：`{e["id"]}`。\n'
        directions=[d for d in world.get('future_designs',[]) if c['id'] in d['participants'] or c['id'] in d['candidate_actors']]
        if directions:
            body+='<h2>后续方向（尚未写入生平）</h2>';md+='\n## 后续方向（尚未写入生平）\n\n'
            for d in directions:
                role='仅作为执行者候选，尚未确定参与此事。' if c['id'] in d['candidate_actors'] else '方向已确认，日期与具体情节未定。'
                body+=f'<section class="future-design"><h3><a href="../timeline.html#future-{d["id"]}">{h(d["title"])}</a></h3><p>{h(role)}</p><p>{h(d["summary"])}</p></section>'
                md+=f'- [{d["title"]}](../worldline.md)：{role}{d["summary"]}\n'
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
    rivals_html,rivals_md=rival_catalog(world,people)
    outputs[OUT/'rivals.html']=page('劲敌选角',rivals_html,'rivals');outputs[DOCS/'rivals.md']=rivals_md
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
        cast_dir=OUT/'cast';cast_dir.mkdir(exist_ok=True)
        for c in people:
            if c.get('game_assets',{}).get('portrait_actor'):
                source=ROOT/'build/pallet/cast'/f'{c["id"]}.png'
                assert source.exists(), 'Build presentation assets before story bible'
                shutil.copyfile(source,cast_dir/source.name)
        for name in ['style.css','filter.js']:shutil.copyfile(ROOT/'tools/story_bible'/name,OUT/name)
        for src in {s for obj in people+world['events']+world.get('future_designs',[]) for s in obj['source_docs']}:
            dest=OUT/'sources'/src.replace('/','--');dest.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/src,dest)
    missing=[m['id'] for m in media if not (OUT/'media'/m['local_name']).exists()]
    print(f'PASS: {len(people)} characters, {len(world["events"])} events, 10 regional references; runtime actors covered; documents {"checked" if args.check else "rendered"}')
    if missing:print('Reference images missing locally; run --fetch-media: '+', '.join(missing))


if __name__=='__main__':main()
