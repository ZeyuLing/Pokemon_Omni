"""Compile player-safe prologue and traceable cast portraits for GBA.

The author bible is NEVER used as a source for runtime text. Portrait imports
are format conversion only; source pixels and author credits are retained.
"""
import hashlib
import json
import struct
import urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/pallet'
MANIFEST = ROOT/'assets/characters/manifest.json'


def cs(s):
    return json.dumps(s, ensure_ascii=False)


def compile_assets():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text('utf-8'))
    opening = json.loads((ROOT/'content/opening/prologue.json').read_text('utf-8'))
    assert opening['visibility'] == 'player_safe'
    chars = {c['id'] for c in json.loads((ROOT/'content/story/characters.json').read_text('utf-8'))['characters']}
    scenes = json.loads((OUT/'scene-audit.json').read_text('utf-8'))
    blob = bytearray()
    rows = []
    audit = []
    for entry in manifest['portraits']:
        assert entry['actor'] in chars
        target = ROOT/entry['source_path']
        if not target.exists():
            assert entry.get('url'), f'Missing generated source: {target}'
            target.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(entry['url'], headers={'User-Agent':'PokemonOmni-local-asset-import/1.0'})
            target.write_bytes(urllib.request.urlopen(req, timeout=45).read())
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        if entry.get('sha256') and entry['sha256'] != sha:
            raise ValueError('Cast source hash changed: '+entry['actor'])
        entry['sha256'] = sha
        im = Image.open(target).convert('RGBA')
        if entry.get('cell') is not None:
            assert im.size == (1536, 1024)
            cell = entry['cell']; x = (cell % 3)*512; y = (cell//3)*512
            # Compiles the generated draft atlas; does not repaint the artwork.
            im = im.crop((x, y, x+512, y+512)).resize((80, 80), Image.Resampling.NEAREST)
        assert im.width <= 80 and im.height <= 80, 'Do not resize imported artist sprites'
        canvas = Image.new('RGBA', (80, 80))
        canvas.paste(im, ((80-im.width)//2, 80-im.height))
        offset = len(blob)
        for r,g,b,a in canvas.get_flattened_data():
            blob += struct.pack('<H', 0x8000 if a<128 else (r>>3)|((g>>3)<<5)|((b>>3)<<10))
        out = OUT/'cast'/f'{entry["actor"]}.png'
        out.parent.mkdir(exist_ok=True); canvas.save(out)
        rows.append('{'+','.join([cs(entry['actor']),cs(entry['name']),cs(entry['caption']),str(offset)])+'}')
        audit.append({'actor':entry['actor'],'bytes':12800,'offset':offset,'source_sha256':sha,
                      'status':entry['status'],'runtime_size':[80,80]})
    ids = [e['actor'] for e in manifest['portraits']]
    scene_rows = []
    for s in opening['scenes']:
        assert set(s['actors']) <= chars, 'Unregistered prologue actor'
        assert 0<=s['tone']<=3 and 1<=s['map']<=len(scenes)
        assert len(s['lines']) == 2 and all(len(t)<=18 for t in s['lines'])
        assert len(s['title']) <= 23
        m = scenes[s['map']-1]; x,y = s['camera']
        assert 0<=x<=max(0,m['width']*16-240) and 0<=y<=max(0,m['height']*16-96)
        portrait = ids.index(s['portrait']) if s['portrait'] else 255
        scene_rows.append('{'+','.join([cs(s['title']),cs(s['lines'][0]),cs(s['lines'][1]),
            str(s['map']),str(s['tone']),str(portrait),str(x),str(y),str(s['duration_ticks'])])+'}')
    (OUT/'presentation_data.h').write_text('''#ifndef OMNI_PRESENTATION_DATA_H
#define OMNI_PRESENTATION_DATA_H
#include <stdint.h>
typedef struct {const char *id,*name,*caption;uint32_t offset;} OmniCastPortrait;
typedef struct {const char *title,*line1,*line2;uint8_t map,tone,portrait;uint16_t x,y,duration;} OmniIntroScene;
extern const unsigned char omni_cast_blob[];
extern const OmniCastPortrait omni_cast[];
extern const OmniIntroScene omni_intro[];
'''+f'#define OMNI_CAST_COUNT {len(rows)}\n#define OMNI_INTRO_COUNT {len(scene_rows)}\n#endif\n',encoding='utf-8')
    (OUT/'presentation_data.c').write_text('#include "presentation_data.h"\nconst OmniCastPortrait omni_cast[]={\n'+',\n'.join(rows)+'\n};\nconst OmniIntroScene omni_intro[]={\n'+',\n'.join(scene_rows)+'\n};\n',encoding='utf-8')
    (OUT/'cast.bin').write_bytes(blob)
    (OUT/'cast.s').write_text('.section .rodata\n.balign 4\n.global omni_cast_blob\nomni_cast_blob:\n.incbin "build/pallet/cast.bin"\n')
    (OUT/'presentation-report.json').write_text(json.dumps({'cast':audit,'prologue_scenes':len(scene_rows),'rom_bytes':len(blob),'private_bible_compiled':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Cast: {len(rows)} portraits, {len(blob)} bytes; prologue: {len(scene_rows)} scenes')


if __name__ == '__main__':
    compile_assets()
