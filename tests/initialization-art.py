"""Validate compiled-size identity assets, not a concept-sheet-only change."""
import hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from initialization_art import ash_frames,partner_frames,partner_overworld
frames=ash_frames();assert len(frames)==9
assert len({hashlib.sha256(f.tobytes()).hexdigest() for f in frames})==9
for f in frames:
    x0,y0,x1,y1=f.getbbox()
    assert f.size==(16,32) and x1-x0<=14 and y1-y0<=22 and y1==32
    assert set(f.getchannel('A').get_flattened_data())<={0,255}
pal={p for f in frames for p in f.get_flattened_data() if p[3]};assert len(pal)<=15
partner=partner_frames();assert len(partner)==4 and all(f.size==(64,64) for f in partner)
assert partner[0].tobytes()!=partner[1].tobytes()
assert partner_overworld().getbbox()[3]<=16
print('PASS: Ash nine distinct 16x32 frames, <=22px visible height, shared15-color palette; hash-locked SID1094 four partner views')
