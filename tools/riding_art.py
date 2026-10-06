"""Native seated Ash, plus explicit per-species saddle/foreground layouts.

All artwork is decoded from locked sources; no generated illustration, resizing,
recoloring or standing-torso substitution. Layout coordinates use source pixels.
"""
import hashlib
import json
import struct
from PIL import Image
from ash_source_art import ROOT, ROM, SHA, PALETTE
from build_game_ui_assets import tile_image, colors

INFO, TABLE = 0x5099c0, 0x505c3c


def seated_frames():
    rom = (ROOT/ROM).read_bytes()
    assert hashlib.sha256(rom).hexdigest() == SHA
    assert struct.unpack_from('<HH',rom,INFO+8)==(32,32)
    assert struct.unpack_from('<I',rom,INFO+28)[0]==TABLE+0x08000000
    frames, records = [], []
    for index in range(3):
        pointer,size=struct.unpack_from('<II',rom,TABLE+index*8)
        offset=pointer-0x08000000
        assert size==512
        frame=tile_image(rom[offset:offset+size],32,32,colors(rom[PALETTE:PALETTE+32]))
        frames.append(frame)
        records.append(dict(index=index,offset=offset,bytes=size,bbox=frame.getbbox(),rgba_sha256=hashlib.sha256(frame.tobytes()).hexdigest()))
    frames.append(frames[2].transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    manifest=dict(source='User Emerald IV Ash ROM; same XY outfit as current walking sprite',
        rom=ROM,rom_sha256=SHA,graphics_info=INFO,frame_table=TABLE,palette=PALETTE,
        frames=records,right='Source-engine horizontal mirror of left',
        conversion='Full native 32x32 seated frames; no crop, recolor, resize or torso truncation',
        scope='Seated rider; reuse of surfing pose does not grant Surf traversal',
        provenance='BrendanSurfing graphics slot replaced by Ash in user ROM; not renamed Brendan/Red artwork',
        distribution='ROM and decoded images stay local')
    (ROOT/'assets/source/ash-iv-seated.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
    return frames


def mount_layout(species, frames, box):
    record=json.loads((ROOT/'assets/characters/riding-layouts.json').read_text('utf8'))['species'][str(species)]
    assert len(record['poses'])==8
    for direction in range(4):
        a,b=[p['seat'] for p in record['poses'][direction*2:direction*2+2]]
        assert abs(a[0]-b[0])<=2 and abs(a[1]-b[1])<=2, (species,'unstable saddle across gait')
    rows=[]
    for frame,pose in zip(frames,record['poses']):
        x,y=pose['seat'];l,t,r,b=pose['foreground']
        assert 0<=x<frame.width and 0<=y<frame.height
        # Saddle must touch the native body near the authored point.
        assert any(frame.getpixel((xx,yy))[3] for yy in range(max(0,y-2),min(frame.height,y+3)) for xx in range(max(0,x-2),min(frame.width,x+3))), (species,pose,'floating saddle')
        rows.append([x-box[0],y-box[1],l-box[0],t-box[1],r-box[0],b-box[1]])
    return rows


def layout_review(species):
    return json.loads((ROOT/"assets/characters/riding-layouts.json").read_text("utf8"))["species"][str(species)]["review"]
