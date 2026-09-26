"""Compile player-safe prologue and traceable cast portraits for GBA.

The author bible is NEVER used as a source for runtime text. Portrait imports
are format conversion only; source pixels and author credits are retained.
"""
import hashlib
import json
import struct
import urllib.request
import copy
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
    scene_rows = []
    beat_audit=[]
    for chapter,s in enumerate(opening['scenes']):
        assert set(s['actors']) <= chars, 'Unregistered prologue actor'
        assert 0<=s['tone']<=2 and len(s['cast'])<=4
        stage=next(i for i,m in enumerate(opening['stages']) if m['id']==s['stage'])
        width,height=opening['stages'][stage]['crop'][2:]
        poses=copy.deepcopy(s['cast']);camera=s.get('camera',[0,0]);monitor=0
        assert {a['actor'] for a in poses}<=set(s['actors'])
        for bi,beat in enumerate(s['beats']):
            lines=beat.get('lines',['','']);speaker=beat.get('speaker','')
            assert len(lines)==2 and all(len(t)<=18 for t in lines),(s['id'],lines)
            if beat.get('actor'):assert beat['actor'] in s['actors']
            end_camera=beat.get('camera',camera);cx,cy=end_camera
            assert 0<=cx<=max(0,width-240) and 0<=cy<=height-112,(s['id'],end_camera)
            duration=beat.get('ticks',beat.get('wait',192+sum(map(len,lines))*4))
            if beat.get('effect')=='monitor':monitor=1
            if beat.get('effect')=='monitor_off':monitor=0
            actors=[]
            for a in poses:
                x,y=a['at'];tx,ty=beat.get('move',{}).get(a['actor'],a['at'])
                assert 0<=tx<=width-16 and 0<=ty<=height,(a['actor'],tx,ty)
                assert x==tx or y==ty,'Walking must follow tile axes'
                direction=beat.get('face',{}).get(a['actor'],(3 if tx>x else 2 if tx<x else 0 if ty>y else 1) if (tx,ty)!=(x,y) else a['face'])
                emote=int(a['actor'] in beat.get('emote',{}))
                actors.append('{'+','.join(map(str,[x,y,tx,ty,opening['sprites'].index(a['sprite']),direction,emote]))+'}')
                a['at']=[tx,ty];a['face']=direction
            actors+=['{0}']*(4-len(actors))
            effect={'healing':1,'radio':2,'papers':3}.get(beat.get('effect'),0)
            speaker_actor=next((i for i,a in enumerate(poses) if a['actor']==beat.get('actor')),255)
            values=[cs(s['title']),cs(speaker),cs(lines[0]),cs(lines[1]),str(duration),*map(str,[*camera,*end_camera,chapter,stage,s['tone'],s['music'],len(poses),effect,monitor,int(bi==0),int(bi==len(s['beats'])-1),sum(map(len,lines)),speaker_actor]),'{'+','.join(actors)+'}']
            scene_rows.append('{'+','.join(values)+'}')
            beat_audit.append({'cue':len(scene_rows)-1,'chapter':chapter,'scene':s['id'],'beat':bi,'duration':duration,'dialogue':bool(speaker),'speaker':speaker,'actor':beat.get('actor'),'movement':bool(beat.get('move') or beat.get('camera'))})
            camera=end_camera
    assert len(scene_rows)<=255
    (OUT/'presentation_data.h').write_text('''#ifndef OMNI_PRESENTATION_DATA_H
#define OMNI_PRESENTATION_DATA_H
#include <stdint.h>
typedef struct {const char *id,*name,*caption;uint32_t offset;} OmniCastPortrait;
typedef struct {int16_t x,y,tx,ty;uint8_t sprite,face,emote;} OmniIntroActor;
typedef struct {const char *title,*speaker,*line1,*line2;uint16_t duration;int16_t cx,cy,tx,ty;uint8_t chapter,stage,tone,music,actor_count,effect,monitor,fade_in,fade_out,letters,speaker_actor;OmniIntroActor actors[4];} OmniIntroScene;
extern const unsigned char omni_cast_blob[];
extern const OmniCastPortrait omni_cast[];
extern const OmniIntroScene omni_intro[];
'''+f'#define OMNI_CAST_COUNT {len(rows)}\n#define OMNI_INTRO_COUNT {len(scene_rows)}\n#define OMNI_INTRO_CHAPTERS {len(opening["scenes"])}\n#endif\n',encoding='utf-8')
    (OUT/'presentation_data.c').write_text('#include "presentation_data.h"\nconst OmniCastPortrait omni_cast[]={\n'+',\n'.join(rows)+'\n};\nconst OmniIntroScene omni_intro[]={\n'+',\n'.join(scene_rows)+'\n};\n',encoding='utf-8')
    (OUT/'cast.bin').write_bytes(blob)
    (OUT/'cast.s').write_text('.section .rodata\n.balign 4\n.global omni_cast_blob\nomni_cast_blob:\n.incbin "build/pallet/cast.bin"\n')
    (OUT/'presentation-report.json').write_text(json.dumps({'cast':audit,'prologue_scenes':len(opening['scenes']),'cues':beat_audit,'seconds':sum(b['duration'] for b in beat_audit)/64,'rom_bytes':len(blob),'private_bible_compiled':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Cast: {len(rows)} portraits, {len(blob)} bytes; prologue: {len(opening["scenes"])} scenes, {len(scene_rows)} cues')


if __name__ == '__main__':
    compile_assets()
