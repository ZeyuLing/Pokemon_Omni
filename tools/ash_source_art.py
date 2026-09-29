"""Decode the user's Emerald IV Ash overworld and trainer art without resizing.

Table layout: pret/pokeemerald ObjectEventGraphicsInfo and SpriteFrameImage.
ROM payload and extracted PNGs stay local. Source offsets are hash-locked.
"""
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image
from extract_rocket_rom import lz10
from build_game_ui_assets import tile_image, colors

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
                    scope='Walking only; trainer-front usage and research-only battle backs are recorded separately in ash-iv-trainer.json',
                    credits='究极绿宝石小智版制作组；转载说明提及八木、司徒参与行走素材，单帧作者尚未独立核实。',
                    distribution='User ROM and decoded art local-only, not included in Git')
    (ROOT/'assets/source/ash-iv-overworld.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return frames


def ash_trainer_art():
    """Source-native front plus four audited backs; only the front is in use.

    The hack moved its trainer tables. The original back palette table points
    to placeholder art, so follow the relocated table used by its code instead.
    """
    rom = (ROOT / ROM).read_bytes()
    if hashlib.sha256(rom).hexdigest() != SHA:
        raise ValueError('Wrong Emerald IV Ash source ROM')
    front_table, palettes, trainer_id = 0x101be90, 0x101c660, 71
    front, palette = 0x36be40, 0x305b60
    back_table, back_palettes, frame_table = 0x1d4c7c8, 0x1d4c788, 0x2ff428
    assert struct.unpack_from('<IHH', rom, front_table + trainer_id * 8) == (front + 0x8000000, 2048, trainer_id)
    assert struct.unpack_from('<II', rom, palettes + trainer_id * 8) == (palette + 0x8000000, trainer_id)
    assert struct.unpack_from('<IHH', rom, back_table) == (0x8d66480, 8192, 0)
    assert struct.unpack_from('<II', rom, back_palettes) == (palette + 0x8000000, 0)
    # Literal references in the source ROM's code, not merely unused old tables.
    for reference, table in ((0x5df78, front_table), (0x5df80, palettes), (0x5dfdc, back_palettes)):
        assert struct.unpack_from('<I', rom, reference)[0] == table + 0x8000000
    raw, compressed_size = lz10(rom, front)
    pal, palette_size = lz10(rom, palette)
    assert len(raw) == 2048 and len(pal) == 32
    front_image = tile_image(raw, 64, 64, colors(pal))
    backs, records = [], []
    for index in range(4):
        offset = 0xd66480 + index * 2048
        assert struct.unpack_from('<II', rom, frame_table + index * 8) == (offset + 0x8000000, 2048)
        frame = tile_image(rom[offset:offset + 2048], 64, 64, colors(pal))
        backs.append(frame)
        records.append(dict(index=index, offset=offset, bytes=2048, bbox=frame.getbbox(),
                            rgba_sha256=hashlib.sha256(frame.tobytes()).hexdigest()))
    out = ROOT / 'assets/imported/ultra-emerald-4-ash-user/ash-trainer-front.png'
    front_image.save(out)
    manifest = dict(source='user-provided Emerald IV Ash ROM', rom=ROM, sha256=SHA,
                    reference='动画 XY 小智衣装；来源改版像素改编，少年阶段，不推定年龄或剧情年代。',
                    conversion='Native 64x64 4bpp decode; no crop, resize, repaint or palette substitution',
                    front=dict(table=front_table, trainer_id=trainer_id, offset=front,
                               compressed_bytes=compressed_size, decoded_bytes=len(raw),
                               palette_table=palettes, palette=palette, palette_compressed_bytes=palette_size,
                               bbox=front_image.getbbox(), rgba_sha256=hashlib.sha256(front_image.tobytes()).hexdigest(),
                               output=out.relative_to(ROOT).as_posix(), usage=['GBA trainer card', 'GBA cast gallery', 'generated story-bible portrait']),
                    back=dict(table=back_table, palette_table=back_palettes, frame_table=frame_table,
                              palette=palette, frames=records, status='decoded_for_research_only_not_in_runtime',
                              limitation='Four source back poses verified as pixels; source animation timing and Omni send-out/capture animation remain unimplemented'),
                    credits='究极绿宝石小智版制作组；正面与背面像素图的具体作者未独立核实。',
                    distribution='User ROM and decoded PNGs local-only; not included in Git')
    (ROOT / 'assets/source/ash-iv-trainer.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return front_image, backs

if __name__ == '__main__':
    frames = ash_frames()
    sheet = Image.new('RGBA', (144,32))
    for i,frame in enumerate(frames): sheet.paste(frame,(16*i,0))
    out=ROOT/'build/pallet';out.mkdir(parents=True,exist_ok=True)
    sheet.save(out/'ash-iv-native.png')
    front, backs = ash_trainer_art()
    trainers = Image.new('RGBA', (320, 64))
    for index, frame in enumerate([front, *backs]):
        trainers.paste(frame, (index * 64, 0))
    trainers.save(out / 'ash-iv-trainer-native.png')
    print('Decoded native Ash: nine walking frames, trainer front, four research-only back poses')
