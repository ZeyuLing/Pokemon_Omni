"""Riding art review from actual ROM captures at integer nearest-neighbor scale."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

OUT=Path(__file__).resolve().parents[1]/'build/pallet'
reviews=json.loads((OUT/'travel-roster-review.json').read_text('utf8'))['reviews']
lookup={r['species']:r for r in reviews}
selected=[(111,'Rhyhorn'),(59,'Arcanine'),(18,'Pidgeot'),(131,'Lapras'),(130,'Gyarados'),(1021,'Raging Bolt')]
sheet=Image.new('RGB',(192*len(selected),4*264),'#20252b');draw=ImageDraw.Draw(sheet)
for col,(species,name) in enumerate(selected):
    for direction in range(4):
        pose=next(p for p in lookup[species]['poses'] if p['direction']==direction and p['mountPose']%2==0)
        frame=Image.frombytes('RGBA',(240,160),(OUT/(pose['file']+'.rgba')).read_bytes())
        draw.text((col*192+4,direction*264+4),f'{name} / {direction}',fill='white')
        sheet.paste(frame.crop((88,24,152,104)).resize((192,240),Image.Resampling.NEAREST),(col*192,direction*264+24))
sheet.save(OUT/'riding-art-six-species.png')
for clip in json.loads((OUT/'rider-transition-review.json').read_text('utf8')):
    frames=[Image.frombytes('RGBA',(240,160),(OUT/(s['file']+'.rgba')).read_bytes()).resize((720,480),Image.Resampling.NEAREST) for s in clip['samples']]
    frames[0].save(OUT/('rider-'+clip['name']+'.gif'),save_all=True,append_images=frames[1:],duration=80,loop=0)
print('Rendered six-species four-direction actual-ROM plate and slowed native rider transitions')
