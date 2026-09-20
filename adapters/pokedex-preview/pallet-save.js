/* Transport protection before replacing an active emulator save. The ROM also
 * validates adventure + Dex together and chooses the latest valid slot. */
(function(root){
 const validOdex=typeof module!=='undefined'?require('./gba-save.js').odex:root.omniValidOdex;
 function valid(bytes,maps){
  if(bytes.length!==32768||!maps)return false;
  const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),hash=(start,n)=>{let h=2166136261;for(let i=start;i<start+n;i++)h=Math.imul(h^bytes[i],16777619)>>>0;return h;};
  for(const base of [0,16384]){
   const n=v.getUint32(base+8,true),p=base+20,a=p+16;
   if(v.getUint32(base,true)!==0x31474d4f||n<164||n>12500||v.getUint32(base+16,true)!==hash(base,16)||v.getUint32(base+12,true)!==hash(p,n))continue;
   if(v.getUint32(p,true)!==0x4c41504f||v.getUint32(p+4,true)!==1||v.getUint32(p+12,true)!==n-148||v.getUint32(a,true)!==0x5644414f||v.getUint32(a+4,true)!==1||v.getUint32(a+128,true)!==hash(a,128))continue;
   const location=v.getUint16(a+12,true),map=maps.find(m=>m.id===location),chapter=bytes[a+14],starter=bytes[a+15],party=bytes[a+16],x=bytes[p+9],y=bytes[p+10];
   if(!map||bytes[p+8]!==location||x>=map.width||y>=map.height||map.collision[y*map.width+x]||bytes[p+11]>3||chapter>3||starter>3||party>1||bytes[a+17]>1||v.getUint16(a+18,true)>999||v.getUint16(a+20,true)>999||v.getUint32(a+24,true)>999999||v.getUint16(a+28,true)>v.getUint16(a+30,true)||!!starter!==(chapter>=2)||!!starter!==!!party)continue;
   if(party){const species=v.getUint16(a+32,true),level=bytes[a+34],hp=v.getUint16(a+36,true),baseHp=[45,39,44][starter-1],maxHp=Math.floor((2*baseHp+31)*5/100)+15;if(species!==[1,4,7][starter-1]||level!==5||hp>maxHp||bytes[a+38]>35||bytes[a+39]>(starter===3?30:40)||bytes[a+40]||bytes[a+41])continue;}
   if(validOdex(bytes.subarray(p+148,p+n)))return true;
  }
  return false;
 }
 if(typeof module!=='undefined')module.exports=valid;else root.omniValidPalletSram=valid;
})(typeof window==='undefined'?globalThis:window);
