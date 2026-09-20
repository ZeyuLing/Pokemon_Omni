"""Independent exhaustive decode/source comparison for the GBA sprite atlas."""
import hashlib
import io
import json
from pathlib import Path
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / 'build/gba/asset-report.json').read_text(encoding='utf-8'))
atlas = (ROOT / 'build/gba/art.bin').read_bytes()
assert report['missing_images'] == 0
checked = set()
for row in report['images']+report.get('portraits',[]):
    offset = row['offset']
    if offset in checked:
        continue
    checked.add(offset)
    mode, = struct.unpack_from('<H', atlas, offset)
    at = offset+2
    if mode == 0:
        values = list(struct.unpack_from('<4096H', atlas, at))
    else:
        assert mode == 1
        values = []
        while len(values) < 4096:
            n, color = struct.unpack_from('<HH', atlas, at); at += 4
            assert n > 0 and len(values)+n <= 4096
            values.extend([color]*n)
    url = row['url']
    source = ROOT / 'assets/imported/rocket-user/bond-sprites' / url.split('/')[-1] if url.startswith('/rocket-art/') else ROOT / '.cache/gba-art' / (hashlib.sha256(url.encode()).hexdigest()+'.img')
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['source_sha256']
    image = Image.open(io.BytesIO(data)).convert('RGBA')
    if row.get('kind') == 'portrait':
        bounds = image.getchannel('A').point(lambda a:255 if a>=96 else 0).getbbox()
        if bounds: image = image.crop(bounds)
        image.thumbnail((56,56), Image.Resampling.NEAREST)
    else:
        image.thumbnail((64,64), Image.Resampling.LANCZOS if image.width>128 else Image.Resampling.NEAREST)
    expected = Image.new('RGBA',(64,64))
    expected.alpha_composite(image,((64-image.width)//2,(64-image.height)//2))
    for actual,(r,g,b,a) in zip(values,expected.get_flattened_data()):
        assert actual == (0x8000 if a<96 else (r//8)+(g//8)*32+(b//8)*1024), url
print(f'PASS: {len(checked)} unique sprite payloads losslessly round-trip to their pinned RGB555 source images')
