"""Finalize the standard GBA cartridge header and record the actual build size."""
from pathlib import Path
import hashlib,json
p=Path('build/gba/omni-dex.gba')
b=bytearray(p.read_bytes())
for asset in ('art.bin','font.bin'):
    assert Path('build/gba',asset).read_bytes() in b, 'Linked ROM contains stale embedded asset: '+asset
b[4:0xa0]=bytes.fromhex('24ffae51699aa2213d84820a84e409ad11248b98c0817f21a352be199309ce2010464a4af82731ec58c7e83382e3cebf85f4df94ce4b09c194568ac01372a7fc9f844d73a3ca9a615897a327fc039876231dc7610304ae56bf38840040a70efdff52fe036f9530f197fbc08560d68025a963be03014e38e2f9a234ffbb3e0344780090cb88113a9465c07c6387f03cafd625e48b380aac7221d4f807')
b[0xa0:0xac]=b'OMNI DEX    '
b[0xac:0xb0]=b'OMDE'
b[0xb0:0xb2]=b'00'
b[0xb2]=0x96
b[0xb3:0xbd]=bytes(10)
b[0xbd]=(-sum(b[0xa0:0xbd])-0x19)&255
assert len(b)<=32*1024*1024
# Pad to the next MiB, with erased-ROM bytes, rather than pretending to fill 32 MiB.
b+=bytes([255])*((-len(b))%(1024*1024))
p.write_bytes(b)
report={'rom':p.as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'header_checksum_valid':((-sum(b[0xa0:0xbd])-0x19)&255)==b[0xbd],'scope':'Standalone GBA Pokedex integration cartridge, not the full world game.'}
Path('build/gba/build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
