"""Build music from the user's hash-locked Rocket ROM, using its own engine.

Melodies are checked against pinned FireRed MIDI data. The archived ROM is
never modified. Patched reference players and rendered audio stay in build/.
The game uses compact independently decodable mono IMA-ADPCM blocks.
"""
import hashlib,json,math,struct,subprocess,sys,urllib.request,wave
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'audio'))
from sequence_audit import audit_song
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/audio';PALLET=ROOT/'build/pallet'
ROM=ROOT/'assets/imported/rocket-user/rocket-user-modifier.gba'
SHA='033235cdd389c4c8cb1aa6d68a93954a55fd681c92a1a554ebc63431117b4eaf'
REV='c75f352304d529f6ba92d4f74b9cf8b5c3810788'
TABLE=0xdac1f8;RATE=16384
SONGS=[('poke_tower','宝可梦塔',518),('pallet','真新镇',512),('vs_trainer','训练家对战',509),('victory_road','冠军之路',507),('silph','希尔弗公司',519),('rocket_hideout','火箭队基地',486),('oak_lab','大木研究所',513),('poke_center','宝可梦中心',515)]
STEPS=[7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767]
INDEX=[-1,-1,-1,-1,2,4,6,8]
def run(args):subprocess.run([str(a) for a in args],cwd=ROOT,check=True)
def encode(samples):
    data=bytearray();decoded=[]
    for at in range(0,len(samples),256):
        block=samples[at:at+256];block=np.pad(block,(0,256-len(block)),mode='edge');predictor=int(block[0]);index=32
        data+=struct.pack('<hBB',predictor,index,0);decoded.append(predictor);codes=[]
        for value in block[1:]:
            step=STEPS[index];diff=int(value)-predictor;code=8 if diff<0 else 0;diff=abs(diff);delta=step>>3
            for bit,part in [(4,step),(2,step>>1),(1,step>>2)]:
                if diff>=part:code|=bit;diff-=part;delta+=part
            predictor=max(-32768,min(32767,predictor+(-delta if code&8 else delta)))
            index=max(0,min(88,index+INDEX[code&7]));codes.append(code);decoded.append(predictor)
        codes.append(0)
        data+=bytes(codes[i]|(codes[i+1]<<4) for i in range(0,256,2))
    return data,np.array(decoded[:len(samples)],dtype=np.float64)
def main():
    OUT.mkdir(parents=True,exist_ok=True);PALLET.mkdir(parents=True,exist_ok=True)
    source=ROM.read_bytes();assert hashlib.sha256(source).hexdigest()==SHA,'Wrong source ROM'
    zig=ROOT/'.cache/toolchains/ziglang/zig.exe'
    run([zig,'cc','-target','arm-freestanding-eabi','-mcpu=arm7tdmi','-mthumb','-std=c99','-O2','-ffreestanding','-fno-builtin','-nostdlib','tools/audio/reference_boot.c','-Wl,-T,tools/audio/reference_boot.ld','-o',OUT/'reference-boot.elf'])
    run([zig,'objcopy','-O','binary',OUT/'reference-boot.elf',OUT/'reference-boot.bin'])
    boot=(OUT/'reference-boot.bin').read_bytes();rom=bytearray(source);rom[0xc0:0xc0+len(boot)]=boot;struct.pack_into('<I',rom,0,0xea00002e)
    combined=bytearray();rows=[];records=[]
    for name,label,index in SONGS+[('select','确认音',5)]:
        head=struct.unpack_from('<I',source,TABLE+index*8)[0];tracks=source[head-0x8000000]
        if name!='select':
            url=f'https://raw.githubusercontent.com/pret/pokefirered/{REV}/sound/songs/midi/mus_{name}.mid'
            path=ROOT/f'.cache/pallet-source/sound/songs/midi/mus_{name}.mid'
            if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(urllib.request.urlopen(url,timeout=30).read())
            midi=path.read_bytes();audit=audit_song(source,TABLE,index,midi);assert audit['all_tracks_match'],f'Melody differs from classic reference: {name}'
            t=audit['tracks'][0];start,end=t['loop_tick'],t['end_tick'];assert start is not None
            ref={'url':url,'sha256':hashlib.sha256(midi).hexdigest(),'note_sequence_match_all_tracks':True,'track_count':tracks}
        else:
            start=None;end=96;ref={'constant_reference':'https://github.com/pret/pokeemerald/blob/5eff78649e7170a877b961ef0b3da13b81a16038/include/constants/songs.h','slot':'SE_SELECT','note_sequence_match_all_tracks':None}
        timing={'header':head,'tracks':tracks,'targets':{'first':1,**({'loop_start':start+1,'loop_end':end+1} if start is not None else {})}}
        (OUT/'timing.json').write_text(json.dumps(timing))
        struct.pack_into('<H',rom,0x2f0,index);(OUT/'reference-player.gba').write_bytes(rom)
        renderer=(ROOT/'tools/audio/render_reference.cjs').read_bytes()
        wav=OUT/'source'/f'{name}.wav';key=hashlib.sha256(boot+renderer+json.dumps(timing,sort_keys=True).encode()+struct.pack('<H',index)).hexdigest()
        cache=wav.with_suffix('.render-key')
        if not wav.exists() or not cache.exists() or cache.read_text()!=key:
            run(['node','tools/audio/render_reference.cjs',OUT/'reference-player.gba',wav,'125' if start is not None else '1.2',OUT/'timing.json']);cache.write_text(key)
        render=json.loads(Path(str(wav)+'.json').read_text())
        with wave.open(str(wav),'rb') as w:
            rate=w.getframerate();pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2).astype(np.float64).mean(axis=1)
        if start is not None:
            marks=render['marks'];assert 'loop_end' in marks,f'Loop not reached: {name}'
            # Preserve a short driver pipeline lead-in, and quantize the loop
            # boundary only to the codec's 15.625 ms independently decoded block.
            begin=max(0,round(marks['loop_start']*RATE/rate/256));finish=round(marks['loop_end']*RATE/rate/256)
        else:begin=0;finish=math.ceil(0.22*RATE/256)
        assert rate%RATE==0,'Unexpected reference DAC rate'
        factor=rate//RATE;taps=np.arange(-24*factor,24*factor+1)
        kernel=np.sinc(taps*0.92/factor)*np.hamming(len(taps));kernel/=kernel.sum()
        pcm=np.convolve(pcm,kernel,mode='same')[::factor];pcm=pcm[:finish*256]
        pcm=np.pad(pcm,(0,finish*256-len(pcm)));pcm=np.clip(np.round(pcm),-32768,32767).astype(np.int16)
        # A short seam taper avoids a click without changing musical timing.
        if start is not None:
            n=32;tail=pcm[-n:].astype(float);front=pcm[begin*256:begin*256+n].astype(float);mix=np.linspace(0,1,n);pcm[-n:]=np.round(tail*(1-mix)+front*mix).astype(np.int16)
        data,decoded=encode(pcm);off=len(combined);combined+=data
        error=np.mean((pcm.astype(float)-decoded)**2);power=np.mean(pcm.astype(float)**2);snr=10*math.log10(power/max(error,1e-9))
        assert snr>15,f'Audio encoding quality: {name} {snr}'
        rows.append('{'+','.join(map(str,[off,finish,begin,int(start is not None)]))+'}')
        records.append({'id':len(records),'name':name,'title_zh':label,'source_slot':index,'source_header':hex(head),'reference':ref,'blocks':finish,'loop_start_block':begin,'seconds':len(pcm)/RATE,'encoded_bytes':len(data),'pcm_sha256':hashlib.sha256(pcm.tobytes()).hexdigest(),'encoded_sha256':hashlib.sha256(data).hexdigest(),'adpcm_snr_db':round(snr,2)})
        with wave.open(str(OUT/f'{name}-preview.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(pcm.tobytes())
        print(f'{name}: {len(pcm)/RATE:.2f}s, {len(data)} bytes, SNR {snr:.1f} dB',flush=True)
    (PALLET/'classic_audio.bin').write_bytes(combined)
    (PALLET/'classic_audio.s').write_text('.section .rodata\n.balign 4\n.global omni_classic_audio_blob\nomni_classic_audio_blob:\n.incbin "build/pallet/classic_audio.bin"\n')
    (PALLET/'classic_audio.h').write_text('''#ifndef OMNI_CLASSIC_AUDIO_H
#define OMNI_CLASSIC_AUDIO_H
#include <stdint.h>
typedef struct {uint32_t offset,blocks,loop_start;uint8_t loop;} OmniAudioClip;
extern const OmniAudioClip omni_audio_clips[];
extern const unsigned char omni_classic_audio_blob[];
#define OMNI_AUDIO_RATE 16384
#define OMNI_AUDIO_BLOCK_BYTES 132
#define OMNI_AUDIO_COUNT 9
#define OMNI_AUDIO_SELECT 8
#endif
''')
    (PALLET/'classic_audio.c').write_text('#include "classic_audio.h"\nconst OmniAudioClip omni_audio_clips[]={'+','.join(rows)+'};\n')
    manifest={'schema_version':1,'source_rom_sha256':SHA,'source_path':str(ROM.relative_to(ROOT)).replace('\\','/'),'source_engine':'Archived m4a/MP2K, original samples and voices rendered in mGBA','tool_reference':'https://github.com/loveemu/saptapper/tree/ff7ec3e4da1f1ffc3bcc05793268036a319b4466','engine_addresses':{'init':'0x08527b04','select':'0x08527bc4','main':'0x08527bb8','vsync':'0x085274a4','song_table':'0x08dac1f8'},'encoding':'mono 16384 Hz, IMA-ADPCM, 256 samples / 132 bytes per independent block; GBA Direct Sound 8-bit output','storage_policy':'Audio, reference ROMs and binaries are local-only; only importer and source audit are committed.','bytes':len(combined),'tracks':records}
    (ROOT/'assets/source/classic-audio.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Classic audio: {len(combined)} bytes',flush=True)
if __name__=='__main__':main()
