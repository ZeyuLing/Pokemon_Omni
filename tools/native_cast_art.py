"""Compile editable native pixel rows, with no resizing or palette reduction."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def pixel_portrait(actor):
    source = ROOT / 'assets/characters/pixel' / (actor + '.json')
    data = json.loads(source.read_text('utf-8'))
    assert data['actor'] == actor and data['size'] == [80, 80]
    assert len(data['rows']) == 80 and all(len(row) == 80 for row in data['rows'])
    assert len(data['palette']) <= 16 and data['palette']['.'] is None
    palette = {key: (0, 0, 0, 0) if value is None else
               (*bytes.fromhex(value.removeprefix('#')), 255)
               for key, value in data['palette'].items()}
    assert all(len(value) == 4 for value in palette.values())
    image = Image.new('RGBA', (80, 80))
    image.putdata([palette[pixel] for row in data['rows'] for pixel in row])
    out = ROOT / 'build/pallet/native-cast' / (actor + '.png')
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return image


if __name__ == '__main__':
    for source in sorted((ROOT / 'assets/characters/pixel').glob('*.json')):
        image = pixel_portrait(source.stem)
        image.resize((320, 320), Image.Resampling.NEAREST).save(
            ROOT / 'build/pallet/native-cast' / (source.stem + '-review.png'))
