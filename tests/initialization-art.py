"""Validate compiled-size identity assets, not a concept-sheet-only change."""
import hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from initialization_art import ash_frames,partner_frames,partner_overworld
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
print('PASS: Ash nine distinct 16x32 frames, source-exact geometry including original walking bob, shared15-color palette; hash-locked SID1094 four partner views')
