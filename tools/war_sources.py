"""Pinned Emerald source imports for the volcanic event stage (not ROM art)."""
import hashlib, io, json, struct, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REV = '5eff78649e7170a877b961ef0b3da13b81a16038'
BASE = f'https://raw.githubusercontent.com/pret/pokeemerald/{REV}/'
records = {}
PMD_REV='88cd945ef14b1d0fc3024a268482d77dfcc529a0'

def download(url):
    for attempt in range(3):
        try:return urllib.request.urlopen(url,timeout=20).read()
        except urllib.error.URLError:
            if attempt==2:raise

def pmd_get(path):
    target=ROOT/'.cache/war-pmd'/path
    url=f'https://raw.githubusercontent.com/PMDCollab/SpriteCollab/{PMD_REV}/'+path
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(download(url))
    data=target.read_bytes()
    records['pmd/'+path]=dict(path='pmd/'+path,url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    return data

def pokemon_frames(number):
    """Native pixel scale, two lateral directions, walk/shoot/hurt key frames.
    All frames share a union crop, so animation never recenters independently.
    """
    base=f'sprite/{number:04d}/'
    root=ET.fromstring(pmd_get(base+'AnimData.xml'))
    pmd_get(base+'credits.txt')
    anims={a.findtext('Name'):a for a in root.find('Anims')}
    def anim(name):
        a=anims[name]
        while a.findtext('CopyOf'):name=a.findtext('CopyOf');a=anims[name]
        return a,Image.open(io.BytesIO(pmd_get(base+name+'-Anim.png'))).convert('RGBA')
    frames=[]
    for direction in (2,6): # PMD left, right; no mirrored anatomy
        for name in ('Walk','Shoot','Hurt','Sleep'):
            a,im=anim(name if name in anims else 'Attack')
            w,h=int(a.findtext('FrameWidth')),int(a.findtext('FrameHeight'))
            count=im.width//w
            indices=[0,min(1,count-1)] if name=='Walk' else [0,min(int(a.findtext('HitFrame','1')),count-1)] if name=='Shoot' else [0]
            for i in indices:
                facing=direction if im.height>=8*h else 0
                frame=im.crop((i*w,facing*h,(i+1)*w,(facing+1)*h))
                assert frame.getbbox(),(number,name,direction,'Empty source animation frame')
                canvas=Image.new('RGBA',(128,128));canvas.paste(frame,(64-w//2,64-h//2));frames.append(canvas)
    boxes=[f.getbbox() for f in frames];box=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))
    return [f.crop(box) for f in frames]

def get(path):
    target = ROOT/'.cache/war-emerald'/path
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(download(BASE+path))
    data = target.read_bytes()
    records['emerald/'+path] = dict(path='emerald/'+path, url=BASE+path,
        sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    return data

def volcano_tiles():
    tiles, metas, palettes = [], [], []
    for directory in ('primary/general', 'secondary/lavaridge'):
        base = 'data/tilesets/'+directory
        im = Image.open(io.BytesIO(get(base+'/tiles.png')))
        tiles.append([im.crop((x,y,x+8,y+8)) for y in range(0,im.height,8) for x in range(0,im.width,8)])
        metas.append(list(struct.iter_unpack('<8H',get(base+'/metatiles.bin'))))
    for i in range(13):
        base='data/tilesets/'+('primary/general' if i<6 else 'secondary/lavaridge')
        palettes.append([tuple(map(int,l.split())) for l in get(base+f'/palettes/{i:02d}.pal').decode().splitlines()[3:19]])
    result={}
    for bank,meta in enumerate(metas):
        for index,parts in enumerate(meta):
            im=Image.new('RGB',(16,16),palettes[0][0])
            for part,t in enumerate(parts):
                ti=t&1023; tb=int(ti>=512); ti-=512 if tb else 0
                pixels=tiles[tb][ti]; pal=palettes[t>>12]
                for y in range(8):
                    for x in range(8):
                        c=pixels.getpixel((7-x if t&1024 else x,7-y if t&2048 else y))
                        if part>=4 and not c:continue
                        im.putpixel(((part%2)*8+x,((part%4)//2)*8+y),pal[c])
            result[index+bank*512]=im
    return result

if __name__=='__main__':
    tiles=volcano_tiles()
    out=Image.new('RGB',(640,((max(tiles)//16)+1)*30),(24,24,24));d=ImageDraw.Draw(out)
    for n,im in tiles.items():
        x=n%16*40;y=n//16*30;out.paste(im,(x,y));d.text((x,y+16),hex(n)[2:],fill='white')
    out.save(ROOT/'build/pallet/volcano-source-tiles.png')
