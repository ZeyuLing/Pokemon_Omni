"""Prepare generated art for GBA, with one isotropic scale for all 16 soldiers.

The generated sheet is reference-sized art, not directly a game sprite. Alpha
bounds locate each cell's content; they never determine an individual scale.
All directions use the FireRed visible-height budget and foot baseline.
"""
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/characters/field-armies'

def cells(path,rows,row_bounds=None):
    sheet=Image.open(path).convert('RGBA');w,h=sheet.size;result=[]
    for row in range(rows):
        for col in range(4):
            top,bottom=(row_bounds[row],row_bounds[row+1]) if row_bounds else (round(row*h/rows),round((row+1)*h/rows))
            cell=sheet.crop((round(col*w/4),top,round((col+1)*w/4),bottom))
            cell.putalpha(cell.getchannel('A').point(lambda v:255 if v>=192 else 0))
            result.append(cell.crop(cell.getbbox()))
    return result

def quantize(frames):
    # One opaque 15-color palette for all directions, plus transparent index 0.
    pixels=[p[:3] for f in frames for p in f.get_flattened_data() if p[3]]
    colors=Image.new('RGB',(len(pixels),1));colors.putdata(pixels)
    pal=colors.quantize(colors=15,method=Image.Quantize.MEDIANCUT)
    result=[]
    for frame in frames:
        q=frame.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE).convert('RGBA')
        q.putalpha(frame.getchannel('A'));result.append(q)
    return result

def soldier_frames():
    # Verified transparent gutters; the generated image did not honor equal rows.
    raw=cells(ART/'soldiers-source.png',4,[0,320,600,875,1199])
    scale=min(20/max(f.height for f in raw),18/max(f.width for f in raw))
    frames=[]
    for cell in raw:
        small=cell.resize((round(cell.width*scale),round(cell.height*scale)),Image.Resampling.NEAREST)
        frame=Image.new('RGBA',(24,32));frame.paste(small,((24-small.width)//2,31-small.height))
        box=frame.getbbox();assert 19<=box[3]-box[1]<=20 and box[3]==31
        frames.append(frame)
    return [quantize(frames[i:i+4]) for i in range(0,16,4)]

def standard_frames():
    raw=cells(ART/'standards-source.png',5,[0,280,550,810,1060,1402])[16:]
    scale=min(30/max(f.height for f in raw),24/max(f.width for f in raw))
    result=[]
    for cell in raw:
        small=cell.resize((round(cell.width*scale),round(cell.height*scale)),Image.Resampling.NEAREST)
        frame=Image.new('RGBA',(26,32));frame.paste(small,(0,32-small.height));result.append(frame)
    return quantize(result)

if __name__=='__main__':
    out=Image.new('RGBA',(96,160))
    for row,frames in enumerate(soldier_frames()):
        for col,frame in enumerate(frames):out.paste(frame,(col*24,row*32))
    for col,frame in enumerate(standard_frames()):out.paste(frame,(col*24,128))
    out.save(ROOT/'build/pallet/field-armies-native.png')
    out.resize((576,960),Image.Resampling.NEAREST).save(ROOT/'build/pallet/field-armies-proof.png')
