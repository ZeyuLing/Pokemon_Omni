"""Contact sheets of actual ROM frames; source sheets are not visual acceptance."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/pallet'
reviews = json.loads((OUT/'travel-roster-review.json').read_text('utf8'))['reviews']
for page in range((len(reviews)+15)//16):
    sheet = Image.new('RGB', (1024, 864), '#20252b')
    draw = ImageDraw.Draw(sheet)
    for index, review in enumerate(reviews[page*16:page*16+16]):
        x, y = index%2*512, index//2*108
        draw.text((x+4,y+2), str(review['species']), fill='white')
        for view in range(8):
            direction,phase=view//2,view%2
            pose = next(p for p in review['poses'] if p['direction']==direction and p['mountPose']%2==phase)
            frame = Image.frombytes('RGBA',(240,160),(OUT/(pose['file']+'.rgba')).read_bytes())
            sheet.paste(frame.crop((88,16,152,104)), (x+view*64,y+20))
    sheet.save(OUT/f'roster-review-{page+1:02}.png')
for species in (6,18,130,131,384):
    review = next(r for r in reviews if r['species']==species)
    frames = [Image.frombytes('RGBA',(240,160),(OUT/(p['file']+'.rgba')).read_bytes()).resize((720,480),Image.Resampling.NEAREST) for p in review['poses']]
    frames[0].save(OUT/f'roster-{species}.gif',save_all=True,append_images=frames[1:],duration=250,loop=0)
print(f'Rendered {len(reviews)} actual-ROM mounts into contact sheets and selected GIFs')
