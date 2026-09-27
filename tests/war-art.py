"""Check packed GBA frames reconstruct source pixels at their original positions."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from war_sources import pokemon_frames
blob=(ROOT/'build/pallet/war.bin').read_bytes()
layout=json.loads((ROOT/'build/pallet/war-art-layout.json').read_text())
count=0
for sprite in layout:
    if not sprite['pmd']:continue
    source=pokemon_frames(sprite['pmd'])
    assert len(source)==len(sprite['frames'])==24
    for expected,frame in zip(source,sprite['frames']):
        w,h=expected.size;actual=[0x8000]*(w*h)
        for y in range(frame['height']):
            for x in range(frame['width']):
                i=y*frame['width']+x
                value=blob[frame['offset']+i//2]>>((i&1)*4)&15
                actual[(y+frame['y'])*w+x+frame['x']]=sprite['palette'][value]
        reference=[0x8000 if a<128 else (r>>3)|((g>>3)<<5)|((b>>3)<<10) for r,g,b,a in expected.getdata()]
        assert actual==reference,(sprite['pmd'],count,'Source pixels or frame origin changed')
        count+=1
print(f'PASS: {count} packed frames preserve source pixels, dimensions and animation origins')
