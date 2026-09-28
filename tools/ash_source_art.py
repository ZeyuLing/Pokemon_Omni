"""Decode the user's Emerald IV Ash overworld at native scale, never resize.

Table layout: pret/pokeemerald ObjectEventGraphicsInfo and SpriteFrameImage.
ROM payload and extracted PNGs stay local. Source offsets are hash-locked.
"""
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ROM = 'assets/imported/ultra-emerald-4-ash-user/ultra-emerald-4-ash-user.gba'
SHA = '30a54ca97fe653dee226d004b1b9b36cc2065116089d9a8c7c96be99bbc0c8bb'
INFO, TABLE, PALETTE_ENTRY, PALETTE = 0x509954, 0x505a8c, 0x50bc08, 0x4987f8

def ash_frames():
    rom = (ROOT / ROM).read_bytes()
    if hashlib.sha256(rom).hexdigest() != SHA:
        raise ValueError('Wrong Emerald IV Ash source ROM; do not reuse these offsets')
    assert struct.unpack_from('<HH', rom, INFO + 8) == (16, 32)
    assert struct.unpack_from('<I', rom, INFO + 28)[0] == TABLE + 0x08000000
    assert struct.unpack_from('<IH', rom, PALETTE_ENTRY) == (PALETTE + 0x08000000, 0x1100)
    colors = [((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31,
               ((v >> 10) & 31) * 255 // 31)
              for (v,) in struct.iter_unpack('<H', rom[PALETTE:PALETTE + 32])]
    frames, records = [], []
    for index in range(9):
        pointer, size = struct.unpack_from('<II', rom, TABLE + index * 8)
        offset = pointer - 0x08000000
        assert size == 256 and 0 <= offset <= len(rom) - size
        frame = Image.new('RGBA', (16, 32))
        for y in range(32):
            for x in range(16):
                value = rom[offset + (y // 8 * 2 + x // 8) * 32 + y % 8 * 4 + x % 8 // 2]
                color = (value >> (4 * (x % 2))) & 15
                frame.putpixel((x, y), (*colors[color], 255 if color else 0))
        records.append(dict(index=index,offset=offset,bytes=size,bbox=frame.getbbox(),
                            rgba_sha256=hashlib.sha256(frame.tobytes()).hexdigest()))
        frames.append(frame)
    manifest = dict(source='user-provided Emerald IV Ash ROM',rom=ROM,sha256=SHA,
                    graphics_info=INFO,frame_table=TABLE,palette_entry=PALETTE_ENTRY,palette=PALETTE,
                    reference='动画 XY 小智衣装；来源改版像素改编，不冒称初代关都服装。',
                    runtime_frame=[16,32],conversion='Native 4bpp decode only; no crop, resize, recolor or per-frame recentering',
                    order=['down idle','up idle','left idle','down step1','down step2','up step1','up step2','left step1','left step2'],
                    right='Horizontal mirror, same convention as source GBA engine',frames=records,
                    scope='Walking only; cycling/surfing/battle backs and portraits are not replaced',
                    credits='究极绿宝石小智版制作组；转载说明提及八木、司徒参与行走素材，单帧作者尚未独立核实。',
                    distribution='User ROM and decoded art local-only, not included in Git')
    (ROOT/'assets/source/ash-iv-overworld.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return frames

if __name__ == '__main__':
    frames = ash_frames()
    sheet = Image.new('RGBA', (144,32))
    for i,frame in enumerate(frames): sheet.paste(frame,(16*i,0))
    out=ROOT/'build/pallet';out.mkdir(parents=True,exist_ok=True)
    sheet.save(out/'ash-iv-native.png')
    print('Decoded nine native Emerald IV Ash frames; original geometry preserved')
