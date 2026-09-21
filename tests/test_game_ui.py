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
        samples = [('wild-battle', 'battle_grass', (108, 0, 140, 92)),
                   ('rocket-battle', 'battle_building', (108, 0, 140, 92)),
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
            for pocket in ('items', 'balls', 'key'):
                name = f'bag-layout-{pocket}-{quantity}'
                rgba = (ROOT/f'build/pallet/{name}.rgba').read_bytes()
                def ink(left, top, right, bottom):
                    return [(x, y) for y in range(top, bottom) for x in range(left, right)
                            if tuple(c >> 3 for c in rgba[(y*240+x)*4:(y*240+x)*4+3]) == (5, 7, 10)]
                with self.subTest(screen=name):
                    self.assertTrue(ink(122, 16, 194, 28), 'First row must contain item or close label')
                    self.assertFalse(ink(122, 28, 228, 32), 'Rows require a clear gap')
                    self.assertEqual(bool(ink(122, 32, 194, 44)), bool(quantity), 'Close follows the item by one row')
                    self.assertFalse(ink(112, 44, 232, 125), 'No floating quantity, header or displaced close row')
                    self.assertFalse(ink(112, 139, 232, 151), 'Footer must not touch bottom frame')
                    self.assertFalse(ink(102, 103, 106, 151), 'Description cannot cross its right edge')
                    title = ink(35, 10, 94, 22)
                    self.assertTrue(title)
                    self.assertLessEqual(abs((min(x for x, _ in title)+max(x for x, _ in title))/2-63.5), 2)
                    if quantity and pocket != 'key':
                        count = ink(198, 16, 228, 28)
                        self.assertTrue(count, 'Quantity must share the item row')
                        self.assertEqual(max(x for x, _ in count), 226, 'Digit group must align to the same right edge')
                        columns = sorted(set(x for x, _ in count))
                        self.assertLessEqual(max(b-a for a, b in zip(columns, columns[1:])), 7, 'Multiplier must stay beside its number')
                    else:
                        self.assertFalse(ink(198, 16, 228, 28), 'Empty/key pockets must not display a quantity')


if __name__ == '__main__':
    unittest.main()
