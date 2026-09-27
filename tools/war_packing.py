"""Lossless frame-local LZSS: flag bit 1 means length/distance, 0 literal byte.
Matches use 12-bit distance minus one and 4-bit length minus three.
No filesystem, ROM or palette assumptions; the decoder knows the pixel count.
"""
def pack(data):
    out=bytearray();at=0;seen={}
    while at<len(data):
        flag_at=len(out);out.append(0)
        for bit in range(7,-1,-1):
            if at>=len(data):break
            best=0;distance=0
            for prior in reversed(seen.get(data[at:at+3],[])[-48:]):
                if at-prior>4096:break
                n=3
                while n<18 and at+n<len(data) and data[prior+n]==data[at+n]:n+=1
                if n>best:best=n;distance=at-prior
                if n==18:break
            count=best if best>=3 else 1
            if count>1:
                out[flag_at]|=1<<bit;code=((count-3)<<12)|(distance-1);out.extend((code>>8,code&255))
            else:out.append(data[at])
            for i in range(at,at+count):
                if i+3<=len(data):seen.setdefault(data[i:i+3],[]).append(i)
            at+=count
    return bytes(out)
