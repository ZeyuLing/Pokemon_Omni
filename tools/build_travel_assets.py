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
    if old.exists():
        expected=next((r for r in json.loads(old.read_text("utf-8"))["files"] if r.get("path")==path),None)
        if expected:assert digest==expected["sha256"]
    records[path]=dict(path=path,url=url,sha256=digest)
    return data
OUT=ROOT/'build/pallet'
SPECIES=[1,4,7,25,16,19,109,13,111]
NAMES=["bulbasaur","charmander","squirtle","pikachu","pidgey","rattata","koffing","weedle","rhyhorn"]
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    blob=bytearray();rows=[];audit=[]
    for species,name in zip(SPECIES,NAMES):
        data=fetch(name,'overworld.png');pal=fetch(name,'overworld_normal.pal').decode().splitlines()[3:19]
        palette=[tuple(map(int,line.split())) for line in pal]
        im=Image.open(io.BytesIO(data));assert im.size==(192,32) and im.mode=='P'
        frames=[];w=h=32;count=2
        for face,indices in enumerate(((0,1),(2,3),(4,5),(4,5))):
            for i in indices:
                f=Image.new('RGBA',(32,32))
                for y in range(32):
                    for x in range(32):
                        c=im.getpixel((i*32+x,y))
                        if c:f.putpixel((31-x if face==3 else x,y),(*palette[c],255))
                frames.append(f)
        credit='Game Freak; HGSS-style follower imported from rh-hideout/pokeemerald-expansion (see repository CREDITS.md)'
        for face in range(4):
            assert frames[face*2].tobytes()!=frames[face*2+1].tobytes(), (name,face,'stationary gait')
        boxes=[f.getbbox() for f in frames];box=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))
        frames=[f.crop(box) for f in frames];cw,ch=frames[0].size
        assert cw<=64 and ch<=64
        offset=len(blob)
        for f in frames:
            blob+=b''.join(struct.pack('<H',0x8000 if p[3]<128 else (p[0]>>3)|((p[1]>>3)<<5)|((p[2]>>3)<<10)) for p in f.get_flattened_data())
        while len(blob)%4:blob.append(0)
        # One common foot origin. Animation bob remains in the source frame.
        rows.append('{'+','.join(map(str,[species,offset,cw,ch,count,w//2-box[0],ch]))+'}')
        proof=Image.new('RGBA',(cw*count,ch*4))
        for i,f in enumerate(frames):proof.paste(f,(i%count*cw,i//count*ch))
        proof.resize((proof.width*4,proof.height*4),Image.Resampling.NEAREST).save(OUT/f'travel-{species}-proof.png')
        audit.append(dict(species=species,frames=count*4,original_cell=[w,h],common_crop=box,credit=credit))
    (OUT/'travel.bin').write_bytes(blob)
    (OUT/'travel.s').write_text('.section .rodata\n.balign 4\n.global omni_travel_blob\nomni_travel_blob:\n.incbin "build/pallet/travel.bin"\n')
    (OUT/'travel_art.h').write_text('#include <stdint.h>\ntypedef struct {uint16_t species;uint32_t offset;uint8_t w,h,frames;int8_t origin_x,origin_y;} OmniTravelArt;\nextern const OmniTravelArt omni_travel_art[9];\nextern const unsigned char omni_travel_blob[];\n')
    (OUT/'travel_art.c').write_text('#include "travel_art.h"\nconst OmniTravelArt omni_travel_art[9]={'+','.join(rows)+'};\n')
    (ROOT/'assets/source/travel-sprites.json').write_text(json.dumps(dict(repository='https://github.com/rh-hideout/pokeemerald-expansion',commit=REV,scope='Native cardinal walk animation; no resampling; local-only decoded artwork',sprites=audit,files=list(records.values())),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(rows)} source-native travel sheets, {len(blob)} bytes')
if __name__=='__main__':main()
