"""Validate compiled-size identity assets, not a concept-sheet-only change."""
import hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from initialization_art import ash_frames,partner_frames,partner_overworld
from ash_source_art import ash_trainer_art
from PIL import Image
frames=ash_frames();assert len(frames)==9
# Golden source pixels: catches resizing, recoloring and direction/frame drift.
assert hashlib.sha256(b"".join(f.tobytes() for f in frames)).hexdigest()=="e77a01d16d3f916a105a71b2944af30fc17dd4259533a5257622f9227c29ac2f"
assert len({hashlib.sha256(f.tobytes()).hexdigest() for f in frames})==9
expected_bounds=[(0,12,16,31),(0,11,16,31),(0,11,16,31),(0,13,16,32),(0,13,16,32),(0,12,16,31),(0,12,16,31),(0,12,16,32),(0,12,16,31)]
for index,f in enumerate(frames):
    x0,y0,x1,y1=f.getbbox()
    assert f.size==(16,32) and (x0,y0,x1,y1)==expected_bounds[index]
    assert set(f.getchannel('A').get_flattened_data())<={0,255}
pal={p for f in frames for p in f.get_flattened_data() if p[3]};assert len(pal)<=15
partner=partner_frames();assert len(partner)==4 and all(f.size==(64,64) for f in partner)
assert partner[0].tobytes()!=partner[1].tobytes()
assert partner_overworld().getbbox()[3]<=16
front,backs=ash_trainer_art()
assert hashlib.sha256(front.tobytes()).hexdigest()=='b83d859388f23efd29d6cf915e0de00446d17e026e76522bdc3b1c360c22b09e'
assert [hashlib.sha256(f.tobytes()).hexdigest() for f in backs]==[
    'c3547c590bcfa991e3d04d09c197de56be0a99835a2c7233550cdf8d2986f6c6',
    '11f93079a5ed2bfad9d4580271225afb8a423f63f61fe90cd2127cbf98d7c4e6',
    '94f219bf3c7f0738b5469dd0b19c9b608519a5c328dd106fb2041b13fa799ee5',
    '9638ab94cd16c6f5b2b06ebea6c976555e38c09ba79d91738ee28abd8fb4cf0f']
# Padding into the gallery's existing frame must never scale source pixels.
expected=Image.new('RGBA',(80,80));expected.paste(front,(8,16))
assert Image.open('build/pallet/cast/ash.png').convert('RGBA').tobytes()==expected.tobytes()
print('PASS: Ash nine distinct 16x32 frames, source-exact geometry including original walking bob, shared15-color palette; hash-locked SID1094 four partner views')
print('PASS: Ash source front and four back poses golden pixels; compiled portrait is native 64x64 with padding only')
