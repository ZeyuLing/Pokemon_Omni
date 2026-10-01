"""Import cardinal gait sheets without resampling or per-frame recentering."""
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def records():
    return json.loads((ROOT / 'assets/source/overworld-repair.json').read_text('utf-8'))['sprites']


def source_frames(actor):
    spec = next(s for s in records() if s['actor'] == actor)
    path = ROOT / spec['path']
    if not path.exists():
        if spec.get('url'):
            data = urllib.request.urlopen(spec['url'], timeout=30).read()
        elif spec.get('archive_bytes'):
            from import_fireash_cast import ArchiveRanges
            with zipfile.ZipFile(ArchiveRanges(spec['archive_url'], spec['archive_bytes'])) as archive:
                data = archive.read(spec['entry'])
        else:
            raw = urllib.request.urlopen(spec['archive_url'], timeout=40).read()
            assert hashlib.sha256(raw).hexdigest() == spec['archive_sha256']
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                data = archive.read(spec['entry'])
        assert hashlib.sha256(data).hexdigest() == spec['sha256']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['sha256']
    sheet = Image.open(path).convert('RGBA')
    sheet.putdata([p if p[3] else (0, 0, 0, 0) for p in sheet.get_flattened_data()])
    assert sheet.width % 4 == sheet.height % 4 == 0
    w, h = sheet.width // 4, sheet.height // 4
    scale = spec['replication']; px, py = spec['phase']
    assert w % scale == h % scale == 0
    frames = []
    for row in spec['rows']:
        for col in spec['poses']:
            # A fixed grid phase removes only transparent leading margins.
            full = sheet.crop((col*w, row*h, (col+1)*w, (row+1)*h))
            bounds = full.getbbox()
            assert bounds and bounds[0] >= px and bounds[1] >= py
            cell = full.crop((px, py, px+w, py+h))
            native = Image.new('RGBA', (w//scale, h//scale))
            for y in range(native.height):
                for x in range(native.width):
                    block = {cell.getpixel((x*scale+dx, y*scale+dy))
                             for dy in range(scale) for dx in range(scale)}
                    assert len(block) == 1, 'Non-native/interpolated source pixel block'
                    native.putpixel((x, y), block.pop())
            frames.append(native)
    # The SAME offset for every pose preserves authored stride/bob and bearings.
    bottom = max(f.getbbox()[3] for f in frames)
    dy = 31 - bottom
    result = []
    for f in frames:
        b = f.getbbox(); assert b[1]+dy >= 0 and b[3]+dy <= 32 and f.width <= 32
        canvas = Image.new('RGBA', (32, 32))
        canvas.paste(f, ((32-f.width)//2, dy))
        result.append(canvas)
    assert result[0].tobytes() != result[3].tobytes(), 'Rear is a duplicate of front'
    for face in range(4):
        assert len({f.tobytes() for f in result[face*3:face*3+3]}) == 3, 'Missing stride pose'
    return result
