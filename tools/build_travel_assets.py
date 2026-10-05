"""Source-native HGSS-style walking frames; shared origin, no resampling."""
import io,json,struct,hashlib
from PIL import Image
from pathlib import Path
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
REV="dfb0f84374230f4d462191601179b742f9f077df"
records={}
def fetch(name,file):
    path=f"graphics/pokemon/{name}/{file}"
    url=f"https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/{REV}/{path}"
    p=ROOT/".cache/travel-rhh"/(name+"-"+file)
    if not p.exists():
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(urllib.request.urlopen(url,timeout=30).read())
    data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
    old=ROOT/"assets/source/travel-sprites.json"
    for manifest in (old,ROOT/'assets/source/travel-roster.json'):
        if manifest.exists():
            expected=next((r for r in json.loads(manifest.read_text('utf8'))['files'] if r.get('path')==path),None)
            if expected:assert digest==expected['sha256']
    records[path]=dict(path=path,url=url,sha256=digest)
    return data
OUT=ROOT/'build/pallet'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    blob=bytearray();rows=[];audit=[]
    roster=json.loads((ROOT/'assets/source/travel-roster.json').read_text('utf8'))['species']
    assert all(r['status']=='native_source_prepared' for r in roster), 'Missing travel source; do not silently remove eligible mounts'
    eligible={r['species'] for r in json.loads((ROOT/'content/travel/generated/profiles.json').read_text('utf8'))['profiles'] if r['eligible']}
    assert eligible <= {r['species'] for r in roster}, 'Qualified species missing from asset roster'
    species_list=[r for r in roster if r['status']=='native_source_prepared']
    for record in species_list:
        species,name=record['species'],record['name']
        data=fetch(name,'overworld.png');pal=fetch(name,'overworld_normal.pal').decode().splitlines()[3:19]
        palette=[tuple(map(int,line.split())) for line in pal]
        im=Image.open(io.BytesIO(data));assert im.width in (im.height*6,im.height*8) and im.mode=='P'
        frames=[];w=h=im.height;count=2
        independent_right=im.width==w*8
        for face,indices in enumerate(((0,1),(2,3),(4,5),(6,7) if independent_right else (4,5))):
            for i in indices:
                f=Image.new('RGBA',(w,h))
                for y in range(h):
                    for x in range(h):
                        c=im.getpixel((i*w+x,y))
                        if c:f.putpixel((w-1-x if face==3 and not independent_right else x,y),(*palette[c],255))
                frames.append(f)
        credit='Game Freak; HGSS-style follower imported from rh-hideout/pokeemerald-expansion (see repository CREDITS.md)'
        for face in range(4):
            assert frames[face*2].getbbox() and frames[face*2+1].getbbox(), (name,face,'empty pose')
            if species in eligible:
                assert frames[face*2].tobytes()!=frames[face*2+1].tobytes(), (name,face,'eligible mount lacks native moving poses')
        boxes=[f.getbbox() for f in frames];box=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))
        if not independent_right:
            left=min(box[0],w-box[2]);box=(left,box[1],w-left,box[3])
        frames=[f.crop(box) for f in frames];cw,ch=frames[0].size
        assert cw<=64 and ch<=64
        offset=len(blob)
        native_palette=[0x8000]+[(r>>3)|((g>>3)<<5)|((b>>3)<<10) for r,g,b in palette[1:]]
        blob+=struct.pack('<16H',*native_palette)
        positions=len(blob);blob+=bytes(32);pose_offsets=[]
        for pose,f in enumerate(frames):
            if not independent_right and pose>=6:
                assert frames[pose-2].transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()==f.tobytes()
                pose_offsets.append(pose_offsets[pose-2]);continue
            pose_offsets.append(len(blob))
            values=[0x8000 if p[3]<128 else (p[0]>>3)|((p[1]>>3)<<5)|((p[2]>>3)<<10) for p in f.get_flattened_data()]
            indices=[native_palette.index(v) for v in values]
            encoded=bytearray();i=0
            while i<len(indices):
                run=1
                while run<16 and i+run<len(indices) and indices[i+run]==indices[i]:run+=1
                encoded.append(((run-1)<<4)|indices[i]);i+=run
            decoded=[native_palette[token&15] for token in encoded for _ in range((token>>4)+1)]
            assert decoded==values, (species,'lossless round trip')
            blob+=encoded
        struct.pack_into('<8I',blob,positions,*pose_offsets)
        while len(blob)%4:blob.append(0)
        # One common foot origin. Animation bob remains in the source frame.
        icon_offset=len(blob)
        icon=Image.open(io.BytesIO(fetch(name,'icon.png')))
        assert icon.size==(32,64) and icon.mode=='P'
        colors=icon.getpalette();icon_palette=[0x8000]+[(colors[i*3]>>3)|((colors[i*3+1]>>3)<<5)|((colors[i*3+2]>>3)<<10) for i in range(1,16)]
        blob+=struct.pack('<16H',*icon_palette)
        icon_indices=list(icon.get_flattened_data())[:32*32];assert max(icon_indices)<16
        encoded=bytearray();i=0
        while i<len(icon_indices):
            run=1
            while run<16 and i+run<len(icon_indices) and icon_indices[i+run]==icon_indices[i]:run+=1
            encoded.append(((run-1)<<4)|icon_indices[i]);i+=run
        assert [token&15 for token in encoded for _ in range((token>>4)+1)]==icon_indices
        blob+=encoded
        while len(blob)%4:blob.append(0)
        rows.append('{'+','.join(map(str,[species,offset,icon_offset,cw,ch,count,w//2-box[0],ch,int(not independent_right)]))+'}')
        proof=Image.new('RGBA',(cw*count,ch*4))
        for i,f in enumerate(frames):proof.paste(f,(i%count*cw,i//count*ch))
        proof.resize((proof.width*4,proof.height*4),Image.Resampling.NEAREST).save(OUT/f'travel-{species}-proof.png')
        audit.append(dict(species=species,frames=count*4,original_cell=[w,h],common_crop=box,credit=credit,distinct_poses=[frames[i*2].tobytes()!=frames[i*2+1].tobytes() for i in range(4)],visual_review='pending',rider_pose='native_torso_prototype'))
    (OUT/'travel.bin').write_bytes(blob)
    (OUT/'travel.s').write_text('/* '+hashlib.sha256(blob).hexdigest()+' */\n.section .rodata\n.balign 4\n.global omni_travel_blob\nomni_travel_blob:\n.incbin "build/pallet/travel.bin"\n')
    (OUT/'travel_art.h').write_text('#include <stdint.h>\ntypedef struct {uint16_t species;uint32_t offset,icon;uint8_t w,h,frames;int8_t origin_x,origin_y;uint8_t mirror_right;} OmniTravelArt;\nenum { OMNI_TRAVEL_ART_COUNT = '+str(len(rows))+' };\nextern const OmniTravelArt omni_travel_art[OMNI_TRAVEL_ART_COUNT];\nextern const unsigned char omni_travel_blob[];\n')
    (OUT/'travel_art.c').write_text('#include "travel_art.h"\nconst OmniTravelArt omni_travel_art[OMNI_TRAVEL_ART_COUNT]={'+','.join(rows)+'};\n')
    (ROOT/'assets/source/travel-sprites.json').write_text(json.dumps(dict(repository='https://github.com/rh-hideout/pokeemerald-expansion',commit=REV,scope='Native cardinal walk animation; RGB555 palette + lossless run encoding; no resampling; local-only decoded artwork',sprites=audit,files=list(records.values())),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(rows)} source-native travel sheets, {len(blob)} bytes')
if __name__=='__main__':main()
