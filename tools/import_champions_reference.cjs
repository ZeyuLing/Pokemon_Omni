'use strict';
// Import only the five M-C Mega ability assignments, never execute remote TypeScript.
const fs=require('node:fs'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {Dex,toID}=require('./legality-reference/node_modules/pokemon-showdown');
const commit='2ddfa0476f8207e12e204b1c69f7c7683b17633c';
(async()=>{
 const files={};
 for(const name of ['pokedex','abilities']){
  const url=`https://raw.githubusercontent.com/smogon/pokemon-showdown/${commit}/data/${name}.ts`;
  const response=await fetch(url);assert(response.ok);const bytes=Buffer.from(await response.arrayBuffer());
  files[name]={url,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),text:bytes.toString('utf8')};
 }
 const records=[];
 for(const id of ['absolmegaz','garchompmegaz','lucariomegaz','golisopodmega','baxcaliburmega']){
  const block=files.pokedex.text.split('\t'+id+': {')[1]?.split('\n\t},')[0];
  const match=block?.match(/abilities: (\{[^\n]+\})/);assert(match,id);
  const abilities=[...match[1].matchAll(/(?:\b(\d)|\b(H|S)):\s*"([^"]+)"/g)].map(m=>{
   const aid=toID(m[3]),abilityBlock=files.abilities.text.split('\t'+aid+': {')[1]?.split('\n\t},')[0];
   const num=Number(abilityBlock?.match(/\bnum: (\d+)/)?.[1]||Dex.abilities.get(aid).num);assert(num>0);
   return {slot:m[1]||m[2],id:aid,name_en:m[3],num};
  });assert(abilities.length);records.push({source_form_id:id,abilities});
 }
 const result={schema_version:1,checked_at:'2026-09-18',scope:'Champions Regulation M-C ability reference; community implementation, not official numeric certification',official_roster:'https://news.pokemon-home.com/en/page/816.html',commit,sources:Object.values(files).map(({text,...v})=>v),records};
 fs.writeFileSync('content/pokedex/champions-ability-reference.json',JSON.stringify(result,null,2)+'\n');
})().catch(e=>{console.error(e);process.exitCode=1;});
