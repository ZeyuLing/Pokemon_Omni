"""Read m4a event timing and compare note sequences with pinned pret MIDI.

Data-format reference: pret/pokeemerald src/m4a_1.s and include/m4a.h.
This reads source data only; it is not a replacement synthesizer.
"""
import struct
WAIT=list(range(25))+[28,30,32,36,40,42,44,48,52,54,56,60,64,66,68,72,76,78,80,84,88,90,92,96]
def midi_tracks(b):
    division=struct.unpack_from('>H',b,12)[0];at=14;tracks=[]
    while at<len(b):
        assert b[at:at+4]==b'MTrk';n=struct.unpack_from('>I',b,at+4)[0];d=b[at+8:at+8+n];at+=8+n
        p=0;tick=0;status=0;notes=[];tempo=[]
        def var():
            nonlocal p
            v=0
            while True:
                c=d[p];p+=1;v=(v<<7)|(c&127)
                if c<128:return v
        while p<len(d):
            tick+=var();c=d[p]
            if c>=128:status=c;p+=1
            if status==255:
                t=d[p];p+=1;ln=var();data=d[p:p+ln];p+=ln
                if t==0x51:tempo.append((tick,int.from_bytes(data,'big')))
            elif status in [240,247]:
                ln=var();p+=ln
            else:
                ln=1 if status&240 in [192,208] else 2;v=d[p:p+ln];p+=ln
                if status&240==144 and v[1]:notes.append((tick,v[0],v[1]))
        tracks.append({'notes':notes,'tempo':tempo})
    return division,tracks

def m4a_track(b,start):
    p=start;tick=0;running=0;key=0;vel=0;shift=0;stack=[];visited={};notes=[];tempo=[]
    for _ in range(100000):
        # Only top-level instruction locations identify the musical loop.
        if not stack:
            if p in visited and tick>visited[p]:return {'notes':notes,'tempo':tempo,'loop_tick':visited[p],'end_tick':tick}
            visited[p]=tick
        c=b[p];p+=1
        if c<128:p-=1;c=running
        elif c>=0xbd:running=c
        if 0x80<=c<=0xb0:tick+=WAIT[c-0x80]
        elif c==0xb1:return {'notes':notes,'tempo':tempo,'loop_tick':None,'end_tick':tick}
        elif c in [0xb2,0xb3]:
            target=struct.unpack_from('<I',b,p)[0]-0x8000000
            if c==0xb3:stack.append(p+4)
            p=target
        elif c==0xb4:
            if stack:p=stack.pop()
        elif c>=0xcf:
            if b[p]<128:key=b[p];p+=1
            if b[p]<128:vel=b[p];p+=1
            if b[p]<128:p+=1
            notes.append((tick,key+shift,vel))
        elif c==0xce:
            if b[p]<128:p+=1
        elif c==0xcd:p+=2
        elif c in [0xba,0xbb,0xbc,0xbd,0xbe,0xbf,0xc0,0xc1,0xc2,0xc3,0xc4,0xc5,0xc8]:
            v=b[p];p+=1
            if c==0xbb:tempo.append((tick,v*2))
            if c==0xbc:shift=v if v<128 else v-256
        else:raise ValueError(f'Unsupported m4a command {c:x} at {p-1:x}')
    raise ValueError('Unbounded m4a sequence')

def audit_song(rom,table,index,midi):
    head=struct.unpack_from('<I',rom,table+index*8)[0]-0x8000000
    tracks=[m4a_track(rom,struct.unpack_from('<I',rom,head+8+i*4)[0]-0x8000000) for i in range(rom[head])]
    div,ref=midi_tracks(midi);ref=[t for t in ref if t['notes']]
    matches=[]
    for i,t in enumerate(tracks):
        keys=[n[1] for n in t['notes']]
        candidates=[j for j,r in enumerate(ref) if [n[1] for n in r['notes'][:len(keys)]]==keys]
        matches.append(candidates)
    return {'tracks':tracks,'reference_division':div,'midi_track_matches':matches,'all_tracks_match':all(matches)}
