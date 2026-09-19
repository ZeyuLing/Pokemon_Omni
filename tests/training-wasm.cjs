const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
(async()=>{
 const data=require('../content/training/plans.json');
 const digest=crypto.createHash('sha256').update(JSON.stringify(data.records)).digest('hex');
 assert.equal(data.content_sha256,digest);
 const {instance}=await WebAssembly.instantiate(fs.readFileSync('build/pokedex/pokedex.wasm'),{}),c=instance.exports;
 assert.equal(c.training_count(),data.records.length);
 assert.equal(c.training_hash()>>>0,parseInt(digest.slice(0,8),16));
 for(const [i,p] of data.records.entries()){
  assert.equal(c.training_status(i,p.generation,p.battle_kind,0,0),3);
  assert.equal(c.training_status(i,p.generation,p.battle_kind,7,7),0);
  assert.equal(c.training_status(i,p.generation,p.battle_kind,7,3),4);
  assert.equal(c.training_status(i,p.generation,p.battle_kind===1?2:1,7,7),2);
 }
 assert.equal(c.training_status(data.records.length,9,1,7,7),1);
 console.log(`PASS: ${data.records.length} training records share JSON/Wasm fingerprint and format/acquisition policy`);
})().catch(e=>{console.error(e);process.exitCode=1;});
