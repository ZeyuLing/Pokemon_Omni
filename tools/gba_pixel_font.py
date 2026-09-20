"""Pinned 12px bitmap face for the Dex; retain 16px world/dialogue glyphs."""
import hashlib
import urllib.request
import zipfile

FONT_URL = 'https://github.com/TakWolf/fusion-pixel-font/releases/download/2026.09.01/fusion-pixel-font-12px-monospaced-bdf-v2026.09.01.zip'
FONT_SHA = '5b1cac9253fa9e20b9fea5fd582eeed985819a3ce4b7f7fb108f8d6e599ad211'


def load_pixel_glyphs(root, characters):
    path = root / '.cache/toolchains/fusion-pixel-12px-2026.09.01.zip'
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(FONT_URL, timeout=60).read())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == FONT_SHA, 'Pixel font hash mismatch'
    archive = zipfile.ZipFile(path)
    source = archive.read('fusion-pixel-12px-monospaced-zh_hans.bdf').decode()
    glyphs = {}
    for block in source.split('STARTCHAR ')[1:]:
        lines = block.splitlines()
        fields = {line.split()[0]:line.split()[1:] for line in lines if line and line != 'BITMAP'}
        code = int(fields['ENCODING'][0])
        if code < 32 or chr(code) not in characters:
            continue
        advance = int(fields['DWIDTH'][0])
        w,h,x,y = map(int,fields['BBX'])
        rows = lines[lines.index('BITMAP')+1:lines.index('ENDCHAR')]
        pixels = [[0]*advance for _ in range(12)]
        for ry,row in enumerate(rows):
            bits = bytes.fromhex(row)
            for rx in range(w):
                tx,ty = x+rx,10-h-y+ry
                if 0 <= tx < advance and 0 <= ty < 12 and bits[rx//8] & (128>>(rx%8)):
                    pixels[ty][tx] = 1
        stride = (advance+7)//8
        data = bytearray(12*stride)
        for yy,row in enumerate(pixels):
            for xx,value in enumerate(row):
                if value: data[yy*stride+xx//8] |= 128>>(xx%8)
        glyphs[code] = (advance,bytes(data))
    missing = sorted(ord(c) for c in characters if ord(c)>=32 and ord(c) not in glyphs)
    if missing: raise ValueError(f'12px font missing glyphs: {missing}')
    return glyphs
