"""Reproducible runtime conversion of Ash art and the user's capped partner.

Source manifests are versioned. ROM sprite payloads remain local and are
decoded only from the hash-locked user-provided cartridge, never committed.
"""
import hashlib,io,json
from pathlib import Path
from PIL import Image
from extract_ultra_emerald_rom import ROM_PATH,SHA,TABLES
from extract_rocket_rom import pointer,lz10,sprite_png
ROOT=Path(__file__).resolve().parents[1]

from ash_source_art import ash_frames

def partner_frames():
    rom=(ROOT/ROM_PATH).read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    images=[];sources=[]
    for side,pal in [('front','normal_palette'),('back','normal_palette'),('front','shiny_palette'),('back','shiny_palette')]:
        sa=pointer(rom,TABLES[side]+1094*8);pa=pointer(rom,TABLES[pal]+1094*8)
        sprite,_=lz10(rom,sa);palette,_=lz10(rom,pa);data=sprite_png(sprite,palette)
        images.append(Image.open(io.BytesIO(data)).convert('RGBA'))
        sources.append(dict(side=side,palette=pal,sprite_offset=sa,palette_offset=pa,decoded_png_sha256=hashlib.sha256(data).hexdigest()))
    manifest=dict(source_rom_sha256=SHA,source_sid=1094,source_name='搭档皮卡丘',sprites=sources,appearance='红白帽；以用户5.8实际素材为准，不等同于官方LGPE搭档必须戴帽的说法。',ash=dict(manifest='assets/source/ash-iv-overworld.json',source='user-provided Emerald IV Ash',runtime_frame=[16,32],conversion='native 4bpp; no resizing',reference='动画 XY 小智服装的来源改版像素形象'))
    (ROOT/'assets/source/initialization-art.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return images

def partner_overworld():
    front=partner_frames()[0];front=front.crop(front.getbbox());front.thumbnail((16,16),Image.Resampling.NEAREST)
    frame=Image.new('RGBA',(16,32));frame.alpha_composite(front,((16-front.width)//2,16-front.height))
    return frame
