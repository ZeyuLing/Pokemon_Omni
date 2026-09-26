"""Build local GBA image/font/text assets; no generated binaries are committed."""
import concurrent.futures
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import unicodedata
import urllib.request
from PIL import Image
from gba_pixel_font import load_pixel_glyphs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/gba'
CACHE = ROOT / '.cache/gba-art'
VARIANTS = ['front_default', 'back_default', 'front_shiny', 'back_shiny',
            'front_female', 'back_female', 'front_shiny_female', 'back_shiny_female']


def pack_image(pixels):
    """Lossless RGB555 runs: little-endian (length, color), 4096 pixels exactly.

    Transparent margins dominate these sprites. Raw fallback caps worst-case
    size; all eight available variants fit without reducing color precision.
    """
    values = struct.unpack('<4096H', pixels)
    runs = bytearray(); start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[end] == values[start]:
            end += 1
        runs += struct.pack('<HH', end-start, values[start]); start = end
    return struct.pack('<H', 1 if len(runs) < len(pixels) else 0) + (runs if len(runs) < len(pixels) else pixels)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT / 'content/pokedex/catalog.json').read_text(encoding='utf-8'))
    plans = json.loads((ROOT / 'content/training/plans.json').read_text(encoding='utf-8'))['records']
    descriptions = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/legality-reference/dex-descriptions.cjs')], cwd=ROOT))
    urls = sorted({v for e in catalog['entries'] for k,v in e['art_reference']['variants'].items() if k in VARIANTS and v})
    front_urls = {e['art_reference']['variants']['front_default'] for e in catalog['entries']}
    def fetch(url):
        target = CACHE / (hashlib.sha256(url.encode()).hexdigest() + '.img')
        if url.startswith('/rocket-art/'):
            data = (ROOT / 'assets/imported/rocket-user/bond-sprites' / url.split('/')[-1]).read_bytes()
        elif url.startswith('/ultra-art/'):
            data = (ROOT / 'assets/imported/ultra-emerald-5.8-user/form-sprites' / url.split('/')[-1]).read_bytes()
        elif target.exists():
            data = target.read_bytes()
        else:
            last = None
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'PokemonOmni-local-asset-import/1.0'})
                    data = urllib.request.urlopen(req, timeout=20).read()
                    Image.open(io.BytesIO(data)).verify()
                    target.write_bytes(data)
                    break
                except Exception as error:
                    last = error
            else:
                return url, None, str(last), None
        image = Image.open(io.BytesIO(data)).convert('RGBA')
        portrait_pixels = None
        if url in front_urls:
            # Source sheets contain wide transparent margins. The main Dex
            # portrait uses the original sprite pixels before fitting the frame.
            bounds = image.getchannel('A').point(lambda a:255 if a>=96 else 0).getbbox()
            portrait = image.crop(bounds) if bounds else image.copy()
            portrait.thumbnail((56,56), Image.Resampling.NEAREST)
            portrait_canvas = Image.new('RGBA',(64,64))
            portrait_canvas.alpha_composite(portrait,((64-portrait.width)//2,(64-portrait.height)//2))
            portrait_pixels = b''.join(struct.pack('<H',0x8000 if a<96 else (r>>3)|((g>>3)<<5)|((b>>3)<<10)) for r,g,b,a in portrait_canvas.get_flattened_data())
        image.thumbnail((64, 64), Image.Resampling.LANCZOS if image.width > 128 else Image.Resampling.NEAREST)
        canvas = Image.new('RGBA', (64, 64))
        canvas.alpha_composite(image, ((64 - image.width) // 2, (64 - image.height) // 2))
        pixels = bytearray()
        for r, g, b, a in canvas.get_flattened_data():
            pixels += struct.pack('<H', 0x8000 if a < 96 else (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
        return url, bytes(pixels), hashlib.sha256(data).hexdigest(), portrait_pixels
    fetched = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for i, result in enumerate(pool.map(fetch, urls)):
            fetched[result[0]] = result
            if i % 100 == 0:
                print(f'Images {i + 1}/{len(urls)}', flush=True)
    art = bytearray(); offsets = {}; seen = {}; audit = []
    for url in urls:
        _, image, sha, _ = fetched[url]
        if image is None:
            offsets[url] = 0xFFFFFFFF
        else:
            key = hashlib.sha256(image).hexdigest()
            if key not in seen:
                seen[key] = len(art); art += pack_image(image)
            offsets[url] = seen[key]
        audit.append({'url': url, 'source_sha256': sha if image else None, 'offset': offsets[url], 'error': None if image else sha})
    portrait_offsets = {}; portrait_audit = []
    for url in sorted(front_urls):
        _,_,sha,pixels = fetched[url]
        if pixels is None:
            portrait_offsets[url] = 0xffffffff
            continue
        key=hashlib.sha256(pixels).hexdigest()
        if key not in seen:
            seen[key]=len(art); art+=pack_image(pixels)
        portrait_offsets[url]=seen[key]
        portrait_audit.append({'url':url,'source_sha256':sha,'offset':seen[key],'kind':'portrait'})
    (OUT / 'art.bin').write_bytes(art)
    manifest_path=ROOT / 'assets/source/gba-reference-images.json'
    if manifest_path.exists():
        previous={r['url']:r['source_sha256'] for r in json.loads(manifest_path.read_text(encoding='utf-8'))['records']}
        for row in audit:
            if row['url'] in previous and previous[row['url']] and row['source_sha256']!=previous[row['url']]:
                raise ValueError('GBA source image hash changed: '+row['url'])
    manifest_path.write_text(json.dumps({'records':[{k:r[k] for k in ('url','source_sha256')} for r in audit]},indent=2)+'\n',encoding='utf-8')
    strings = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -/:+.,()%?[]')
    def ctext(text):
        text = unicodedata.normalize('NFC', str(text or ''))
        strings.update(text)
        return json.dumps(text, ensure_ascii=False)
    type_names = {t['id']: t['name'] for t in catalog['types']}
    moves = sorted(catalog['moves'])
    move_idx = {m: i for i, m in enumerate(moves)}
    move_lines = []
    for mid in moves:
        m = catalog['moves'][mid]
        kind = {'Physical':'物理','Special':'特殊','Status':'变化'}[m['category']]
        move_lines.append('{'+','.join([ctext(m['name_zh']),ctext(type_names.get(m['type'],m['type'])+'/'+kind),str(m['power'] or 0),str(0 if m['accuracy'] is True else m['accuracy']),str(m['pp']),ctext(descriptions['moves'].get(mid) or '此招式效果尚未核实。')])+'}')
    plan_lines = []
    plan_indexes = {}; learnsets = []; infos = []; move_sources = []
    for i, p in enumerate(plans):
        plan_indexes.setdefault(p['entry_id'], []).append(i)
        item_text = '\n'.join([p['item']['name_zh'],p['item']['effect'], '替代道具：'+('、'.join(a['name'] for a in p['alternative_items']) or '来源未提供'), '携带条件及获取尚待本项目配置。'])
        strategy = '\n'.join([p['role'],p['label'],'赛制：'+p['format'], '单打' if p['battle_kind']==1 else '双打', '参考等级：'+str(p['level']), '携带：'+p['item']['name_zh'], '特性：'+p['ability']['name_zh'], '性格：'+p['nature_zh'], '招式：'+'、'.join(m['name_zh'] for m in p['moves']), '太晶属性：'+(type_names.get(p['tera_type'],p['tera_type']) or '未指定'), *p['strategy_notes'],p['usage_note'], '来源：Smogon / pkmn 固定快照', '校验：pokemon-showdown 0.11.11'])
        plan_lines.append('{'+','.join([ctext(p['role']),ctext(p['format']),ctext(p['item']['name_zh']),ctext(p['ability']['name_zh']),ctext(p['nature_zh']),'{'+','.join(ctext(p['moves'][i]['name_zh'] if i < len(p['moves']) else '') for i in range(4))+'}',ctext(item_text),ctext(strategy)])+'}')
    extras = []; variants = []; decoded_sources = []
    entry_by_id = {e['entry_id']:e for e in catalog['entries']}
    by_name = {e['name_reference']:e for e in catalog['entries']}
    indexes = []
    for e in catalog['entries']:
        strings.update(unicodedata.normalize('NFC', e['name_zh_hans']))
        strings.update(unicodedata.normalize('NFC', e['name_reference']))
        pools = sorted(set(m for pool in e['move_pool_ids'] for m in catalog['move_pools'][pool] if m in move_idx))
        start = len(learnsets); learnsets.extend(move_idx[m] for m in pools)
        for m in pools:
            codes = sorted({s for pool in e['move_pool_ids'] for s in catalog['move_pools'][pool].get(m,[])})
            move_sources.append(ctext(' '.join(codes)))
            methods = {'L':'升级 Lv.','M':'招式机器','T':'招式教学','E':'蛋招式','S':'活动编号 ', 'D':'梦世界','V':'虚拟主机转移','R':'特殊传授','C':'捕获来源'}
            decoded_sources.append(ctext('\n'.join(f'第{s[0]}世代 '+methods.get(s[1:2],'来源代码 ')+ (s[2:] if s[1:2] in ('L','S') else '' if s[1:2] in methods else s) for s in codes)))
        pstart = len(indexes); indexes.extend(plan_indexes.get(e['entry_id'], []))
        abilities = ' / '.join(dict.fromkeys(catalog['abilities'][a['id']]['name_zh'] for a in e['abilities']))
        list_name=e['name_zh_hans'].replace(' · ','·').replace('超极巨化','超巨').replace('超级进化','Mega').replace('极巨化','极巨')
        infos.append('{'+','.join([str(portrait_offsets[e['art_reference']['variants']['front_default']])+'u',str(start),str(len(pools)),str(pstart),str(len(indexes)-pstart),ctext('/'.join(type_names[t] for t in e['types'])),ctext(abilities),ctext(catalog['categories'][e['category_id']-1]['name']),ctext(list_name)])+'}')
        variants.append('{'+','.join(str(offsets.get(e['art_reference']['variants'].get(k),0xffffffff))+'u' for k in VARIANTS)+'}')
        ability_text = '\n'.join(('隐藏特性：' if a['slot']=='H' else '特性：')+catalog['abilities'][a['id']]['name_zh']+'\n'+(descriptions['abilities'].get(a['id']) or '本参考库没有对应的效果说明。') for a in e['abilities'])
        ability_text += '\n特性名称来自用户版本；独立编号，效果尚待核实。' if e.get('source_rom_evidence') else '\n效果为固定第九世代参考原文；形态是否采用该特性，以本项目审核为准。'
        evolution = []
        if e.get('prevo'):
            pre = by_name.get(e['prevo']); evolution.append('进化前：'+(pre['name_zh_hans'] if pre else e['prevo']))
        for edge in e.get('evolution_edges',[]):
            evolution.append(edge['name_zh']+'：'+edge['summary_zh']+'；'+'；'.join(str(edge[k]) for k in ('item_zh','move_zh','condition') if edge.get(k)))
        if not evolution: evolution.append('此参考条目没有常规进化路线。')
        evolution.append('以上为来源规则；不同世代可能有差异，本项目进化条件尚待接入。')
        transition = [e.get('transition',{}).get('summary_zh',''), e.get('mechanic_note','')]
        if e.get('required_items_zh'): transition.append('所需道具：'+'、'.join(e['required_items_zh']))
        t=e.get('form_transition_reference') or {}
        if t.get('required_move'): transition.append('所需招式：'+t['required_move'])
        if e['category'] in ('dynamax','gigantamax'): transition.append('极巨化不修改六项种族值；改变的是实际 HP，极巨等级 0 为 1.5 倍，等级 10 为 2 倍。超极巨化另有外观与专属极巨招式。')
        transition.append('羁绊与其他形态的触发、解除条件须以已核实来源及本项目规则为准。')
        acquisition = ['真新镇大木研究所：妙蛙种子、小火龙、杰尼龟三选一。仅普通形态。' if e['entry_id'] in ('dex:bulbasaur:base','dex:charmander:base','dex:squirtle:base') else '本项目获取地点尚未配置。',e.get('acquisition',{}).get('note',''),'登记规则：'+e['registration_rule'], '查看参考资料不等于已经遇见或捕获。']
        identity = [e['name_zh_hans'],e['name_reference'],'身高：'+str(e.get('height_m') if e.get('height_m') is not None else '未知')+' m','体重：'+str(e.get('weight_kg') if e.get('weight_kg') is not None else '未知')+' kg']
        facts=e.get('species_facts') or {}
        if facts: identity += ['捕获率参数：'+str(facts.get('capture_rate','未知')), '孵化周期参数：'+str(facts.get('egg_cycles','未知')), '性别比例参数：'+str(facts.get('gender_rate','未知'))+'（-1无性别，0全雄，8全雌，其余为雌性占八分之几）']
        evidence = identity+['种族值状态：'+e.get('stats_status','未知'), '招式表状态：'+e.get('move_pool_status','未知'), '特性状态：'+e.get('ability_status','未知'), '战斗数据：尚未正式审定', '来源招式是跨世代并集；不代表可以同时携带。','羁绊条目：双 ROM 的图像与数值核对不等于已完成触发规则核验。' if e['research_only'] else '图鉴资料与游戏捕捉进度独立。']
        if e.get('source_rom_evidence'):
            evidence[-1]='究极绿宝石用户版：单份 ROM 提取；获取、招式、永久保持与战斗规则仍待核实。'
        extras.append('{'+','.join(ctext('\n'.join(v) if isinstance(v,list) else v) for v in (ability_text,evolution,transition,acquisition,evidence))+'}')
    # Include all authored GBA UI literals in the font subset.
    for file in (ROOT / 'adapters/gba').glob('*.[ch]'):
        strings.update(file.read_text(encoding='utf-8'))
    for file in (ROOT / 'core/src').glob('adventure.c'):
        strings.update(file.read_text(encoding='utf-8'))
    for file in (ROOT / 'content/pallet-town').glob('*.json'):
        strings.update(file.read_text(encoding='utf-8'))
    opening=json.loads((ROOT/'content/opening/prologue.json').read_text(encoding='utf-8'))
    for scene in opening['scenes']:
        strings.update(scene['title'])
        for beat in scene['beats']:
            strings.update(beat.get('speaker',''))
            for value in beat.get('lines',[]):strings.update(value)
    cast=json.loads((ROOT/'assets/characters/manifest.json').read_text(encoding='utf-8'))
    for person in cast['portraits']:
        strings.update(person['name']);strings.update(person['caption'])
    font_path=ROOT / '.cache/toolchains/unifont-16.0.04.hex.gz'
    assert hashlib.sha256(font_path.read_bytes()).hexdigest() == 'f9c8c7802453f47be02677176aeac2342ee96d354fad7a26cedcce48e68e1d9f'
    glyphs={}
    for line in gzip.decompress(font_path.read_bytes()).decode().splitlines():
        code, bits = line.split(':')
        if chr(int(code,16)) in strings:
            glyphs[int(code,16)] = bytes.fromhex(bits)
    missing=sorted(ord(c) for c in strings if ord(c)>=32 and ord(c) not in glyphs)
    if missing:
        raise ValueError(f'Uncovered font glyphs: {missing}')
    font=bytearray(); glyph_lines=[]
    for code,bits in sorted(glyphs.items()):
        glyph_lines.append('{'+f'{code},{len(font)},{8 if len(bits)==16 else 16}'+'}');font+=bits
    small_glyphs = load_pixel_glyphs(ROOT, strings)
    small_lines = []
    for code,(width,bits) in sorted(small_glyphs.items()):
        small_lines.append('{'+f'{code},{len(font)},{width}'+'}'); font += bits
    (OUT / 'font.bin').write_bytes(font)
    header='''#ifndef OMNI_GBA_DATA_H
#define OMNI_GBA_DATA_H
#include <stdint.h>
typedef struct {uint32_t art,move_start;uint16_t move_count,plan_start,plan_count;const char *types,*abilities,*category,*list_name;} GbaInfo;
typedef struct {const char *name,*kind;uint16_t power,accuracy,pp;const char *effect;} GbaMove;
typedef struct {const char *role,*format,*item,*ability,*nature,*moves[4],*item_detail,*strategy;} GbaPlanText;
typedef struct {const char *abilities,*evolution,*transition,*acquisition,*evidence;} GbaExtra;
typedef struct {uint32_t code,offset;uint8_t width;} GbaGlyph;
extern const GbaInfo gba_info[];
extern const GbaMove gba_moves[];
extern const GbaPlanText gba_plan_text[];
extern const GbaExtra gba_extra[];
extern const uint32_t gba_variants[][8];
extern const uint16_t gba_learnsets[],gba_plan_indexes[];
extern const char *const gba_move_sources[];
extern const char *const gba_move_sources_readable[];
extern const unsigned char gba_art[],gba_font[];
extern const GbaGlyph gba_glyphs[];
extern const GbaGlyph gba_small_glyphs[];
extern const unsigned gba_glyph_count;
extern const unsigned gba_small_glyph_count;
#endif
'''
    (OUT / 'gba_data.h').write_text(header)
    source='#include "gba_data.h"\n'
    for declaration,rows in [('GbaInfo gba_info',infos),('GbaMove gba_moves',move_lines),('GbaPlanText gba_plan_text',plan_lines),('GbaExtra gba_extra',extras),('GbaGlyph gba_glyphs',glyph_lines),('GbaGlyph gba_small_glyphs',small_lines)]:
        source+=f'const {declaration}[]={{\n'+',\n'.join(rows)+'\n};\n'
    source+='const uint16_t gba_learnsets[]={'+','.join(map(str,learnsets))+'};\n'
    source+='const char *const gba_move_sources[]={'+','.join(move_sources)+'};\n'
    source+='const char *const gba_move_sources_readable[]={'+','.join(decoded_sources)+'};\n'
    source+='const uint32_t gba_variants[][8]={'+','.join(variants)+'};\n'
    source+='const uint16_t gba_plan_indexes[]={'+','.join(map(str,indexes))+'};\n'
    source+=f'const unsigned gba_glyph_count={len(glyphs)};\n'
    source+=f'const unsigned gba_small_glyph_count={len(small_glyphs)};\n'
    (OUT / 'gba_data.c').write_text(source,encoding='utf-8')
    # Zig's assembly cache does not track .incbin inputs. Bind its cache key to
    # BOTH embedded payloads so a changed font subset cannot reuse old bytes.
    blob_hash=hashlib.sha256(art+font).hexdigest()
    (OUT / 'blobs.s').write_text(f'/* Embedded payload SHA-256: {blob_hash} */\n'+'.section .rodata\n.balign 4\n.global gba_art\ngba_art:\n.incbin "build/gba/art.bin"\n.balign 4\n.global gba_font\ngba_font:\n.incbin "build/gba/font.bin"\n')
    (OUT / 'asset-report.json').write_text(json.dumps({'images':audit,'portraits':portrait_audit,'unique_images':len(seen),'art_bytes':len(art),'glyph_count':len(glyphs),'small_glyph_count':len(small_glyphs),'missing_images':sum(x['error'] is not None for x in audit)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'GBA art {len(art)} bytes; glyphs {len(glyphs)}; missing images {sum(x[1] is None for x in fetched.values())}',flush=True)


if __name__=='__main__':main()
