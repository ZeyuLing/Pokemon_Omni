"""Decode hash-locked Rocket ROM interface assets into the GBA adapter.

No screenshots are pasted into the game: tilemaps, tiles and palettes are
decoded independently, then composed with live game text/HP/items at runtime.
"""
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image
from extract_rocket_rom import lz10, USER_SHA

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/pallet'
MANIFEST = ROOT / 'assets/source/game-ui.json'
ROM_PATH = ROOT / 'assets/imported/rocket-user/rocket-user-modifier.gba'
REFERENCE_COMMIT = '5eff78649e7170a877b961ef0b3da13b81a16038'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def colors(data):
    return [((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31,
             ((v >> 10) & 31) * 255 // 31, 255)
            for (v,) in struct.iter_unpack('<H', data)]


def tile_image(data, width, height, pal, block_w=0, block_h=0, transparent=True):
    assert width % 8 == height % 8 == 0
    assert len(data) == width * height // 2
    image = Image.new('RGBA', (width, height))
    block_w, block_h = block_w or width, block_h or height
    offset = 0
    for by in range(0, height, block_h):
        for bx in range(0, width, block_w):
            for ty in range(by, by + block_h, 8):
                for tx in range(bx, bx + block_w, 8):
                    for y in range(8):
                        for x in range(0, 8, 2):
                            value = data[offset]
                            offset += 1
                            for dx, index in ((0, value & 15), (1, value >> 4)):
                                image.putpixel((tx+x+dx, ty+y), (0, 0, 0, 0) if transparent and not index else pal[index])
    return image


def tilemap_image(tiles, tilemap, pal, palette_base=0, transparent=False):
    image = Image.new('RGBA', (256, len(tilemap)//64*8))
    for cell, (entry,) in enumerate(struct.iter_unpack('<H', tilemap)):
        tile = entry & 1023
        bank = (entry >> 12) - palette_base
        for y in range(8):
            for x in range(8):
                sx, sy = (7-x if entry & 1024 else x), (7-y if entry & 2048 else y)
                byte = tiles[tile*32+sy*4+sx//2]
                index = (byte >> (4*(sx & 1))) & 15
                color = (0, 0, 0, 0) if transparent and not index else pal[bank*16+index]
                image.putpixel(((cell % 32)*8+x, (cell//32)*8+y), color)
    return image


def main():
    rom = ROM_PATH.read_bytes()
    if sha(rom) != USER_SHA:
        raise ValueError('The UI importer requires the archived, hash-verified Rocket ROM')
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads(MANIFEST.read_text('utf-8')) if MANIFEST.exists() else None
    sources, pictures = {}, {}

    def read(name, offset, raw_size=0, reference=None):
        data, consumed = (rom[offset:offset+raw_size], raw_size) if raw_size else lz10(rom, offset)
        record = {'offset': hex(offset), 'encoding': 'raw' if raw_size else 'lz10',
                  'encoded_bytes': consumed, 'decoded_bytes': len(data),
                  'encoded_sha256': sha(rom[offset:offset+consumed]), 'decoded_sha256': sha(data)}
        if reference:
            record['structural_reference'] = f'https://github.com/pret/pokeemerald/blob/{REFERENCE_COMMIT}/{reference}'
        if old and name in old['sources'] and record != old['sources'][name]:
            raise ValueError('UI source record changed: '+name)
        sources[name] = record
        return data

    for name, index in [('grass', 0), ('building', 8)]:
        fields = struct.unpack_from('<5I', rom, 0x5a6368+index*20)
        tiles = read(name+'_tiles', fields[0]-0x8000000, reference='src/data/graphics/battle_environment.h')
        tilemap = read(name+'_map', fields[1]-0x8000000)
        pal = colors(read(name+'_palette', fields[4]-0x8000000))
        pictures['battle_'+name] = tilemap_image(tiles, tilemap, pal, 2).crop((0, 0, 240, 112))

    textbox_tiles = read('textbox_tiles', 24590188, reference='graphics/battle_interface/textbox.png')
    textbox_map = read('textbox_map', 24591504)
    textbox_pal = colors(read('textbox_palette', 24591436))
    textbox = tilemap_image(textbox_tiles, textbox_map, textbox_pal, transparent=True)
    textbox.save(OUT/'source-textbox-map.png')
    pictures['battle_textbox'] = textbox.crop((0, 112, 240, 160))
    pictures['battle_commands'] = textbox.crop((0, 272, 240, 320))
    pictures['battle_moves'] = textbox.crop((0, 432, 240, 480))
    health_pal = colors(read('healthbox_palette', 24719944, 32))
    for name, offset, height, block_h in [('player', 24774772, 64, 64), ('opponent', 24775448, 32, 32)]:
        data = read('healthbox_'+name, offset, reference=f'graphics/battle_interface/healthbox_singles_{name}.png')
        pictures['healthbox_'+name] = tile_image(data, 128, height, health_pal, 64, block_h)
    pictures['hp_elements'] = tile_image(read('hp_elements', 24720008, 384), 96, 8,
                                       colors(read('hp_palette', 24719976, 32)))
    pictures['exp_elements'] = tile_image(read('exp_elements', 24720392, 288), 72, 8, health_pal)
    bag_pal = colors(read('bag_background_palette', 29860640))
    bag_bg_tiles = read('bag_background_tiles', 29860792)
    pictures['bag_background'] = tilemap_image(bag_bg_tiles, read('bag_background_map', 29861412), bag_pal).crop((0, 0, 240, 160))
    # item_menu.c: DrawPocketIndicatorSquare uses palette 1, tiles 0x17/0x2b.
    for name, tile in [('idle', 0x17), ('active', 0x2b)]:
        pictures['bag_indicator_'+name] = tile_image(bag_bg_tiles[tile*32:(tile+1)*32], 8, 8, bag_pal[16:], transparent=False)
    bag_tiles = read('bag_sprite_tiles', 29854748, reference='graphics/bag/bag_male.png')
    bag_pal = colors(read('bag_sprite_palette', 29860600))
    for name, frame in [('items', 1), ('key', 2), ('balls', 3), ('tms', 4), ('berries', 5)]:
        pictures['bag_'+name] = tile_image(bag_tiles[frame*2048:(frame+1)*2048], 64, 64, bag_pal)
    for name, gfx, pal in [('potion', 29946528, 29946728), ('pokeball', 29940256, 29940432), ('bag_return', 29940096, 29940232)]:
        pictures[name] = tile_image(read(name+'_tiles', gfx), 24, 24, colors(read(name+'_palette', pal)))
    arrows = tile_image(read('scroll_arrow_tiles', 13590936, reference='graphics/interface/scroll_indicator.png'), 16, 32,
                        colors(read('scroll_arrow_palette', 13590904, 32, 'graphics/interface/red.pal')))
    pictures['bag_arrow_left'] = arrows.crop((0, 0, 16, 16))
    pictures['bag_arrow_right'] = pictures['bag_arrow_left'].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    pictures['window'] = tile_image(read('window_tiles', 11963192, 288, 'graphics/text_window/1.png'), 24, 24,
                                    colors(read('window_palette', 11968952, 32)), transparent=False)

    blob, declarations, images = bytearray(), [], {}
    for name, im in pictures.items():
        im.save(OUT/('ui-'+name+'.png'))
        offset = len(blob)
        for r, g, b, a in im.get_flattened_data():
            blob += struct.pack('<H', 0x8000 if a == 0 else (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
        declarations.append(f'#define UI_{name.upper()} {offset}u\n#define UI_{name.upper()}_W {im.width}\n#define UI_{name.upper()}_H {im.height}')
        images[name] = {'width': im.width, 'height': im.height, 'offset': offset, 'pixel_sha256': sha(blob[offset:])}
    (OUT/'game_ui.bin').write_bytes(blob)
    (OUT/'game_ui.h').write_text('#ifndef OMNI_GAME_UI_H\n#define OMNI_GAME_UI_H\nextern const unsigned char omni_game_ui_blob[];\n'+'\n'.join(declarations)+'\n#endif\n', 'utf-8')
    # Zig's assembler cache does not track .incbin contents; make changes to
    # the payload change the assembly source as well as the generated offsets.
    (OUT/'game_ui.s').write_text(f'/* Embedded UI SHA-256: {sha(blob)} */\n'+'.section .rodata\n.balign 4\n.global omni_game_ui_blob\nomni_game_ui_blob:\n.incbin "build/pallet/game_ui.bin"\n', 'utf-8')
    manifest = {'schema_version': 1, 'rom_path': str(ROM_PATH.relative_to(ROOT)).replace('\\', '/'), 'rom_sha256': USER_SHA,
                'scope': 'Actual Rocket ROM UI pixels; portable core is unchanged. Not a port of the source menu engine.',
                'terrain_table_offset': '0x5a6368', 'reference_commit': REFERENCE_COMMIT, 'sources': sources, 'images': images,
                'blob_bytes': len(blob), 'blob_sha256': sha(blob)}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    print(f'Rocket UI: {len(sources)} source blocks, {len(images)} decoded assets, {len(blob)} bytes')


if __name__ == '__main__':
    main()
