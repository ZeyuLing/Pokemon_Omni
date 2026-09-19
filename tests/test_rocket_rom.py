"""Bounds and rendering tests for the local-only ROM importer; no ROM required."""
import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

spec = importlib.util.spec_from_file_location('rocket', Path(__file__).resolve().parents[1] / 'tools/extract_rocket_rom.py')
rocket = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rocket)


class RocketParserTests(unittest.TestCase):
    def test_overlapping_lz_reference(self):
        stream = bytes.fromhex('10090000104142433002')
        self.assertEqual(rocket.lz10(stream, 0), (b'ABCABCABC', len(stream)))

    def test_bad_lz_streams(self):
        for stream in [b'', bytes.fromhex('1001000000'), bytes.fromhex('10030000800000'),
                       bytes.fromhex('10000000'), bytes.fromhex('10010001')]:
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                rocket.lz10(stream, 0)

    def test_rom_pointers(self):
        self.assertEqual(rocket.pointer(struct.pack('<I', 0x08000002), 0), 2)
        for value in [0, 0x07000000, 0x08000004]:
            with self.assertRaises(ValueError):
                rocket.pointer(struct.pack('<I', value), 0)

    def test_latin_identity_encoding(self):
        self.assertEqual(rocket.decode_name(bytes([0xC3, 0xE1, 0xE4, 0xE9, 0xE0, 0xE7, 0xE3, 0xFF, 0xBB])), 'Impulso')
        self.assertEqual(rocket.decode_name(bytes([0x5A, 0x6F, 0xB5, 0xB6])), 'Íí♂♀')

    def test_tile_order_palette_and_transparency(self):
        tiles = bytearray(2048)
        tiles[0] = 0x21  # lower nibble is left pixel
        tiles[32] = 3    # next tile is x=8
        tiles[256] = 1   # next tile row is y=8
        palette = struct.pack('<16H', 0x7FFF, 31, 31 << 5, 31 << 10, *([0] * 12))
        png = rocket.sprite_png(tiles, palette)
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        cursor, compressed = 8, b''
        while cursor < len(png):
            length = struct.unpack_from('>I', png, cursor)[0]
            kind = png[cursor + 4:cursor + 8]
            body = png[cursor + 8:cursor + 8 + length]
            self.assertEqual(struct.unpack_from('>I', png, cursor + 8 + length)[0], zlib.crc32(kind + body))
            if kind == b'IDAT':
                compressed += body
            cursor += length + 12
        raw = zlib.decompress(compressed)
        pixel = lambda x, y: raw[y * 257 + 1 + x * 4:y * 257 + 5 + x * 4]
        self.assertEqual(pixel(0, 0), bytes([255, 0, 0, 255]))
        self.assertEqual(pixel(1, 0), bytes([0, 255, 0, 255]))
        self.assertEqual(pixel(8, 0), bytes([0, 0, 255, 255]))
        self.assertEqual(pixel(0, 8), bytes([255, 0, 0, 255]))
        self.assertEqual(pixel(2, 0)[3], 0)


if __name__ == '__main__':
    unittest.main()
