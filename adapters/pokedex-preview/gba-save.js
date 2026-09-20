/* Validate imported transport bytes before replacing emulator/browsing state.
 * The ROM still applies the shared C ODEX loader and newest-valid-slot policy. */
(function(root){
 function odex(bytes){if(bytes.length<16)return false;const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let h=2166136261;for(let i=0;i<bytes.length-4;i++)h=Math.imul(h^bytes[i],16777619)>>>0;const count=v.getUint32(8,true);if(bytes[0]!==79||bytes[1]!==68||bytes[2]!==69||bytes[3]!==88||v.getUint32(4,true)!==1||bytes.length!==16+count*5||h!==v.getUint32(bytes.length-4,true))return false;const seen=new Set();for(let i=0;i<count;i++){const id=v.getUint32(12+i*5,true),f=bytes[16+i*5];if(!id||seen.has(id)||!f||(f&248)||((f&2)&&!(f&1))||((f&4)&&(f&3)!==3))return false;seen.add(id);}return true;}
 function valid(bytes){if(bytes.length!==32768)return false;const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),hash=(start,n)=>{let h=2166136261;for(let i=start;i<start+n;i++)h=Math.imul(h^bytes[i],16777619)>>>0;return h;};
  for(const base of [0,16384]){if(bytes[base]!==79||bytes[base+1]!==68||bytes[base+2]!==71||bytes[base+3]!==1)continue;const n=v.getUint32(base+8,true),start=base+20;if(n<16||n>12288||hash(base,16)!==v.getUint32(base+16,true)||hash(start,n)!==v.getUint32(base+12,true))continue;
   if(bytes[start]!==79||bytes[start+1]!==68||bytes[start+2]!==69||bytes[start+3]!==88||v.getUint32(start+4,true)!==1)continue;const count=v.getUint32(start+8,true);if(n!==16+count*5||hash(start,n-4)!==v.getUint32(start+n-4,true))continue;
   let ok=true;const seen=new Set();for(let i=0;i<count;i++){const id=v.getUint32(start+12+i*5,true),f=bytes[start+16+i*5];if(!id||seen.has(id)||!f||(f&248)||((f&2)&&!(f&1))||((f&4)&&(f&3)!==3)){ok=false;break;}seen.add(id);}if(ok)return true;
  }return false;
 }
 if(typeof module!=='undefined'){module.exports=valid;module.exports.odex=odex;}else{root.omniValidSram=valid;root.omniValidOdex=odex;}
})(typeof window==='undefined'?globalThis:window);
