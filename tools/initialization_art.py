"""Reproducible runtime conversion of Ash art and the user's capped partner.

Generated source art is versioned. ROM sprite payloads remain local and are
decoded only from the hash-locked user-provided cartridge, never committed.
"""
import hashlib,io,json
from pathlib import Path
from PIL import Image
from extract_ultra_emerald_rom import ROM_PATH,SHA,TABLES
from extract_rocket_rom import pointer,lz10,sprite_png
ROOT=Path(__file__).resolve().parents[1]

def ash_frames():
    image=Image.open(ROOT/'assets/characters/ash-kanto-walk-v1.png').convert('RGBA')
    frames=[]
    for y in range(3):
        for x in range(3):
            cell=image.crop((x*image.width//3,y*image.height//3,(x+1)*image.width//3,(y+1)*image.height//3))
            cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=160 else 0))
            box=cell.getbbox();assert box
            frames.append(cell.crop(box))
    scale=min(14/max(f.width for f in frames),22/max(f.height for f in frames))
    opaque=[p[:3] for p in image.get_flattened_data() if p[3]>=160]
    palette=Image.new('RGB',(len(opaque),1));palette.putdata(opaque)
    palette=palette.quantize(colors=15)
    native=[]
    for frame in frames:
        size=(max(1,round(frame.width*scale)),max(1,round(frame.height*scale)))
        tiny=frame.resize(size,Image.Resampling.NEAREST)
        rgb=tiny.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE).convert('RGBA');rgb.putalpha(tiny.getchannel('A'))
        canvas=Image.new('RGBA',(16,32));canvas.alpha_composite(rgb,((16-size[0])//2,32-size[1]));native.append(canvas)
    # Engine order: down/up/left idle; down/up/left two walk phases.
    return [native[i] for i in (0,3,6,1,2,4,5,7,8)]

def partner_frames():
    rom=(ROOT/ROM_PATH).read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    images=[];sources=[]
    for side,pal in [('front','normal_palette'),('back','normal_palette'),('front','shiny_palette'),('back','shiny_palette')]:
        sa=pointer(rom,TABLES[side]+1094*8);pa=pointer(rom,TABLES[pal]+1094*8)
        sprite,_=lz10(rom,sa);palette,_=lz10(rom,pa);data=sprite_png(sprite,palette)
        images.append(Image.open(io.BytesIO(data)).convert('RGBA'))
        sources.append(dict(side=side,palette=pal,sprite_offset=sa,palette_offset=pa,decoded_png_sha256=hashlib.sha256(data).hexdigest()))
    manifest=dict(source_rom_sha256=SHA,source_sid=1094,source_name='搭档皮卡丘',sprites=sources,appearance='红白帽；以用户5.8实际素材为准，不等同于官方LGPE搭档必须戴帽的说法。',ash=dict(path='assets/characters/ash-kanto-walk-v1.png',sha256=hashlib.sha256((ROOT/'assets/characters/ash-kanto-walk-v1.png').read_bytes()).hexdigest(),reference='宝可梦动画初代关都服装：红白帽、黑发、蓝马甲、白短袖、绿手套。',generator='built-in image_gen',runtime_frame=[16,32],max_visible_body=[14,22],conversion='alpha threshold160; nearest pixel resampling; shared15-color palette; feet aligned at31',prompt='assets/characters/ash-kanto-walk-v1.prompt.txt'))
    (ROOT/'assets/source/initialization-art.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return images

def partner_overworld():
    front=partner_frames()[0];front=front.crop(front.getbbox());front.thumbnail((16,16),Image.Resampling.NEAREST)
    frame=Image.new('RGBA',(16,32));frame.alpha_composite(front,((16-front.width)//2,16-front.height))
    return frame
