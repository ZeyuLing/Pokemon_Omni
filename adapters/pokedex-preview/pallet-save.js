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
   const version=v.getUint32(a+4,true);
   if(v.getUint32(p,true)!==0x4c41504f||v.getUint32(p+4,true)!==1||v.getUint32(p+12,true)!==n-148||v.getUint32(a,true)!==0x5644414f||![1,2].includes(version)||v.getUint32(a+128,true)!==hash(a,128))continue;
   const location=v.getUint16(a+12,true),map=maps.find(m=>m.id===location),chapter=bytes[a+14],starter=bytes[a+15],party=bytes[a+16],x=bytes[p+9],y=bytes[p+10];
   if(!map||bytes[p+8]!==location||x>=map.width||y>=map.height||map.collision[y*map.width+x]||bytes[p+11]>3||chapter>3||starter>(version===1?3:4)||party>(version===1?1:6)||bytes[a+17]>1||v.getUint16(a+18,true)>999||v.getUint16(a+20,true)>999||v.getUint32(a+24,true)>999999||v.getUint16(a+28,true)>v.getUint16(a+30,true)||!!starter!==(chapter>=2)||!!starter!==!!party||(!starter&&location>=6)||(version===1&&location>5))continue;
   const event=version===2?v.getUint16(a+22,true):0;
   if(event>15||((event&2)&&!(event&1))||((event&8)&&!(event&4)))continue;
   const roster={1:[45,35,40],4:[39,35,40],7:[44,35,30],25:[35,30,40],16:[40,35,0],19:[30,35,30],109:[40,35,0]};
   let partyValid=true;
   for(let i=0;i<party;i++){const m=a+32+i*16,species=v.getUint16(m,true),level=bytes[m+2],hp=v.getUint16(m+4,true),spec=roster[species];if(!spec||level<2||level>10||hp>Math.floor((2*spec[0]+31)*level/100)+level+10||bytes[m+6]>spec[1]||bytes[m+7]>spec[2]||bytes[m+8]||bytes[m+9]||(version===2&&(bytes[m+3]>1||v.getUint32(m+10,true)>1000))||(version===1&&(species!==[1,4,7][starter-1]||level!==5))){partyValid=false;break;}}
   if(!partyValid)continue;
   if(validOdex(bytes.subarray(p+148,p+n)))return true;
  }
  return false;
 }
 if(typeof module!=='undefined')module.exports=valid;else root.omniValidPalletSram=valid;
})(typeof window==='undefined'?globalThis:window);
