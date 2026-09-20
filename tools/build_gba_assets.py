"""Build local GBA image/font/text assets; no generated binaries are committed."""
import concurrent.futures
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/gba'
CACHE = ROOT / '.cache/gba-art'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT / 'content/pokedex/catalog.json').read_text(encoding='utf-8'))
    plans = json.loads((ROOT / 'content/training/plans.json').read_text(encoding='utf-8'))['records']
    urls = sorted({e['art_reference']['variants']['front_default'] for e in catalog['entries']})
    def fetch(url):
        target = CACHE / (hashlib.sha256(url.encode()).hexdigest() + '.img')
        if url.startswith('/rocket-art/'):
            data = (ROOT / 'assets/imported/rocket-user/bond-sprites' / url.split('/')[-1]).read_bytes()
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
                return url, None, str(last)
        image = Image.open(io.BytesIO(data)).convert('RGBA')
        image.thumbnail((64, 64), Image.Resampling.LANCZOS if image.width > 128 else Image.Resampling.NEAREST)
        canvas = Image.new('RGBA', (64, 64))
        canvas.alpha_composite(image, ((64 - image.width) // 2, (64 - image.height) // 2))
        pixels = bytearray()
        for r, g, b, a in canvas.get_flattened_data():
            pixels += struct.pack('<H', 0x8000 if a < 96 else (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
        return url, bytes(pixels), hashlib.sha256(data).hexdigest()
    fetched = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for i, result in enumerate(pool.map(fetch, urls)):
            fetched[result[0]] = result
            if i % 100 == 0:
                print(f'Images {i + 1}/{len(urls)}', flush=True)
    art = bytearray(); offsets = {}; seen = {}; audit = []
    for url in urls:
        _, image, sha = fetched[url]
        if image is None:
            offsets[url] = 0xFFFFFFFF
        else:
            key = hashlib.sha256(image).hexdigest()
            if key not in seen:
                seen[key] = len(art); art += image
            offsets[url] = seen[key]
        audit.append({'url': url, 'source_sha256': sha if image else None, 'offset': offsets[url], 'error': None if image else sha})
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
        text = str(text or '')
        strings.update(text)
        return json.dumps(text, ensure_ascii=False)
    type_names = {t['id']: t['name'] for t in catalog['types']}
    moves = sorted(catalog['moves'])
    move_idx = {m: i for i, m in enumerate(moves)}
    move_lines = []
    for mid in moves:
        m = catalog['moves'][mid]
        kind = {'Physical':'物理','Special':'特殊','Status':'变化'}[m['category']]
        move_lines.append('{'+','.join([ctext(m['name_zh']),ctext(type_names.get(m['type'],m['type'])+'/'+kind),str(m['power'] or 0),str(0 if m['accuracy'] is True else m['accuracy']),str(m['pp'])])+'}')
    plan_lines = []
    plan_indexes = {}; learnsets = []; infos = []; move_sources = []
    for i, p in enumerate(plans):
        plan_indexes.setdefault(p['entry_id'], []).append(i)
        plan_lines.append('{'+','.join([ctext(p['role']),ctext(p['format']),ctext(p['item']['name_zh']),ctext(p['ability']['name_zh']),ctext(p['nature_zh']),'{'+','.join(ctext(p['moves'][i]['name_zh'] if i < len(p['moves']) else '') for i in range(4))+'}'])+'}')
    indexes = []
    for e in catalog['entries']:
        strings.update(e['name_zh_hans']); strings.update(e['name_reference'])
        pools = sorted(set(m for pool in e['move_pool_ids'] for m in catalog['move_pools'][pool] if m in move_idx))
        start = len(learnsets); learnsets.extend(move_idx[m] for m in pools)
        for m in pools:
            move_sources.append(ctext(' '.join(sorted({s for pool in e['move_pool_ids'] for s in catalog['move_pools'][pool].get(m,[])}))))
        pstart = len(indexes); indexes.extend(plan_indexes.get(e['entry_id'], []))
        abilities = ' / '.join(dict.fromkeys(catalog['abilities'][a['id']]['name_zh'] for a in e['abilities']))
        infos.append('{'+','.join([str(offsets[e['art_reference']['variants']['front_default']])+'u',str(start),str(len(pools)),str(pstart),str(len(indexes)-pstart),ctext('/'.join(type_names[t] for t in e['types'])),ctext(abilities),ctext(catalog['categories'][e['category_id']-1]['name'])])+'}')
    # Include all authored GBA UI literals in the font subset.
    for file in (ROOT / 'adapters/gba').glob('*.[ch]'):
        strings.update(file.read_text(encoding='utf-8'))
    for file in (ROOT / 'core/src').glob('adventure.c'):
        strings.update(file.read_text(encoding='utf-8'))
    for file in (ROOT / 'content/pallet-town').glob('*.json'):
        strings.update(file.read_text(encoding='utf-8'))
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
    (OUT / 'font.bin').write_bytes(font)
    header='''#ifndef OMNI_GBA_DATA_H
#define OMNI_GBA_DATA_H
#include <stdint.h>
typedef struct {uint32_t art,move_start;uint16_t move_count,plan_start,plan_count;const char *types,*abilities,*category;} GbaInfo;
typedef struct {const char *name,*kind;uint16_t power,accuracy,pp;} GbaMove;
typedef struct {const char *role,*format,*item,*ability,*nature,*moves[4];} GbaPlanText;
typedef struct {uint32_t code,offset;uint8_t width;} GbaGlyph;
extern const GbaInfo gba_info[];
extern const GbaMove gba_moves[];
extern const GbaPlanText gba_plan_text[];
extern const uint16_t gba_learnsets[],gba_plan_indexes[];
extern const char *const gba_move_sources[];
extern const unsigned char gba_art[],gba_font[];
extern const GbaGlyph gba_glyphs[];
extern const unsigned gba_glyph_count;
#endif
'''
    (OUT / 'gba_data.h').write_text(header)
    source='#include "gba_data.h"\n'
    for declaration,rows in [('GbaInfo gba_info',infos),('GbaMove gba_moves',move_lines),('GbaPlanText gba_plan_text',plan_lines),('GbaGlyph gba_glyphs',glyph_lines)]:
        source+=f'const {declaration}[]={{\n'+',\n'.join(rows)+'\n};\n'
    source+='const uint16_t gba_learnsets[]={'+','.join(map(str,learnsets))+'};\n'
    source+='const char *const gba_move_sources[]={'+','.join(move_sources)+'};\n'
    source+='const uint16_t gba_plan_indexes[]={'+','.join(map(str,indexes))+'};\n'
    source+=f'const unsigned gba_glyph_count={len(glyphs)};\n'
    (OUT / 'gba_data.c').write_text(source,encoding='utf-8')
    # Zig's assembly cache does not track .incbin inputs. Bind its cache key to
    # BOTH embedded payloads so a changed font subset cannot reuse old bytes.
    blob_hash=hashlib.sha256(art+font).hexdigest()
    (OUT / 'blobs.s').write_text(f'/* Embedded payload SHA-256: {blob_hash} */\n'+'.section .rodata\n.balign 4\n.global gba_art\ngba_art:\n.incbin "build/gba/art.bin"\n.balign 4\n.global gba_font\ngba_font:\n.incbin "build/gba/font.bin"\n')
    (OUT / 'asset-report.json').write_text(json.dumps({'images':audit,'unique_images':len(seen),'art_bytes':len(art),'glyph_count':len(glyphs),'missing_images':sum(x['error'] is not None for x in audit)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'GBA art {len(art)} bytes; glyphs {len(glyphs)}; missing images {sum(x[1] is None for x in fetched.values())}',flush=True)


if __name__=='__main__':main()
