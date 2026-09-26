"""Compile source-layout rooms, generated cinematic illustrations and sprites.

Illustrations are explicitly noninteractive stages; source-room collision and
foreground masks remain independently reproducible.
"""
import hashlib,io,json,struct,urllib.request
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
REV='c75f352304d529f6ba92d4f74b9cf8b5c3810788'
BASE=f'https://raw.githubusercontent.com/pret/pokefirered/{REV}/'
OUT=ROOT/'build/pallet'
MANIFEST=ROOT/'assets/source/opening-stages.json'
records={}
old={r['path']:r for r in json.loads(MANIFEST.read_text('utf-8'))['files']} if MANIFEST.exists() else {}
def get(path):
    cached=ROOT/'.cache/pallet-source'/path
    if cached.exists():b=cached.read_bytes()
    elif (ROOT/'.cache/pokefirered'/path).exists():b=(ROOT/'.cache/pokefirered'/path).read_bytes()
    else:b=urllib.request.urlopen(BASE+path,timeout=30).read()
    digest=hashlib.sha256(b).hexdigest()
    if path in old:assert digest==old[path]['sha256'],path
    cached.parent.mkdir(parents=True,exist_ok=True);cached.write_bytes(b)
    records[path]={'path':path,'url':BASE+path,'sha256':digest,'bytes':len(b)}
    return b
def rgba555(im,tone=0):
    data=bytearray()
    for r,g,b,a in im.convert('RGBA').get_flattened_data():
        r>>=3;g>>=3;b>>=3
        if tone==1:r=r*4//5;g=g*4//5;b=b*17//20
        if tone==2:r=r*3//5;g=g*5//8;b=min(31,b*7//8+2)
        data+=struct.pack('<H',0x8000 if a<128 else r|(g<<5)|(b<<10))
    return data
def render(layout, with_collision=False):
    names={'gTileset_General':'primary/general','gTileset_Building':'primary/building','gTileset_PalletTown':'secondary/pallet_town','gTileset_GenericBuilding1':'secondary/generic_building_1','gTileset_GenericBuilding2':'secondary/generic_building_2','gTileset_Lab':'secondary/lab','gTileset_ViridianCity':'secondary/viridian_city','gTileset_PokemonCenter':'secondary/pokemon_center','gTileset_Mart':'secondary/mart','gTileset_SilphCo':'secondary/silph_co','gTileset_PokemonLeague':'secondary/pokemon_league'}
    dirs=[f'data/tilesets/{names[layout[k]]}' for k in ['primary_tileset','secondary_tileset']]
    tiles=[];metas=[];attrs=[]
    gfxdirs=[d.replace('/silph_co','/condominiums') for d in dirs]
    if gfxdirs!=dirs:get('src/data/tilesets/graphics.h')
    for d,g in zip(dirs,gfxdirs):
        im=Image.open(io.BytesIO(get(g+'/tiles.png')))
        tiles.append([im.crop((x,y,x+8,y+8)) for y in range(0,im.height,8) for x in range(0,im.width,8)])
        metas.append(list(struct.iter_unpack('<8H',get(d+'/metatiles.bin'))))
        attrs.append([a[0] for a in struct.iter_unpack('<I',get(d+'/metatile_attributes.bin'))])
    palettes=[]
    for i in range(13):palettes.append([tuple(map(int,line.split())) for line in get(gfxdirs[0 if i<7 else 1]+f'/palettes/{i:02d}.pal').decode().splitlines()[3:19]])
    w,h=layout['width'],layout['height'];blocks=[a[0] for a in struct.iter_unpack('<H',get(layout['blockdata_filepath']))]
    bg=Image.new('RGB',(w*16,h*16),palettes[0][0]);mask=Image.new('L',bg.size);collision=[]
    for cell,block in enumerate(blocks):
        mid=block&1023;bank=mid>=640;idx=mid-640 if bank else mid;layer=(attrs[bank][idx]>>29)&3
        behavior=attrs[bank][idx]&511
        collision.append(int(bool(block&0xc00 or behavior in range(0x10,0x16))))
        for part,tile in enumerate(metas[bank][idx]):
            tileid=tile&1023;tb=tileid>=640;ti=tileid-640 if tb else tileid;pixels=tiles[tb][ti];pal=palettes[tile>>12]
            ox=(cell%w)*16+(part%2)*8;oy=(cell//w)*16+((part%4)//2)*8
            for y in range(8):
                for x in range(8):
                    p=pixels.getpixel((7-x if tile&1024 else x,7-y if tile&2048 else y))
                    if part>=4 and not p:continue
                    bg.putpixel((ox+x,oy+y),pal[p])
                    if part>=4 and p and layer!=1:mask.putpixel((ox+x,oy+y),1)
    return (bg,mask,collision) if with_collision else (bg,mask)
def main():
    opening=json.loads((ROOT/'content/opening/prologue.json').read_text('utf-8'))
    layouts={l.get('id'):l for l in json.loads(get('data/layouts/layouts.json'))['layouts']}
    blob=bytearray();stages=[];sprites=[];grids={};illustrations=[]
    (OUT/'stages').mkdir(parents=True,exist_ok=True)
    for s in opening['stages']:
        if s.get('kind')=='illustration':
            asset=json.loads((ROOT/s['manifest']).read_text('utf8'))
            raw=(ROOT/asset['image']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==asset['sha256'], 'Cinematic source hash changed'
            x,y,w,h=s['crop'];assert x==y==0 and w%16==h%16==0
            with Image.open(io.BytesIO(raw)) as source:
                assert list(source.size)==asset['dimensions']
                assert source.width*h==source.height*w, 'Do not stretch cinematic art'
                bg=source.convert('RGB').resize((w,h),Image.Resampling.LANCZOS)
            art=len(blob);blob+=rgba555(bg);mk=len(blob);blob+=bytes(w*h)
            # All tiles blocked: this is an illustration, never a walkable map.
            grid=[1]*(w//16*h//16);co=len(blob);blob+=bytes(grid)
            while len(blob)%4:blob.append(0)
            stages.append('{'+','.join(map(str,[w,h,art,mk,co]))+'}')
            bg.save(OUT/'stages'/f'{s["id"]}.png')
            grids[s['id']]={'width':w//16,'height':h//16,'cells':grid,'source':asset['image'],'crop':s['crop'],'kind':'illustration'}
            illustrations.append({'stage':s['id'],'manifest':s['manifest'],'image':asset['image'],'sha256':asset['sha256'],'runtime_size':[w,h]})
            continue
        meta=json.loads(get(f'data/maps/{s["source"]}/map.json'));layout=layouts[meta['layout']]
        bg,mask,cells=render(layout,True);bg.save(OUT/'stages'/f'{s["id"]}-full.png')
        x,y,w,h=s['crop'];assert x>=0 and y>=0 and x+w<=bg.width and y+h<=bg.height
        assert all(v%16==0 for v in (x,y,w,h)), 'Stage crops must preserve source collision tiles'
        bg=bg.crop((x,y,x+w,y+h));mask=mask.crop((x,y,x+w,y+h));art=len(blob)
        tone=next(c['tone'] for c in opening['scenes'] if c['stage']==s['id'])
        blob+=rgba555(bg,tone);mk=len(blob);blob+=mask.tobytes()
        grid=[cells[ty*layout['width']+tx] for ty in range(y//16,(y+h)//16) for tx in range(x//16,(x+w)//16)]
        co=len(blob);blob+=bytes(grid)
        while len(blob)%4:blob.append(0)
        stages.append('{'+','.join(map(str,[w,h,art,mk,co]))+'}');bg.save(OUT/'stages'/f'{s["id"]}.png')
        grids[s['id']]={'width':w//16,'height':h//16,'cells':grid,'source':s['source'],'crop':s['crop']}
    for name in opening['sprites']:
        im=Image.open(io.BytesIO(get('graphics/object_events/pics/people/'+name+'.png'))).convert('RGBA')
        # Indexed source transparency is color index zero, not PNG metadata.
        original=Image.open(io.BytesIO(get('graphics/object_events/pics/people/'+name+'.png')))
        pal=original.getpalette();height=original.height;count=original.width//16;offset=len(blob)
        for frame in range(count):
            canvas=Image.new('RGBA',(16,32))
            for y in range(min(32,height)):
                for x in range(16):
                    p=original.getpixel((frame*16+x,y))
                    if p:canvas.putpixel((x,y),tuple(pal[p*3:p*3+3])+ (255,))
            blob+=rgba555(canvas)
        sprites.append('{'+','.join(map(str,[offset,count]))+'}')
    (OUT/'opening_stage.bin').write_bytes(blob)
    (OUT/'opening_stage.s').write_text(f'/* SHA256 {hashlib.sha256(blob).hexdigest()} */\n'+'.section .rodata\n.balign 4\n.global omni_opening_stage_blob\nomni_opening_stage_blob:\n.incbin "build/pallet/opening_stage.bin"\n')
    (OUT/'opening_stage.h').write_text('''#ifndef OMNI_OPENING_STAGE_H
#define OMNI_OPENING_STAGE_H
#include <stdint.h>
typedef struct {uint16_t w,h;uint32_t art,mask,collision;} OmniStage;
typedef struct {uint32_t offset;uint8_t frames;} OmniStageSprite;
extern const OmniStage omni_stages[];
extern const OmniStageSprite omni_stage_sprites[];
extern const unsigned char omni_opening_stage_blob[];
#endif
''')
    (OUT/'opening_stage.c').write_text('#include "opening_stage.h"\nconst OmniStage omni_stages[]={'+','.join(stages)+'};\nconst OmniStageSprite omni_stage_sprites[]={'+','.join(sprites)+'};\n')
    (OUT/'opening-collision.json').write_text(json.dumps(grids,indent=2)+'\n')
    MANIFEST.write_text(json.dumps({'repository':'https://github.com/pret/pokefirered','commit':REV,'scope':'Native room tiles/layouts and sprites plus separately credited generated cinematic illustrations; no source event scripts; illustrations do not define world geography','files':list(records.values()),'illustrations':illustrations},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Opening stages: {len(stages)}, sprites: {len(sprites)}, bytes: {len(blob)}')
if __name__=='__main__':main()
