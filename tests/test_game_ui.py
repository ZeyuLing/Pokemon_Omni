"""Source decoding and real-ROM presentation checks, not mock screenshots."""
import hashlib
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from build_game_ui_assets import tile_image, tilemap_image
from extract_rocket_rom import lz10


class SourceInterfaceTests(unittest.TestCase):
    def test_tile_order_and_flips(self):
        palette = [(i, i, i, 255) for i in range(16)]
        tiles = bytes([0x21]*32+[0x43]*32)
        image = tile_image(tiles, 16, 8, palette)
        self.assertEqual(image.getpixel((0, 0)), palette[1])
        self.assertEqual(image.getpixel((9, 7)), palette[4])
        entries = [0x400, 1]+[0]*30
        image = tilemap_image(tiles, struct.pack('<32H', *entries), palette)
        self.assertEqual(image.getpixel((0, 0)), palette[2])
        self.assertEqual(image.getpixel((8, 0)), palette[3])

    def test_archived_rom_and_every_source_block(self):
        manifest = json.loads((ROOT/'assets/source/game-ui.json').read_text('utf-8'))
        rom = (ROOT/manifest['rom_path']).read_bytes()
        digest = lambda b: hashlib.sha256(b).hexdigest()
        self.assertEqual(digest(rom), manifest['rom_sha256'])
        for name, row in manifest['sources'].items():
            with self.subTest(asset=name):
                offset = int(row['offset'], 16)
                encoded = rom[offset:offset+row['encoded_bytes']]
                data = lz10(rom, offset)[0] if row['encoding'] == 'lz10' else encoded
                self.assertEqual(digest(encoded), row['encoded_sha256'])
                self.assertEqual(digest(data), row['decoded_sha256'])
                self.assertEqual(len(data), row['decoded_bytes'])
        blob = (ROOT/'build/pallet/game_ui.bin').read_bytes()
        self.assertEqual(digest(blob), manifest['blob_sha256'])
        self.assertEqual(len(blob), manifest['blob_bytes'])
        for row in manifest['images'].values():
            data = blob[row['offset']:row['offset']+row['width']*row['height']*2]
            self.assertEqual(digest(data), row['pixel_sha256'])

    def test_actual_emulator_displays_source_pixels(self):
        # These regions exclude all live text, actors, sprites and healthboxes.
        manifest = json.loads((ROOT/'assets/source/game-ui.json').read_text('utf-8'))
        blob = (ROOT/'build/pallet/game_ui.bin').read_bytes()
        samples = [('wild-battle', 'battle_grass', (116, 0, 140, 72)),
                   ('rocket-battle', 'battle_building', (116, 0, 140, 72)),
                   ('bag-items', 'bag_background', (2, 26, 20, 68)),
                   ('bag-balls', 'bag_background', (2, 26, 20, 68))]
        for screenshot, name, rect in samples:
            with self.subTest(screen=screenshot):
                rgba = (ROOT/f'build/pallet/{screenshot}.rgba').read_bytes()
                row = manifest['images'][name]
                for y in range(rect[1], rect[3]):
                    for x in range(rect[0], rect[2]):
                        expected = struct.unpack_from('<H', blob, row['offset']+(y*row['width']+x)*2)[0]
                        r, g, b = rgba[(y*240+x)*4:(y*240+x)*4+3]
                        actual = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
                        self.assertEqual(actual, expected, (screenshot, x, y))

    def test_bag_text_stays_in_rows_and_inside_frames(self):
        # Read final framebuffer pixels, so this catches misplaced draw calls
        # even when every source image and every button still works correctly.
        for quantity in (0, 9, 99, 999):
            for pocket in ('items', 'balls', 'tms', 'berries', 'key'):
                name = f'bag-layout-{pocket}-{quantity}'
                rgba = (ROOT/f'build/pallet/{name}.rgba').read_bytes()
                def ink(left, top, right, bottom):
                    return [(x, y) for y in range(top, bottom) for x in range(left, right)
                            if tuple(c >> 3 for c in rgba[(y*240+x)*4:(y*240+x)*4+3]) == (0, 0, 0)]
                with self.subTest(screen=name):
                    has_item = bool(quantity) and pocket not in ('tms', 'berries')
                    self.assertTrue(ink(120, 17, 194, 29), 'Source list starts at window (112,16) + (8,1)')
                    self.assertFalse(ink(120, 29, 231, 33), 'Rows require a clear gap')
                    self.assertEqual(bool(ink(120, 33, 194, 45)), has_item, 'Close follows the item by one row')
                    self.assertFalse(ink(112, 45, 232, 151), 'The source bag has no money panel or footer')
                    self.assertFalse(ink(104, 103, 106, 151), 'Description cannot cross its right edge')
                    title = ink(35, 9, 94, 21)
                    self.assertTrue(title)
                    self.assertLessEqual(abs((min(x for x, _ in title)+max(x for x, _ in title))/2-63.5), 2)
                    if has_item and pocket != 'key':
                        count = ink(198, 17, 231, 29)
                        self.assertTrue(count, 'Quantity must share the item row')
                        self.assertEqual(max(x for x, _ in count), 229, 'Source quantity right edge is window x112 + 119')
                        columns = sorted(set(x for x, _ in count))
                        self.assertLessEqual(max(b-a for a, b in zip(columns, columns[1:])), 7, 'Multiplier must stay beside its number')
                    else:
                        self.assertFalse(ink(198, 17, 231, 29), 'Empty/key pockets must not display a quantity')

    def test_battle_name_and_level_do_not_overwrite_healthbox_border(self):
        manifest=json.loads((ROOT/'assets/source/game-ui.json').read_text('utf-8'))
        blob=(ROOT/'build/pallet/game_ui.bin').read_bytes()
        for name in ('wild-battle','rocket-battle'):
            rgba=(ROOT/f'build/pallet/{name}.rgba').read_bytes()
            for asset,x,y,region in [('opponent',12,14,(12,19,116,30)),('player',126,72,(132,77,238,88))]:
                offset=manifest['images']['healthbox_'+asset]['offset']
                count=0
                for py in range(region[1],region[3]):
                    for px in range(region[0],region[2]):
                        p=(py*240+px)*4
                        if tuple(c>>3 for c in rgba[p:p+3])!=(5,7,10):continue
                        count+=1
                        source=struct.unpack_from('<H',blob,offset+((py-y)*128+px-x)*2)[0]
                        self.assertEqual(source,31|(31<<5)|(27<<10),(name,asset,px,py,'Text must stay on the light interior'))
                self.assertGreater(count,0)

    def test_bag_source_sprite_anchors_and_no_extra_panels(self):
        manifest = json.loads((ROOT/'assets/source/game-ui.json').read_text('utf-8'))
        blob = (ROOT/'build/pallet/game_ui.bin').read_bytes()
        def compare(rgba, name, x, y):
            asset = manifest['images'][name]
            for sy in range(asset['height']):
                for sx in range(asset['width']):
                    color = struct.unpack_from('<H', blob, asset['offset']+(sy*asset['width']+sx)*2)[0]
                    if color & 0x8000:
                        continue
                    p = ((y+sy)*240+x+sx)*4
                    r,g,b = rgba[p:p+3]
                    self.assertEqual((r>>3)|((g>>3)<<5)|((b>>3)<<10), color, (name,x+sx,y+sy))
        for index, pocket in enumerate(('items','balls','tms','berries','key')):
            rgba = (ROOT/f'build/pallet/bag-layout-{pocket}-0.rgba').read_bytes()
            with self.subTest(pocket=pocket):
                compare(rgba,'bag_'+pocket,36,34)
                compare(rgba,'bag_return',8,72)
                compare(rgba,'bag_arrow_left',20,8)
                compare(rgba,'bag_arrow_right',92,8)
                for dot in range(5):
                    compare(rgba,'bag_indicator_'+('active' if dot==index else 'idle'),40+dot*8,24)
        for quantity in (9,99,999):
            rgba=(ROOT/f'build/pallet/bag-layout-close-{quantity}.rgba').read_bytes()
            compare(rgba,'bag_return',8,72)
            # Closing selection moves down exactly one source list row.
            for row in range(9):
                for column in range(row+1 if row<5 else 9-row):
                    p=((36+row)*240+113+column)*4
                    self.assertEqual(rgba[p:p+3],b'\0\0\0')
        # Every pixel of the unused list must remain the source background,
        # detecting money/help labels regardless of text color. Include battle.
        background = manifest['images']['bag_background']['offset']
        for name in ['battle-bag']+[f'bag-layout-{p}-{n}' for n in (0,9,99,999) for p in ('items','balls','tms','berries','key')]:
            rgba=(ROOT/f'build/pallet/{name}.rgba').read_bytes()
            for y in range(49,144):
                for x in range(112,232):
                    r,g,b=rgba[(y*240+x)*4:(y*240+x)*4+3]
                    self.assertEqual((r>>3)|((g>>3)<<5)|((b>>3)<<10),struct.unpack_from('<H',blob,background+(y*240+x)*2)[0],(name,x,y))
        for quantity in (0,9,99,999):
            for a,b in [('wrap','items'),('back','key')]:
                self.assertEqual((ROOT/f'build/pallet/bag-layout-{a}-{quantity}.rgba').read_bytes(),(ROOT/f'build/pallet/bag-layout-{b}-{quantity}.rgba').read_bytes(),'Pocket wrap order must match source')


if __name__ == '__main__':
    unittest.main()
