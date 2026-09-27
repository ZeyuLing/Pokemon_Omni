"""Native source tiles and object-event frames -> authored war stage.
No rendered illustration, screenshot, generated creature art or game ROM here.
"""
import io,json,hashlib
from PIL import Image
from build_opening_stages import ROOT,OUT,get,render,rgba555,records
import war_sources
from war_packing import pack

def compile_war():
    assert json.loads((ROOT/'content/opening/prologue.json').read_text('utf8'))['stages'][0]['kind']=='battlefield', 'GBA war stage must occupy slot zero'
    source_manifest=ROOT/'assets/source/battlefield.json'
    pinned={f['path']:f for f in json.loads(source_manifest.read_text('utf8'))['files']} if source_manifest.exists() else {}
    data=json.loads((ROOT/'content/opening/battlefield.json').read_text('utf8'))
    source=war_sources.volcano_tiles()
    tiles={k:source[index] for k,index in data['tiles'].items()}
    # Source pixels remain intact in cache. This is the scene's reproducible
    # palette lighting: dark rock against emissive lava, not a screen tint.
    if data.get('rock_lighting'):
        scales=data['rock_lighting']
        for key,tile in tiles.items():
            if key=='~':continue
            lit=tile.copy()
            for y in range(16):
                for x in range(16):
                    rgb=tile.getpixel((x,y))
                    if rgb[0]>180 and rgb[1]<80:continue
                    lit.putpixel((x,y),tuple(c*s//100 for c,s in zip(rgb,scales)))
            tiles[key]=lit
    w,h=data['size'];bg=Image.new('RGB',(w*16,h*16));terrain=[]
    for y,row in enumerate(data['map']):
        assert len(row)==w
        for x,c in enumerate(row):
            bg.paste(tiles[c],(x*16,y*16));terrain.append(2 if c=='~' else 1 if c in '#^v<>' else 0)
    blob=bytearray();sprites=[];art_layout=[]
    for s in data['sprites']:
        if s.get('native_overworld'):
            from war_humans import native_frames
            frames=native_frames(s,get)
        elif 'pmd' in s:
            frames=war_sources.pokemon_frames(s['pmd'])
        else:
            raw=war_sources.get(s['path']) if s.get('source')=='emerald' else get(s['path'])
            im=Image.open(io.BytesIO(raw));pal=im.getpalette();fw,fh=s['frame'];frames=[]
            assert im.width%fw==0 and im.height==fh
            for frame in range(im.width//fw):
                canvas=Image.new('RGBA',(fw,fh))
                for y in range(fh):
                    for x in range(fw):
                        c=im.getpixel((frame*fw+x,y))
                        if c:canvas.putpixel((x,y),(*s.get('palette',{}).get(str(c),pal[c*3:c*3+3]),255))
                frames.append(canvas)
        fw,fh=frames[0].size;offset=len(blob)
        palette=[0x8000]
        frame_map=[];unique_frames=[];frame_layout=[]
        for frame in frames:
            box=frame.getbbox() if 'pmd' in s else (0,0,fw,fh)
            cropped=frame.crop(box);cw,ch=cropped.size
            indices=[]
            for r,g,b,a in cropped.getdata():
                c=0x8000 if a<128 else (r>>3)|((g>>3)<<5)|((b>>3)<<10)
                if c not in palette:palette.append(c)
                indices.append(palette.index(c))
            assert len(palette)<=16,(s['name'],len(palette))
            if len(indices)%2:indices.append(0)
            assert len(indices)//2<=4096, 'Frame exceeds GBA scratch space'
            packed=pack(bytes(indices[i]|(indices[i+1]<<4) for i in range(0,len(indices),2)))
            if packed not in unique_frames:unique_frames.append(packed)
            position=sum(len(p) for p in unique_frames[:unique_frames.index(packed)])
            frame_map.append('{'+','.join(map(str,[position,cw,ch,box[0],box[1]]))+'}')
            frame_layout.append(dict(offset=offset+position,width=cw,height=ch,x=box[0],y=box[1]))
        for packed in unique_frames:blob.extend(packed)
        frame_map += ['{0,0,0,0,0}']*(48-len(frame_map))
        palette += [0x8000]*(16-len(palette))
        art_layout.append(dict(pmd=s.get('pmd'),width=fw,height=fh,palette=palette,frames=frame_layout))
        sprites.append('{'+','.join(map(str,[offset,fw,fh,len(frames),int(s['human']),int('pmd' in s)]))+',{'+','.join(map(str,palette))+'},{'+','.join(frame_map)+'}}')
    # Enforce traversable routes across the entire foot rectangle, not only endpoints.
    actors=data['actors'];count=len(actors)
    cache_offsets=[];cache_bytes=0
    for actor in actors:
        cache_offsets.append(cache_bytes)
        cache_bytes+=max((f['width']*f['height']+1)//2 for f in art_layout[actor['sprite']]['frames'])
        cache_bytes=(cache_bytes+3)&~3
    assert 0<count<=255
    assert len(data['factions'])==4
    rosters=[{data['sprites'][a['sprite']].get('pmd') for a in actors if a['team']==team and not data['sprites'][a['sprite']]['human']} for team in range(4)]
    assert all(rosters) and all(not (rosters[a]&rosters[b]) for a in range(4) for b in range(a+1,4)), 'Regional battle rosters must be visually distinct'
    species=[data['sprites'][a['sprite']]['pmd'] for a in actors if not data['sprites'][a['sprite']]['human']]
    assert len(species)==len(set(species))==24, 'Each Pokemon actor must have its own species'
    for team in range(4):
        assert {actors[a['target']]['team'] for a in actors if a['team']==team and a['attack']}==set(range(4))-{team}, 'Each region must fight all three opponents'
    assert sum(a.get('stop')==1600 for a in actors)==20
    assert sum(a['attack']>0 and a.get('stop',65535)>1600 for a in actors)==8
    for a in actors:
        assert 0<=a['target']<count and a['team'] in (0,1,2,3)
        assert 0<=a['attack']<=7 and a['layer'] in (0,2) and 0<=a['sprite']<len(sprites)
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
    rows=['{'+','.join(map(str,[*a['at'],*a['to'],a['start'],a['duration'],a['phase'],a['sprite'],a['team'],a['layer'],a['target'],a['attack'],a['role'],a.get('stop',65535)]))+'}' for a in actors]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'war.bin').write_bytes(blob)
    (OUT/'war-art-layout.json').write_text(json.dumps(art_layout))
    (OUT/'war.s').write_text(f'/* {hashlib.sha256(blob).hexdigest()} */\n.section .rodata\n.balign 4\n.global omni_war_art\nomni_war_art:\n.incbin "build/pallet/war.bin"\n')
    (OUT/'war_data.h').write_text('''#ifndef OMNI_WAR_DATA_H
#define OMNI_WAR_DATA_H
#include "omni/battlefield.h"
typedef struct {uint32_t offset;uint8_t w,h,x,y;} OmniWarFrame;
typedef struct {uint32_t offset;uint8_t w,h,frames,human,pmd;uint16_t palette[16];OmniWarFrame frame_map[48];} OmniWarSprite;
extern const unsigned char omni_war_art[];
extern const OmniWarActor omni_war_actors[];
extern const OmniWarSprite omni_war_sprites[];
extern const unsigned char omni_war_terrain[];
extern const int16_t omni_war_standards[4][2];
extern const uint32_t omni_war_cache_offsets[];
'''+f'#define OMNI_WAR_COUNT {count}\n#define OMNI_WAR_WIDTH {w*16}\n#define OMNI_WAR_HEIGHT {h*16}\n#define OMNI_WAR_CACHE_BYTES {cache_bytes}\n#endif\n')
    standards=','.join('{'+','.join(map(str,p))+'}' for p in data['staging']['standards'])
    (OUT/'war_data.c').write_text('#include "war_data.h"\nconst OmniWarActor omni_war_actors[]={'+','.join(rows)+'};\nconst OmniWarSprite omni_war_sprites[]={'+','.join(sprites)+'};\nconst unsigned char omni_war_terrain[]={'+','.join(map(str,terrain))+'};\nconst int16_t omni_war_standards[4][2]={'+standards+'};\n')
    (OUT/'war-terrain.json').write_text(json.dumps({'width':w,'height':h,'cells':terrain,'actors':actors}))
    with (OUT/'war_data.c').open('a') as target:target.write('const uint32_t omni_war_cache_offsets[]={'+','.join(map(str,cache_offsets))+'};\n')
    fire_red_paths={s['path'] for s in data['sprites'] if 'path' in s and s.get('source','firered')=='firered'}
    combined={**{path:records[path] for path in sorted(fire_red_paths)},**war_sources.records}
    for path,record in combined.items():
        assert path not in pinned or pinned[path]['sha256']==record['sha256'], 'Battlefield source changed: '+path
    source_manifest.write_text(json.dumps({'scope':'Omni Mt Chimney front: Emerald volcanic tiles, PMD native animation frames with credits, FireRed human bases with runtime uniforms, native FireRed/Emerald/Platinum commander sheets. No global geography or canonical war claims.','files':list(combined.values()),'actors':count,'sprite_bytes':len(blob),'commander_sources':[s for s in data['sprites'] if s.get('native_overworld')]},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return bg,Image.new('L',bg.size),[int(c!=0) for c in terrain]
