"""Protect native pixels across every portrait, including editable custom sources."""
import hashlib
import json
import struct
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from native_cast_art import pixel_portrait
from fireash_cast_art import native_portrait

manifest = json.loads((ROOT / 'assets/characters/manifest.json').read_text('utf-8'))
blob = (ROOT / 'build/pallet/cast.bin').read_bytes()
seen = set()
for index, entry in enumerate(manifest['portraits']):
    assert 'cell' not in entry, 'Rejected illustration atlas reintroduced'
    assert entry['origin'] != 'built-in image_gen'
    path = ROOT / entry['source_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    if entry.get('decoder') == 'native_pixel_rows':
        image = pixel_portrait(entry['actor'])
        assert len(image.getcolors()) <= 16
        assert set(image.getchannel('A').get_flattened_data()) == {0, 255}
    elif entry.get('decoder') == 'fireash_native':
        image = native_portrait(entry['actor'])
    else:
        image = Image.open(path).convert('RGBA')
    assert image.width <= 80 and image.height <= 80
    expected = Image.new('RGBA', (80, 80))
    expected.paste(image, ((80-image.width)//2, 80-image.height))
    actual = Image.open(ROOT / 'build/pallet/cast' / (entry['actor']+'.png')).convert('RGBA')
    assert actual.tobytes() == expected.tobytes(), entry['actor'] + ': resampled or shifted source'
    encoded = b''.join(struct.pack('<H', 0x8000 if a < 128 else
                      (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
                      for r, g, b, a in expected.get_flattened_data())
    assert blob[index*12800:(index+1)*12800] == encoded
    seen.add(hashlib.sha256(encoded).hexdigest())
assert len(seen) == len(manifest['portraits'])
print(f'PASS: {len(seen)} distinct source-exact compiled portraits; no illustration resize path; three native 16-color redraws')
