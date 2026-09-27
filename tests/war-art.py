"""Check packed GBA frames reconstruct source pixels at their original positions."""
import json,sys,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from war_sources import pokemon_frames
from war_humans import native_frames
from build_opening_stages import get
from PIL import Image,ImageDraw
blob=(ROOT/'build/pallet/war.bin').read_bytes()
layout=json.loads((ROOT/'build/pallet/war-art-layout.json').read_text())
count=0
lance_runtime_frames=[]
specs=json.loads((ROOT/'content/opening/battlefield.json').read_text('utf8'))['sprites']
proof=Image.new('RGB',(448,384),(34,38,44));native_count=0
labels=ImageDraw.Draw(proof)
for i,label in enumerate(['Front','Back','Left','Right']):labels.text((128+i*80,5),label,fill='white')
for i,label in enumerate(['Lance / FR','Drake / E','Flint / Pt','Caitlin / Pt']):labels.text((5,48+i*90),label,fill='white')
for index,sprite in enumerate(layout):
    if sprite['pmd']:
        source=pokemon_frames(sprite['pmd']);assert len(source)==len(sprite['frames'])==48
    elif specs[index].get('native_overworld'):
        source=native_frames(specs[index],get);assert len(source)==len(sprite['frames'])==4
        assert all(f.height==32 and f.getbbox()[3]==31 for f in source)
        assert len({f.getbbox()[3]-f.getbbox()[1] for f in source})==1,'Direction-dependent human height'
    else:continue
    for expected,frame in zip(source,sprite['frames']):
        w,h=expected.size;actual=[0x8000]*(w*h)
        # Independent decoder for the cartridge's flag/match stream.
        decoded=bytearray();at=frame['offset'];size=(frame['width']*frame['height']+1)//2
        while len(decoded)<size:
            flags=blob[at];at+=1
            for bit in range(7,-1,-1):
                if len(decoded)>=size:break
                if flags&(1<<bit):
                    code=blob[at]*256+blob[at+1];at+=2;distance=(code&4095)+1
                    assert distance<=len(decoded)
                    for _ in range((code>>12)+3):decoded.append(decoded[-distance])
                else:decoded.append(blob[at]);at+=1
        assert len(decoded)==size
        for y in range(frame['height']):
            for x in range(frame['width']):
                i=y*frame['width']+x
                value=decoded[i//2]>>((i&1)*4)&15
                actual[(y+frame['y'])*w+x+frame['x']]=sprite['palette'][value]
        reference=[0x8000 if a<128 else (r>>3)|((g>>3)<<5)|((b>>3)<<10) for r,g,b,a in expected.getdata()]
        assert actual==reference,(sprite['pmd'],count,'Source pixels or frame origin changed')
        if index==12:lance_runtime_frames.append(struct.pack('<'+'H'*len(actual),*actual))
        if not sprite['pmd']:
            image=Image.new('RGBA',(w,h));image.putdata([(0,0,0,0) if v==0x8000 else ((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31,255) for v in actual]);image=image.resize((w*2,h*2),Image.Resampling.NEAREST)
            x=128+(native_count%4)*80+(64-image.width)//2;y=24+(native_count//4)*90
            labels.line((x-8,y+62,x+72,y+62),fill=(75,79,87))
            proof.paste(image,(x,y),image);native_count+=1
        count+=1
proof.save(ROOT/'build/pallet/native-commanders-proof.png')
assert native_count==16
opening=json.loads((ROOT/'content/opening/prologue.json').read_text('utf8'))
table=(ROOT/'build/pallet/opening_stage.c').read_text()
rows=re.findall(r'\{(\d+),(\d+)\}',table.split('const OmniStageSprite omni_stage_sprites[]=')[1])
offset,frames=map(int,rows[opening['sprites'].index('lance')])
meeting_blob=(ROOT/'build/pallet/opening_stage.bin').read_bytes()
assert frames==3
for direction in range(3):
    assert lance_runtime_frames[direction]==meeting_blob[offset+direction*1024:offset+(direction+1)*1024], 'Lance differs between battlefield and meeting room'
print(f'PASS: {count} packed frames preserve source pixels, dimensions and animation origins')
