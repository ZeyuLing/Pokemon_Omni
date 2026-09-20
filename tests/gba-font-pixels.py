"""Compare rendered Chinese text against the pinned BDF, without generated indices."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
source = zipfile.ZipFile(root / '.cache/toolchains/fusion-pixel-12px-2026.09.01.zip').read('fusion-pixel-12px-monospaced-zh_hans.bdf').decode()
blocks = {}
for block in source.split('STARTCHAR ')[1:]:
    lines = block.splitlines()
    fields = {line.split()[0]:line.split()[1:] for line in lines if line and line!='BITMAP'}
    blocks[int(fields['ENCODING'][0])] = (fields,lines)
pixels = (root / 'build/pallet/dex-evolution.rgba').read_bytes()
x = 8
for char in '进化路线与条件':
    fields,lines = blocks[ord(char)]
    advance = int(fields['DWIDTH'][0])
    w,h,left,bottom = map(int,fields['BBX'])
    rows = [bytes.fromhex(row) for row in lines[lines.index('BITMAP')+1:lines.index('ENDCHAR')]]
    for y in range(12):
        for dx in range(advance):
            sx,sy = dx-left,y-(10-h-bottom)
            expected = 0<=sx<w and 0<=sy<h and bool(rows[sy][sx//8] & (128>>(sx%8)))
            actual = pixels[((y+4)*240+x+dx)*4]>>3 == 7
            assert actual == expected, (char,dx,y)
    x += advance
print('PASS: actual ARM ROM Chinese header pixels match the pinned 12px BDF')
