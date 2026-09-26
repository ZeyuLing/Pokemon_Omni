"""Compile classic FireRed title layers; never bake a screenshot into the ROM.

The native logo/Charizard tilemap positions are preserved. The version lettering
and backdrop are adapted for Omni. Source downloads stay local.
"""
import hashlib
import json
import struct
import urllib.request
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/pallet'
CACHE = ROOT/'.cache/title-source'
REV = 'c75f352304d529f6ba92d4f74b9cf8b5c3810788'
FILES = ['firered/background.pal',
         'firered/game_title_logo.png', 'firered/game_title_logo.pal', 'firered/game_title_logo.bin',
         'firered/box_art_mon.png', 'firered/box_art_mon.pal', 'firered/box_art_mon.bin',
         'copyright_press_start.png', 'copyright_press_start.bin']

def sha(b): return hashlib.sha256(b).hexdigest()

def layer(png, tilemap, palette, remove_version=False):
    tiles = Image.open(CACHE/png)
    colors = [tuple(map(int, s.split()))+(255,) for s in (CACHE/palette).read_text().splitlines()[3:]]
    out = Image.new('RGBA', (256, 256))
    for n, (entry,) in enumerate(struct.iter_unpack('<H', (CACHE/tilemap).read_bytes())):
        tile = entry & 1023
        for y in range(8):
            for x in range(8):
                sx = tile % (tiles.width//8)*8 + (7-x if entry & 1024 else x)
                sy = tile // (tiles.width//8)*8 + (7-y if entry & 2048 else y)
                # Version tiles occupy the rightmost 80 columns of the sheet.
                if remove_version and sx >= 176: continue
                index = tiles.getpixel((sx, sy))
                # gbagfx main.c passes !image.hasPalette to ConvertToTiles4Bpp.
                if tiles.mode == 'L': index = 15-index//17
                if index: out.putpixel((n%32*8+x, n//32*8+y), colors[index])
    return out.crop((0, 0, 240, 160))

def wordmark():
    # Authored block letters at native resolution, white fill and stepped edge.
    letters = ['01110/10001/10001/10001/10001/10001/01110',
               '10001/11011/10101/10101/10001/10001/10001',
               '10001/11001/11001/10101/10011/10011/10001',
               '01110/00100/00100/00100/00100/00100/01110']
    mask = Image.new('L', (89, 29))
    for n, letter in enumerate(letters):
        for y, row in enumerate(letter.split('/')):
            for x, c in enumerate(row):
                if c == '1':
                    for yy in range(3):
                        for xx in range(3): mask.putpixel((4+n*21+x*3+xx+(6-y)//2, 4+y*3+yy), 255)
    out = Image.new('RGBA', mask.size)
    out.paste((24, 24, 32, 255), (0, 0), mask.filter(ImageFilter.MaxFilter(5)))
    out.paste((255, 255, 255, 255), (0, 0), mask)
    return out

def main():
    records = []
    manifest_path = ROOT/'assets/source/title-screen.json'
    prior = json.loads(manifest_path.read_text('utf8')) if manifest_path.exists() else None
    for f in FILES:
        p = CACHE/f; p.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://raw.githubusercontent.com/pret/pokefirered/{REV}/graphics/title_screen/{f}'
        if not p.exists(): p.write_bytes(urllib.request.urlopen(url, timeout=30).read())
        records.append({'path': f, 'url': url, 'sha256': sha(p.read_bytes())})
    if prior:
        for old in prior['sources']: assert old in records, 'Title source hash changed'
    image = Image.new('RGBA', (240, 160), (0, 0, 0, 255))
    for png, tm, pal, logo in [('firered/box_art_mon.png', 'firered/box_art_mon.bin', 'firered/box_art_mon.pal', False),
                             ('firered/game_title_logo.png', 'firered/game_title_logo.bin', 'firered/game_title_logo.pal', True)]:
        image.alpha_composite(layer(png, tm, pal, logo))
    image.alpha_composite(wordmark(), (40, 61))
    prompt = layer('copyright_press_start.png', 'copyright_press_start.bin', 'firered/background.pal')
    OUT.mkdir(exist_ok=True, parents=True)
    prompt.save(OUT/'title-prompt-layout.png')
    # Preserve the source PRESS START pixels, but not its original release date.
    press = prompt.crop((40,128,136,136))
    blob = b''.join(struct.pack('<H', (r>>3) | ((g>>3)<<5) | ((b>>3)<<10)) for r,g,b,a in image.get_flattened_data())
    blob += b''.join(struct.pack('<H', 0x8000 if not a else (r>>3) | ((g>>3)<<5) | ((b>>3)<<10)) for r,g,b,a in press.get_flattened_data())
    OUT.mkdir(exist_ok=True, parents=True)
    image.save(OUT/'title-art.png'); (OUT/'title.bin').write_bytes(blob)
    (OUT/'title.s').write_text(f'/* SHA256 {sha(blob)} */\n.section .rodata\n.balign 4\n.global omni_title_pixels\nomni_title_pixels:\n.incbin "build/pallet/title.bin"\n')
    manifest = {'sources': records, 'adaptation': 'FireRed logo, Charizard and PRESS START at native tilemap positions; authored OMNI version wordmark and black backdrop. FireRed intro effects are not ported. Not the Rocket hack cover or final commissioned Omni cover art.',
                'credits': 'Original Pokémon graphics: Game Freak / Nintendo / Creatures; extraction reference: pret/pokefirered.',
                'size': [240,160], 'bytes': len(blob), 'sha256': sha(blob)}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', 'utf8')
    print(f'Title: {len(blob)} bytes, {len(records)} pinned source files')

if __name__ == '__main__': main()
