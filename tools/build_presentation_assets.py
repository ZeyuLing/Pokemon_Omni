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
from opening_blocking import route
from build_rocket_dialogue import width as glyph_width

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
    beat_audit=[];routes=[]
    grids=json.loads((OUT/'opening-collision.json').read_text('utf8'))
    for chapter,s in enumerate(opening['scenes']):
        assert set(s['actors']) <= chars, 'Unregistered prologue actor'
        assert 0<=s['tone']<=2 and len(s['cast'])<=4
        stage=next(i for i,m in enumerate(opening['stages']) if m['id']==s['stage'])
        width,height=opening['stages'][stage]['crop'][2:]
        poses=copy.deepcopy(s['cast']);camera=s.get('camera',[0,0]);monitor=0;music=s['music']
        grid=grids[s['stage']]
        if grid.get('kind')=='illustration':
            assert not poses, 'Illustration stages cannot host walkable sprites'
        assert {a['actor'] for a in poses}<=set(s['actors'])
        for a in poses:route(grid,a['at'],a['at'],[b['at'] for b in poses if b is not a])
        for bi,beat in enumerate(s['beats']):
            lines=beat.get('lines',['','']);speaker=beat.get('speaker','')
            assert len(lines)==2 and all(sum(glyph_width(c) for c in t)<=204 for t in lines),(s['id'],lines)
            if beat.get('actor'):assert beat['actor'] in s['actors']
            end_camera=beat.get('camera',camera);cx,cy=end_camera
            max_y=height-(160 if grid.get('kind') in ('illustration','battlefield') else 112)
            assert 0<=cx<=max(0,width-240) and 0<=cy<=max_y,(s['id'],end_camera)
            duration=beat.get('ticks',beat.get('wait',192+sum(map(len,lines))*4))
            assert len(beat.get('move',{}))<=1, 'One moving actor per cue; other cast members reserve their tiles'
            actor_paths={a['actor']:route(grid,a['at'],beat.get('move',{}).get(a['actor'],a['at']),[b['at'] for b in poses if b is not a]) for a in poses}
            longest=max((len(p)-1 for p in actor_paths.values()),default=0)
            if longest:duration=max(32,longest*24)
            music=beat.get('music',music)
            if beat.get('effect')=='monitor':monitor=1
            if beat.get('effect')=='monitor_off':monitor=0
            actors=[]
            for a in poses:
                x,y=a['at'];tx,ty=beat.get('move',{}).get(a['actor'],a['at'])
                assert 0<=tx<=width-16 and 0<=ty<=height,(a['actor'],tx,ty)
                direction=beat.get('face',{}).get(a['actor'],(3 if tx>x else 2 if tx<x else 0 if ty>y else 1) if (tx,ty)!=(x,y) else a['face'])
                emote=int(a['actor'] in beat.get('emote',{}))
                path=actor_paths[a['actor']];path_offset=len(routes)
                assert len(path)<=255 and path_offset+len(path)<=65535, 'Route exceeds generated data bounds'
                routes.extend(path)
                actors.append('{'+','.join(map(str,[x,y,tx,ty,path_offset,len(path),opening['sprites'].index(a['sprite']),direction,emote]))+'}')
                if len(path)>1 and a['actor'] not in beat.get('face',{}):
                    end,prev=path[-1],path[-2];direction=3 if end[0]>prev[0] else 2 if end[0]<prev[0] else 0 if end[1]>prev[1] else 1
                a['at']=[tx,ty];a['face']=direction
            actors+=['{0}']*(4-len(actors))
            effect={'healing':1,'radio':2,'papers':3}.get(beat.get('effect'),0)
            speaker_actor=next((i for i,a in enumerate(poses) if a['actor']==beat.get('actor')),255)
            fade_in=bi==0 and s['transition']['kind'] in ('fade_in','night_to_morning')
            fade_out=bi==len(s['beats'])-1 and (chapter==len(opening['scenes'])-1 or opening['scenes'][chapter+1]['transition']['kind']=='night_to_morning')
            document=s.get('props',{}).get('document',[-100,-100]);terminal=s.get('props',{}).get('monitor',[-100,-100])
            war_time=sum(b['duration'] for b in beat_audit if b['stage']=='war') if s['stage']=='war' else 0
            values=[cs(s['title']),cs(speaker),cs(lines[0]),cs(lines[1]),str(duration),str(war_time),*map(str,[*camera,*end_camera,*document,*terminal,chapter,stage,s['tone'],music,len(poses),effect,monitor,int(fade_in),int(fade_out),int(bi==0 and s.get('show_title',True)),sum(map(len,lines)),speaker_actor]),'{'+','.join(actors)+'}']
            scene_rows.append('{'+','.join(values)+'}')
            beat_audit.append({'cue':len(scene_rows)-1,'chapter':chapter,'scene':s['id'],'stage':s['stage'],'beat':bi,'duration':duration,'dialogue':bool(speaker),'speaker':speaker,'actor':beat.get('actor'),'movement':bool(beat.get('move') or beat.get('camera')),'paths':actor_paths,'music':music,'fade_in':bool(fade_in),'fade_out':bool(fade_out),'camera':[camera,end_camera]})
            camera=end_camera
    assert len(scene_rows)<=255
    (OUT/'presentation_data.h').write_text('''#ifndef OMNI_PRESENTATION_DATA_H
#define OMNI_PRESENTATION_DATA_H
#include <stdint.h>
#include "omni/stage.h"
typedef struct {const char *id,*name,*caption;uint32_t offset;} OmniCastPortrait;
typedef struct {int16_t x,y,tx,ty;uint16_t path;uint8_t count,sprite,face,emote;} OmniIntroActor;
typedef struct {const char *title,*speaker,*line1,*line2;uint16_t duration,war_time;int16_t cx,cy,tx,ty,document_x,document_y,monitor_x,monitor_y;uint8_t chapter,stage,tone,music,actor_count,effect,monitor,fade_in,fade_out,location_title,letters,speaker_actor;OmniIntroActor actors[4];} OmniIntroScene;
extern const unsigned char omni_cast_blob[];
extern const OmniCastPortrait omni_cast[];
extern const OmniIntroScene omni_intro[];
extern const OmniWalkPoint omni_intro_paths[];
'''+f'#define OMNI_CAST_COUNT {len(rows)}\n#define OMNI_INTRO_COUNT {len(scene_rows)}\n#define OMNI_INTRO_CHAPTERS {len(opening["scenes"])}\n#endif\n',encoding='utf-8')
    (OUT/'presentation_data.c').write_text('#include "presentation_data.h"\nconst OmniWalkPoint omni_intro_paths[]={'+','.join('{'+f'{x},{y}'+'}' for x,y in routes)+'};\nconst OmniCastPortrait omni_cast[]={\n'+',\n'.join(rows)+'\n};\nconst OmniIntroScene omni_intro[]={\n'+',\n'.join(scene_rows)+'\n};\n',encoding='utf-8')
    (OUT/'cast.bin').write_bytes(blob)
    (OUT/'cast.s').write_text(f'/* SHA256 {hashlib.sha256(blob).hexdigest()} */\n'+'.section .rodata\n.balign 4\n.global omni_cast_blob\nomni_cast_blob:\n.incbin "build/pallet/cast.bin"\n')
    (OUT/'presentation-report.json').write_text(json.dumps({'cast':audit,'prologue_scenes':len(opening['scenes']),'cues':beat_audit,'seconds':sum(b['duration'] for b in beat_audit)/64,'rom_bytes':len(blob),'private_bible_compiled':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Cast: {len(rows)} portraits, {len(blob)} bytes; prologue: {len(opening["scenes"])} scenes, {len(scene_rows)} cues')


if __name__ == '__main__':
    compile_assets()
