"""Prepare native movement sources for every rule-qualified default species.

Downloads are cache-only. Missing sources stay explicit, never replaced with another
species or counted as visual acceptance. Alternate forms are a separate backlog.
"""
import concurrent.futures
import io
import json
from pathlib import Path
from PIL import Image
from build_travel_assets import fetch, ROOT, REV
from riding_art import layout_review


def prepare(profile):
    number, name = profile['species'], profile['identifier']
    aliases = {'giratina': 'giratina', 'shaymin': 'shaymin', 'landorus': 'landorus',
               'tornadus': 'tornadus', 'thundurus': 'thundurus'}
    name = aliases.get(name, name.replace('-', '_'))
    result = dict(species=number, name=name, eligible=profile['eligible'], status='missing',
                  visual_review=layout_review(number), rider_pose='full_native_ash_seated')
    try:
        data = fetch(name, 'overworld.png')
        palette = fetch(name, 'overworld_normal.pal')
        im = Image.open(io.BytesIO(data))
        assert im.mode == 'P' and im.width in (im.height * 6, im.height * 8) and im.height <= 64, ('layout', im.size, im.mode)
        assert len(palette.decode().splitlines()[3:19]) == 16
        assert max(im.get_flattened_data()) < 16
        icon=Image.open(io.BytesIO(fetch(name,'icon.png')))
        assert icon.size==(32,64) and icon.mode=='P'
        result.update(status='native_source_prepared', cell=im.height, party_icon='native_32x64_two_frames')
    except Exception as error:
        result['error'] = str(error)
    return result


def main():
    profiles = json.loads((ROOT/'content/travel/generated/profiles.json').read_text('utf8'))['profiles']
    required = {1,4,7,25,16,19,109,13,111,59,128,131}
    # Retain already prepared followers when a riding safety review rejects them.
    previous = ROOT/'assets/source/travel-roster.json'
    if previous.exists():
        required.update(r['species'] for r in json.loads(previous.read_text('utf8'))['species'])
    selected = [p for p in profiles if p['eligible'] or p['species'] in required]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(prepare, selected))
    from build_travel_assets import records
    result = dict(repository='https://github.com/rh-hideout/pokeemerald-expansion', commit=REV,
                  scope='Default-form riding candidates; technical source preparation, not visual acceptance',
                  species=rows, files=sorted(records.values(), key=lambda r:r['path']))
    (ROOT/'assets/source/travel-roster.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', 'utf8')
    print(json.dumps(dict(requested=len(rows), prepared=sum(r['status']=='native_source_prepared' for r in rows),
                         missing=[r for r in rows if r['status']=='missing']), ensure_ascii=False))


if __name__ == '__main__':
    main()
