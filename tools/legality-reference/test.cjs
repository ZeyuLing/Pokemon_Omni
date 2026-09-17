const assert = require('node:assert/strict');
const {validate} = require('./validate.cjs');
const base = {species:'Charizard',ability:'Blaze',moves:['Flamethrower'],nature:'Timid',evs:{spa:252,spe:252,spd:4}};
let checks=0;
function check(set,expected,format='gen9nationaldexag') {assert.equal(validate([set],format).valid,expected); checks++;}
check(base,true);
check({...base,moves:['Extreme Speed']},false);
check({...base,ability:'Wonder Guard'},false);
check({...base,evs:{spa:252,spe:252,hp:252}},false);
check({...base,evs:{spa:-1}},false);
check({...base,ivs:{atk:32}},false);
check({...base,level:1.5},false);
check({...base,level:101},false);
check({species:'Mewtwo',ability:'Pressure',moves:['Psychic']},false,'gen9ou');
const before=JSON.stringify(base); validate([base],'gen9nationaldexag'); assert.equal(JSON.stringify(base),before); checks++;
assert.throws(()=>validate([base],'')); checks++;
assert.throws(()=>validate([base],'notarealformat')); checks++;
console.log(`PASS: ${checks} host reference checks`);
