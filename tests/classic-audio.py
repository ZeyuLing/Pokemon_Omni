"""Compare music captured from the actual ROM to its archived source mix.

Run after presentation-rom.cjs. Checks wave content AND exact time progression
across two musical loops, detecting FIFO ring corruption and dropped blocks.
"""
import json,wave
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
out=root/'build/pallet'
manifest=json.loads((root/'assets/source/classic-audio.json').read_text('utf8'))
clip=next(t for t in manifest['tracks'] if t['name']=='pallet')
meta=json.loads((out/'music-loop.json').read_text())
with wave.open(str(root/'build/audio/pallet-preview.wav'),'rb') as w:
    assert w.getframerate()==16384
    ref=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)
stereo=np.fromfile(out/'music-loop.pcm',dtype='<i2').reshape(-1,2)
assert meta['rate']==32768
pcm=stereo.mean(axis=1)[::2];ref-=ref.mean()
power=np.r_[0,np.cumsum(ref*ref)]
nfft=1<<int(np.ceil(np.log2(len(ref)+16384-1)))
fr=np.fft.rfft(ref,nfft);rows=[]
loop_start=clip['loop_start_block']*256
loop_length=(clip['blocks']-clip['loop_start_block'])*256
for second in [0,1,10,20,30,40,44,50,59]:
    x=pcm[second*16384:(second+1)*16384];x=x-x.mean();n=len(x)
    dots=np.fft.irfft(fr*np.conj(np.fft.rfft(x,nfft)),nfft)[:len(ref)-n+1]
    score=dots/np.sqrt((power[n:]-power[:-n])*np.dot(x,x)+1e-12)
    at=int(np.argmax(score));correlation=float(score[at])
    assert correlation>.95, f'Source music corrupted: {second}s, correlation {correlation}'
    expected=at if not rows else loop_start+(rows[0]['reference_sample']+second*16384-loop_start)%loop_length
    assert abs(at-expected)<=1,f'Audio dropped/duplicated samples at {second}s: {at-expected}'
    rows.append({'second':second,'reference_sample':at,'correlation':correlation,'phase_error_samples':at-expected})
assert meta['end']['loops']>meta['start']['loops']
report={'source_rom_sha256':manifest['source_rom_sha256'],'rate':16384,'windows':rows,'minimum_correlation':min(r['correlation'] for r in rows),'scope':'Actual ROM Pallet playback, post ADPCM and 8-bit DAC; selected windows through 60 seconds. Not a subjective listening review.'}
(out/'audio-correlation.json').write_text(json.dumps(report,indent=2)+'\n')
with wave.open(str(out/'music-in-game.wav'),'wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(meta['rate']);w.writeframes(stereo[:12*meta['rate']].tobytes())
print(f'PASS: classic source correlation >= {report["minimum_correlation"]:.3f}; exact sample phase across 60 seconds and looping')
