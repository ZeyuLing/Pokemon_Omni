/* Build a bounded v3 fixture from a verified current save. Only tests use this:
 * a two-partner legacy party, no modern forms, old quest flags, lab spawn. */
module.exports=function legacyFixture(source){
 const hash=b=>{let h=2166136261;for(const c of b)h=Math.imul(h^c,16777619)>>>0;return h;};
 const out=Buffer.alloc(32768,255);
 for(const slot of [0,16384]){
  const p=slot+20,a=p+16,n=source.readUInt32LE(slot+8),dex=source.subarray(p+932,p+n);
  const payload=Buffer.alloc(156+dex.length);source.copy(payload,0,p,p+156);
  payload.writeUInt32LE(2,4);payload.writeUInt32LE(dex.length,12);payload[8]=5;payload[9]=6;payload[10]=4;payload[11]=1;
  const g=payload.subarray(16,156);g.writeUInt32LE(3,4);g.writeUInt16LE(5,12);g[14]=3;g[15]=4;g[16]=2;g.writeUInt16LE(15,22);
  g.fill(0,32,128);
  for(const [i,species,pp] of [[0,25,30],[1,1,35]]){const q=32+i*16;g.writeUInt16LE(species,q);g[q+2]=5;g.writeUInt16LE(1,q+4);g[q+6]=pp;g[q+7]=40;g.writeUInt32LE(125,q+10);}
  g.writeUInt32LE(hash(g.subarray(0,136)),136);dex.copy(payload,156);
  const header=Buffer.from(source.subarray(slot,slot+20));header.writeUInt32LE(payload.length,8);header.writeUInt32LE(hash(payload),12);header.writeUInt32LE(hash(header.subarray(0,16)),16);
  header.copy(out,slot);payload.copy(out,p);
 }
 return out;
};
