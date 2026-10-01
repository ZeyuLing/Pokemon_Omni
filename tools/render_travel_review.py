"""Render actual-ROM captures from tests/travel-rom.cjs for visual inspection."""
import json
from pathlib import Path
from PIL import Image
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
for name in ['travel-follow-pikachu','travel-follow-rhyhorn','travel-riding-rhyhorn','travel-indoor']:
    frame(name).resize((720,480),Image.Resampling.NEAREST).save(OUT/(name+'.png'))
print('Rendered actual ROM follow/ride sequences (slowed for review), four rider directions and stills')
