"""Reject stationary gait sheets and source-to-ROM pixel changes."""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from summit_sprites import frames
from build_opening_stages import get

audit = {a['actor']: a for a in json.loads((ROOT/'build/pallet/opening-sprite-audit.json').read_text())}
blob = (ROOT/'build/pallet/opening_stage.bin').read_bytes()
actors = ['steven','cynthia','karen','alder','diantha','leon','geeta']
for actor in actors:
    record = audit[actor]
    assert record['layout'] == 'cardinal_gait' and record['frames'] == 12
    images = frames(actor, get)
    for face in range(4):
        poses = images[face*3:face*3+3]
        assert len({f.tobytes() for f in poses}) == 3, (actor, face, 'missing stride')
    assert images[0].tobytes() != images[3].tobytes(), (actor, 'false rear view')
    encoded = b''.join(struct.pack('<H',0x8000 if a<128 else (r>>3)|((g>>3)<<5)|((b>>3)<<10))
                       for f in images for r,g,b,a in f.get_flattened_data())
    assert blob[record['offset']:record['offset']+len(encoded)] == encoded, actor
print('PASS: 7 cardinal gait sheets, 84 compiled source-exact frames, two distinct strides per direction')
