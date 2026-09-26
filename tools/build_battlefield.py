"""Native source tiles and object-event frames -> authored war stage.
No rendered illustration, screenshot, generated creature art or game ROM here.
"""
import io,json,hashlib
from PIL import Image
from build_opening_stages import ROOT,OUT,get,render,rgba555,records

def compile_war():
    assert json.loads((ROOT/'content/opening/prologue.json').read_text('utf8'))['stages'][0]['kind']=='battlefield', 'GBA war stage must occupy slot zero'
    source_manifest=ROOT/'assets/source/battlefield.json'
    pinned={f['path']:f for f in json.loads(source_manifest.read_text('utf8'))['files']} if source_manifest.exists() else {}
    data=json.loads((ROOT/'content/opening/battlefield.json').read_text('utf8'))
    layouts={l.get('id'):l for l in json.loads(get('data/layouts/layouts.json'))['layouts']}
    meta=json.loads(get('data/maps/ViridianCity/map.json'))
    source,_,_=render(layouts[meta['layout']],True)
    tiles={k:source.crop((x*16,y*16,x*16+16,y*16+16)) for k,(x,y) in data['tiles'].items()}
    w,h=data['size'];bg=Image.new('RGB',(w*16,h*16));terrain=[]
    for y,row in enumerate(data['map']):
        assert len(row)==w
        for x,c in enumerate(row):
            bg.paste(tiles[c],(x*16,y*16));terrain.append(2 if c in '~lr' else 1 if c in '#TABCD|' else 0)
    blob=bytearray();sprites=[]
    for s in data['sprites']:
        im=Image.open(io.BytesIO(get(s['path'])));pal=im.getpalette();fw,fh=s['frame'];offset=len(blob)
        assert im.width%fw==0 and im.height==fh
        for frame in range(im.width//fw):
            canvas=Image.new('RGBA',(fw,fh))
            for y in range(fh):
                for x in range(fw):
                    c=im.getpixel((frame*fw+x,y))
                    if c:canvas.putpixel((x,y),(*pal[c*3:c*3+3],255))
            blob+=rgba555(canvas)
        sprites.append('{'+','.join(map(str,[offset,fw,fh,im.width//fw,int(s['human'])]))+'}')
    # Enforce traversable routes across the entire foot rectangle, not only endpoints.
    actors=data['actors'];count=len(actors)
    assert 0<count<=255
    for a in actors:
        assert 0<=a['target']<count and a['team'] in (0,1)
        assert 0<=a['attack']<=5 and a['layer'] in (0,1,2) and 0<=a['sprite']<len(sprites)
        assert not a['attack'] or actors[a['target']]['team']!=a['team'], 'Attack target must be an opponent'
        x,y=a['at'];tx,ty=a['to'];assert x==tx or y==ty
        distance=abs(x-tx)+abs(y-ty)
        for step in range(distance+1):
            xx=x+(1 if tx>x else -1 if tx<x else 0)*step
            yy=y+(1 if ty>y else -1 if ty<y else 0)*step
            for fx,fy in ((xx+2,yy-12),(xx+13,yy-1)):
                assert 0<=fx<w*16 and 0<=fy<h*16,a['id']
                cell=terrain[fy//16*w+fx//16]
                assert a['layer']==2 or cell==(2 if a['layer']==1 else 0),(a['id'],xx,yy,cell)
    rows=['{'+','.join(map(str,[*a['at'],*a['to'],a['start'],a['duration'],a['phase'],a['sprite'],a['team'],a['layer'],a['target'],a['attack'],a['role']]))+'}' for a in actors]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'war.bin').write_bytes(blob)
    (OUT/'war.s').write_text(f'/* {hashlib.sha256(blob).hexdigest()} */\n.section .rodata\n.balign 4\n.global omni_war_art\nomni_war_art:\n.incbin "build/pallet/war.bin"\n')
    (OUT/'war_data.h').write_text('''#ifndef OMNI_WAR_DATA_H
#define OMNI_WAR_DATA_H
#include "omni/battlefield.h"
typedef struct {uint32_t offset;uint8_t w,h,frames,human;} OmniWarSprite;
extern const unsigned char omni_war_art[];
extern const OmniWarActor omni_war_actors[];
extern const OmniWarSprite omni_war_sprites[];
'''+f'#define OMNI_WAR_COUNT {count}\n#define OMNI_WAR_WIDTH {w*16}\n#define OMNI_WAR_HEIGHT {h*16}\n#endif\n')
    (OUT/'war_data.c').write_text('#include "war_data.h"\nconst OmniWarActor omni_war_actors[]={'+','.join(rows)+'};\nconst OmniWarSprite omni_war_sprites[]={'+','.join(sprites)+'};\n')
    (OUT/'war-terrain.json').write_text(json.dumps({'width':w,'height':h,'cells':terrain,'actors':actors}))
    for path,record in records.items():
        assert path not in pinned or pinned[path]['sha256']==record['sha256'], 'Battlefield source changed: '+path
    source_manifest.write_text(json.dumps({'scope':'Authored unnamed battlefield assembled from native FireRed tiles and object-event frames; not a copy of an official map or of Emerald event scripts. Procedural move effects are Omni authored.','files':list(records.values()),'actors':count,'sprite_bytes':len(blob)},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return bg,Image.new('L',bg.size),[int(c!=0) for c in terrain]
