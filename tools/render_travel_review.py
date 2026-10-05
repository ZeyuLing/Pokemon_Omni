"""Render actual-ROM captures from tests/travel-rom.cjs for visual inspection."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/pallet'
samples=json.loads((OUT/'travel-walk-review.json').read_text())
def frame(name):return Image.frombytes('RGBA',(240,160),(OUT/(name+'.rgba')).read_bytes()).convert('RGB')
for mode,label in ((0,'following'),(1,'riding')):
    shots=[frame(s['file']).resize((720,480),Image.Resampling.NEAREST) for s in samples if s['mounted']==mode]
    shots[0].save(OUT/f'travel-{label}-actual.gif',save_all=True,append_images=shots[1:],duration=65,loop=0)
review=Image.new('RGB',(960,640))
for direction in range(4):
    s=next(s for s in reversed(samples) if s['mounted'] and s['direction']==direction)
    review.paste(frame(s['file']).resize((480,320),Image.Resampling.NEAREST),((direction%2)*480,(direction//2)*320))
review.save(OUT/'travel-rider-directions.png')
for name in ['travel-follow-pikachu','travel-riding-and-following','travel-indoor','travel-lapras-land-rejected']:
    frame(name).resize((720,480),Image.Resampling.NEAREST).save(OUT/(name+'.png'))
mounts=json.loads((OUT/'mount-species-review.json').read_text())['mountResults']
review=Image.new('RGB',(240*len(mounts),4*184))
draw=ImageDraw.Draw(review)
for col,mount in enumerate(mounts):
    species=mount['species']
    rows=[s for s in samples if s['mounted'] and s['mountSpecies']==species]
    shots=[frame(s['file']).resize((720,480),Image.Resampling.NEAREST) for s in rows]
    shots[0].save(OUT/f'mount-{species}-actual.gif',save_all=True,append_images=shots[1:],duration=100,loop=0)
    for direction in range(4):
        s=next(s for s in rows if s['direction']==direction)
        draw.text((col*240+8,direction*184+5),f'Species {species} / direction {direction}',fill='white')
        review.paste(frame(s['file']),(col*240,direction*184+24))
review.save(OUT/'mount-multispecies-directions.png')
print('Rendered current actual-ROM frames: three mounts, four directions each, and slowed gait GIFs')
