"""Import the archived Rocket field dialogue, including its Chinese glyphs.

The table reference describes encoding only. Every rendered glyph and frame
pixel is read from the user's hash-locked ROM, including local modifications.
"""
import hashlib
import json
import struct
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image
from extract_rocket_rom import USER_SHA
from build_game_ui_assets import tile_image, colors

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/pallet'
TABLE_REV = '5a78e4da2cf61fbe7b7e64b110accc06cdee800b'
TABLE_PATH = 'old_(PMxxUS_CHPLUS_RELEASE)/PMEMUS_CHPLUS_RELEASE2/PMEMUS_CHPLUS_RELEASE2_TBL.txt'
TABLE_URL = 'https://raw.githubusercontent.com/Wokann/Pokemon_GBA_Font_Patch/'+TABLE_REV+'/'+urllib.parse.quote(TABLE_PATH)
CHINESE = 0x1d3612c
LATIN = 0xd34c28
PUNCT = {' ':0,'。':0xad,'，':0xb8,'、':0xb8,'！':0xab,'？':0xac,'：':0xf0,
         '…':0xb0,'—':0xae,'·':0xaf,'“':0xb1,'”':0xb2,'（':0x5c,'）':0x5d}

def digest(b): return hashlib.sha256(b).hexdigest()

def charset():
    p=ROOT/'.cache/rocket-font-reference'/TABLE_PATH
    if not p.exists():
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(urllib.request.urlopen(TABLE_URL,timeout=30).read())
    raw=p.read_bytes(); mapping={}
    for line in raw.decode('gbk').splitlines():
        code,char=line.split('=',1)
        if char==' ':continue
        high,low=int(code[:2],16),int(code[2:],16)
        bank=high-1-(high>6)-(high>0x1b)
        mapping[char]=CHINESE+(bank*256+low)*64
    mapping.update({char:LATIN+index*64 for char,index in PUNCT.items()})
    for first,count,code in [('0',10,0xa1),('A',26,0xbb),('a',26,0xd5)]:
        mapping.update({chr(ord(first)+i):LATIN+(code+i)*64 for i in range(count)})
    return mapping,raw

def glyph_pixels(rom,offset):
    return [[(struct.unpack_from('<H',rom,offset+(y//8*2+x//8)*16+y%8*2)[0]>>(14-2*(x%8)))&3 for x in range(16)] for y in range(16)]

def width(char):
    return 12 if '\u4e00'<=char<='\u9fff' or char=='。' else 6

def wrap(text,max_width=204):
    """Source-sized lines; punctuation stays with the preceding phrase."""
    result=[];line='';used=0
    for char in text:
        if char=='\n':result.append(line);line='';used=0;continue
        w=width(char)
        if used+w>max_width:
            if char in '。，、！？：…' and line:
                tail=line[-1];result.append(line[:-1]);line=tail;used=width(tail)
            else:result.append(line);line='';used=0
        line+=char;used+=w
    result.append(line)
    return result

def main():
    rom=(ROOT/'assets/imported/rocket-user/rocket-user-modifier.gba').read_bytes()
    assert digest(rom)==USER_SHA
    mapping,table=charset()
    opening=json.loads((ROOT/'content/opening/prologue.json').read_text('utf-8'))
    strings=[]
    for scene in opening['scenes']:
        strings.append(scene['title'])
        for beat in scene['beats']: strings.extend([beat.get('speaker',''),*beat.get('lines',[])])
    # Test phrase from the real ROM's opening, used for pixel verification.
    strings+=['本版本只在西班牙火箭队吧','进行更新发布。','跳过这段开场？','A跳过 B继续','第一次世界大战末期','翌晨 · 真新镇','：']
    chars=sorted(set(''.join(strings))-{'\n'})
    missing=[c for c in chars if c not in mapping]
    assert not missing, 'No silent substitute for missing source glyphs: '+repr(missing)
    blob=bytearray();rows=[];glyphs=[]
    for c in chars:
        off=mapping[c];data=rom[off:off+64]
        if c=='。':
            # This translation uses the small circle glyph, not Latin '.'.
            # Its two 8x8 tiles live in the source Japanese font bank. Preserve
            # the observed two-pixel left inset in a standard 16x16 glyph slot.
            pixels=[[0]*16 for _ in range(16)]
            for y in range(16):
                v=struct.unpack_from('<H',rom,0xd422f8+(256 if y>=8 else 0)+y%8*2)[0]
                for x in range(8):pixels[y][x+2]=(v>>(14-2*x))&3
            data=b''.join(struct.pack('<H',sum(pixels[ty+y][tx+x]<<(14-2*x) for x in range(8))) for ty,tx in ((0,0),(0,8),(8,0),(8,8)) for y in range(8))
        offset=len(blob);blob+=data
        rows.append('{'+f'{ord(c)},{width(c)},{offset}'+'}')
        glyphs.append({'char':c,'codepoint':ord(c),'rom_offset':hex(off) if c!='。' else ['0xd422f8','0xd423f8'],'width':width(c),'sha256':digest(data)})
    # Source menu.c DrawDialogueFrame: window (2,15), 27x4 tiles.
    pal=colors(rom[0xb6a438:0xb6a438+32])
    tiles=tile_image(rom[0x1cd0c4c:0x1cd0c4c+448],56,16,pal,transparent=True)
    frame=Image.new('RGBA',(240,48))
    for y in range(6):
        for x in range(30):
            index=([1,3]+[4]*26+[5,6])[x] if y in (0,5) else (7 if x==0 else 10 if x==29 else 9)
            t=tiles.crop((index%7*8,index//7*8,index%7*8+8,index//7*8+8))
            if y==5:t=t.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            frame.paste(t,(x*8,y*8))
    frame_offset=len(blob)
    for r,g,b,a in frame.get_flattened_data():blob+=struct.pack('<H',0x8000 if not a else (r>>3)|((g>>3)<<5)|((b>>3)<<10))
    arrow=tile_image(rom[0x53110c:0x53110c+192],8,48,pal,transparent=True).crop((0,0,8,16))
    arrow_offset=len(blob)
    for r,g,b,a in arrow.get_flattened_data():blob+=struct.pack('<H',0x8000 if not a else (r>>3)|((g>>3)<<5)|((b>>3)<<10))
    OUT.mkdir(parents=True,exist_ok=True);frame.save(OUT/'rocket-dialogue-frame.png');arrow.save(OUT/'rocket-dialogue-arrow.png')
    (OUT/'rocket_text.bin').write_bytes(blob)
    (OUT/'rocket_text.s').write_text(f'/* SHA256 {digest(blob)} */\n.section .rodata\n.balign 4\n.global omni_rocket_text_blob\nomni_rocket_text_blob:\n.incbin "build/pallet/rocket_text.bin"\n')
    (OUT/'rocket_text.h').write_text('''#ifndef OMNI_ROCKET_TEXT_H
#define OMNI_ROCKET_TEXT_H
#include <stdint.h>
typedef struct {uint16_t code,width;uint32_t offset;} OmniRocketGlyph;
extern const OmniRocketGlyph omni_rocket_glyphs[];
extern const unsigned char omni_rocket_text_blob[];
'''+f'#define OMNI_ROCKET_GLYPHS {len(rows)}\n#define OMNI_ROCKET_FRAME {frame_offset}\n#define OMNI_ROCKET_ARROW {arrow_offset}\n#endif\n')
    (OUT/'rocket_text.c').write_text('#include "rocket_text.h"\nconst OmniRocketGlyph omni_rocket_glyphs[]={'+','.join(rows)+'};\n')
    manifest={'rom_sha256':USER_SHA,'table':{'url':TABLE_URL,'sha256':digest(table),'purpose':'Encoding reference, not substituted font artwork'},'chinese_bank':hex(CHINESE),'latin_bank':hex(LATIN),'frame_tiles':'0x1cd0c4c','palette':'0xb6a438','arrow':'0x53110c','layout':{'window':[0,112,240,48],'text_origin':[16,121],'line_step':14,'foreground_rgb555':[12,12,12],'shadow_rgb555':[26,26,25],'speaker':'inline prefix; no separate name box'},'glyphs':glyphs,'blob_sha256':digest(blob),'bytes':len(blob)}
    target=ROOT/'assets/source/rocket-dialogue.json'
    if target.exists():assert json.loads(target.read_text('utf8'))['table']['sha256']==digest(table)
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
    print(f'Rocket dialogue: {len(chars)} source glyphs, {len(blob)} bytes')

if __name__=='__main__': main()
