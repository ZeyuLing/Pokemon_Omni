"""Recover duplicated source pixels; reject any interpolation or recoloring."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def native_portrait(actor):
    manifest = json.loads((ROOT / 'assets/source/fireash-cast.json').read_text('utf-8'))
    record = next(r for r in manifest['sprites'] if r['actor'] == actor)
    source = ROOT / record['source_path']
    if hashlib.sha256(source.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Fire Ash source changed: ' + actor)
    image = Image.open(source).convert('RGBA')
    assert list(image.size) == record['source_canvas']
    assert list(image.getbbox()) == record['native_bounds']
    x0, y0, x1, y1 = record['native_bounds']
    scale = record['pixel_replication']
    assert (x1 - x0) % scale == (y1 - y0) % scale == 0
    native = Image.new('RGBA', tuple(record['native_size']))
    for y in range(native.height):
        for x in range(native.width):
            block = [image.getpixel((x0+x*scale+dx, y0+y*scale+dy))
                     for dy in range(scale) for dx in range(scale)]
            block = [p if p[3] else (0, 0, 0, 0) for p in block]
            if len(set(block)) != 1:
                raise ValueError('Source is not an exact replicated pixel grid')
            native.putpixel((x, y), block[0])
    assert hashlib.sha256(native.tobytes()).hexdigest() == record['native_rgba_sha256']
    output = ROOT / record['output']
    output.parent.mkdir(parents=True, exist_ok=True)
    native.save(output)
    return native
