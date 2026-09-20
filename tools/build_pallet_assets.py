"""Pinned FireRed reference maps -> GBA presentation, no upstream game scripts.
The source manifest is committed; images, imported binaries and compiled maps stay local.
"""
import hashlib, io, json, struct, urllib.request
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
REV='c75f352304d529f6ba92d4f74b9cf8b5c3810788'
BASE=f'https://raw.githubusercontent.com/pret/pokefirered/{REV}/'
CACHE=ROOT/'.cache/pallet-source'
OUT=ROOT/'build/pallet'
MANIFEST=ROOT/'assets/source/pallet-town.json'
records={}
old={r['path']:r for r in json.loads(MANIFEST.read_text())['files']} if MANIFEST.exists() else {}

def get(path):
    cache=CACHE/path
    if cache.exists(): data=cache.read_bytes()
    else:
        clone=ROOT/'.cache/pokefirered'/path
        data=clone.read_bytes() if clone.exists() else urllib.request.urlopen(BASE+path,timeout=30).read()
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(data)
    sha=hashlib.sha256(data).hexdigest()
    if path in old and old[path]['sha256']!=sha:raise ValueError('Source hash changed: '+path)
    records[path]={'path':path,'url':BASE+path,'sha256':sha,'bytes':len(data)}
    return data

def rgb555(rgb):
    r,g,b=rgb[:3];return (r>>3)|((g>>3)<<5)|((b>>3)<<10)

def packed(im):return b''.join(struct.pack('<H',rgb555(p)) for p in im.convert('RGB').get_flattened_data())
def cs(s):return json.dumps(s,ensure_ascii=False)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    scene=json.loads((ROOT/'content/pallet-town/scene.json').read_text(encoding='utf-8'))
    layouts={l.get('id'):l for l in json.loads(get('data/layouts/layouts.json'))['layouts']}
    names={'gTileset_General':'primary/general','gTileset_Building':'primary/building','gTileset_PalletTown':'secondary/pallet_town','gTileset_GenericBuilding1':'secondary/generic_building_1','gTileset_GenericBuilding2':'secondary/generic_building_2','gTileset_Lab':'secondary/lab','gTileset_ViridianCity':'secondary/viridian_city','gTileset_PokemonCenter':'secondary/pokemon_center','gTileset_Mart':'secondary/mart'}
    blob=bytearray();map_rows=[];actor_rows=[];sign_rows=[];warp_rows=[];audit=[]
    sprites=['red_normal','mom','prof_oak','blue','woman_1','fat_man','scientist','daisy','item_ball','pikachu','nurse','rocket_m','rocket_f']
    maps={m['source']:m for m in scene['maps']}
    source_maps={name:json.loads(get(f'data/maps/{name}/map.json')) for name in maps}
    source_ids={m['id']:name for name,m in source_maps.items()}
    for source,m in maps.items():
        meta=source_maps[source];layout=layouts[meta['layout']];w,h=layout['width'],layout['height']
        dirs=[f'data/tilesets/{names[layout[k]]}' for k in ['primary_tileset','secondary_tileset']]
        tiles=[];metas=[];attrs=[]
        for d in dirs:
            im=Image.open(io.BytesIO(get(d+'/tiles.png')))
            tiles.append([im.crop((x,y,x+8,y+8)) for y in range(0,im.height,8) for x in range(0,im.width,8)])
            metas.append(list(struct.iter_unpack('<8H',get(d+'/metatiles.bin'))))
            attrs.append([a[0] for a in struct.iter_unpack('<I',get(d+'/metatile_attributes.bin'))])
        palettes=[]
        for i in range(13):
            pal=get(dirs[0 if i<7 else 1]+f'/palettes/{i:02d}.pal').decode().splitlines()[3:19]
            palettes.append([tuple(map(int,line.split())) for line in pal])
        blocks=[a[0] for a in struct.iter_unpack('<H',get(layout['blockdata_filepath']))]
        assert len(blocks)==w*h
        bg=Image.new('RGB',(w*16,h*16),palettes[0][0]);mask=bytearray(w*h*256);collision=[];grass=[]
        for cell,block in enumerate(blocks):
            mid=block&1023;bank=mid>=640;idx=mid-640 if bank else mid
            attr=attrs[bank][idx];layer=(attr>>29)&3;behavior=attr&511
            collision.append(1 if block&0xc00 or behavior in (0x10,0x11,0x12,0x13,0x14,0x15) else 0)
            grass.append(int(behavior==2))
            for part,tile in enumerate(metas[bank][idx]):
                tileid=tile&1023;tb=tileid>=640;ti=tileid-640 if tb else tileid
                pixels=tiles[tb][ti];palette=palettes[tile>>12]
                ox=(cell%w)*16+(part%2)*8;oy=(cell//w)*16+((part%4)//2)*8
                for y in range(8):
                    for x in range(8):
                        p=pixels.getpixel((7-x if tile&1024 else x,7-y if tile&2048 else y))
                        if part>=4 and not p:continue
                        bg.putpixel((ox+x,oy+y),palette[p])
                        if part>=4 and p and layer!=1:mask[(oy+y)*(w*16)+ox+x]=1
        art_offset=len(blob);blob+=packed(bg)
        mask_offset=len(blob);blob+=mask
        for warp in meta['warp_events']:
            if warp['dest_map'] not in source_ids:collision[warp['y']*w+warp['x']]=1
        collision_offset=len(blob);blob+=bytes(collision)
        grass_offset=len(blob);blob+=bytes(grass)
        while len(blob)%4:blob.append(0)
        actor_start=len(actor_rows)
        for a in m['actors']:actor_rows.append('{'+','.join(map(str,[m['id'],a['x'],a['y'],sprites.index(a['sprite']),a.get('person',0),a.get('starter',0),a['direction']]))+'}')
        sign_start=len(sign_rows)
        for s in m['signs']:sign_rows.append('{'+','.join([str(m['id']),str(s['x']),str(s['y']),str(s.get('person',0)),cs(s['text'])])+'}')
        warp_start=len(warp_rows)
        for warp in meta['warp_events']:
            if warp['dest_map'] not in source_ids:continue
            destname=source_ids[warp['dest_map']];dest=source_maps[destname]['warp_events'][int(warp['dest_warp_id'])]
            warp_rows.append('{'+','.join(map(str,[m['id'],warp['x'],warp['y'],maps[destname]['id'],dest['x'],dest['y']]))+'}')
        map_rows.append('{'+','.join([str(m['id']),str(w),str(h),cs(m['name']),str(art_offset),str(mask_offset),str(collision_offset),str(grass_offset),str(actor_start),str(len(m['actors'])),str(sign_start),str(len(m['signs'])),str(warp_start),str(len(warp_rows)-warp_start)])+'}')
        bg.save(OUT/(source+'.png'))
        audit.append({'id':m['id'],'key':m['key'],'source':source,'width':w,'height':h,'collision':collision,'grass':grass,'warps':[warp for warp in meta['warp_events'] if warp['dest_map'] in source_ids],'actors':m['actors'],'signs':m['signs']})
    sprite_rows=[]
    for sprite in sprites:
        path='graphics/object_events/pics/'+('misc/item_ball.png' if sprite=='item_ball' else 'pokemon/pikachu.png' if sprite=='pikachu' else f'people/{sprite}.png')
        im=Image.open(io.BytesIO(get(path)));palette=im.getpalette();height=im.height;frames=im.width//16;offset=len(blob)
        for frame in range(frames):
            for y in range(32):
                for x in range(16):
                    p=im.getpixel((frame*16+x,y)) if y<height else 0
                    blob+=struct.pack('<H',rgb555(palette[p*3:p*3+3]) if p else 0x8000)
        sprite_rows.append('{'+','.join(map(str,[offset,frames]))+'}')
    battle_offsets=[]
    for species in ('bulbasaur','charmander','squirtle','pikachu','pidgey','rattata','koffing'):
        for side in ('front','back'):
            im=Image.open(io.BytesIO(get(f'graphics/pokemon/{species}/{side}.png')))
            palette=im.getpalette();battle_offsets.append(len(blob))
            for y in range(64):
                for x in range(64):
                    p=im.getpixel((x,y))
                    blob+=struct.pack('<H',rgb555(palette[p*3:p*3+3]) if p else 0x8000)
    (OUT/'world.bin').write_bytes(blob)
    (OUT/'world_blobs.s').write_text(f'/* {hashlib.sha256(blob).hexdigest()} */\n.section .rodata\n.balign 4\n.global pallet_world_blob\npallet_world_blob:\n.incbin "build/pallet/world.bin"\n')
    (OUT/'world_data.h').write_text('''#ifndef OMNI_PALLET_DATA_H
#define OMNI_PALLET_DATA_H
#include <stdint.h>
typedef struct {uint8_t id,w,h;const char *name;uint32_t art,mask,collision,grass;uint16_t actors,actor_count,signs,sign_count,warps,warp_count;} PalletMap;
typedef struct {uint8_t map,x,y,sprite,person,starter,direction;} PalletActor;
typedef struct {uint8_t map,x,y,person;const char *text;} PalletSign;
typedef struct {uint8_t map,x,y,dest_map,dest_x,dest_y;} PalletWarp;
typedef struct {uint32_t offset;uint8_t frames;} PalletSprite;
extern const PalletMap pallet_maps[9];
extern const PalletActor pallet_actors[];
extern const PalletSign pallet_signs[];
extern const PalletWarp pallet_warps[];
extern const PalletSprite pallet_sprites[13];
extern const uint32_t pallet_battle_sprites[14];
extern const unsigned char pallet_world_blob[];
#endif
''')
    code='#include "world_data.h"\n'
    for name,rows in [('PalletMap pallet_maps',map_rows),('PalletActor pallet_actors',actor_rows),('PalletSign pallet_signs',sign_rows),('PalletWarp pallet_warps',warp_rows),('PalletSprite pallet_sprites',sprite_rows)]:code+='const '+name+'[]={\n'+',\n'.join(rows)+'\n};\n'
    code+='const uint32_t pallet_battle_sprites[14]={'+','.join(map(str,battle_offsets))+'};\n'
    (OUT/'world_data.c').write_text(code,encoding='utf-8')
    (OUT/'scene-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    MANIFEST.write_text(json.dumps({'repository':'https://github.com/pret/pokefirered','commit':REV,'scope':'Map layouts, metatiles and character artwork only; no upstream engine or story scripts executed','files':sorted(records.values(),key=lambda r:r['path'])},indent=2)+'\n')
    print(f'Pallet assets: {len(maps)} maps, {len(sprites)} sprites, {len(blob)} bytes; {len(records)} pinned sources')

if __name__=='__main__':main()
