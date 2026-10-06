'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {BattleEnvironment} = require('../tools/battle-lab/environment.cjs');
const {encode, FEATURE_NAMES, FEATURE_SCHEMA} = require('../tools/battle-lab/features.cjs');
const {infer, loadNetwork, networkAgent} = require('../tools/battle-lab/network.cjs');
const {prepare, gamesFor, play, run} = require('../tools/battle-lab/learning.cjs');
const {teams} = require('../tools/battle-lab/fixtures.cjs');
const {verifyReplay} = require('../tools/battle-lab/episode.cjs');
const mon = (species, ability, moves) => ({species, ability, moves, evs: {hp: 1}});
const model = () => ({schema: FEATURE_SCHEMA, features: FEATURE_NAMES,
  w: FEATURE_NAMES.map(() => [0, 0]), b: [0, 0], policy: [0, 0], value: [0, 0], valueBias: 0});

test('effects distinguish Substitute, Swords Dance, attacks and healing', () => {
  const env = new BattleEnvironment({seed: [1,2,3,4], teams: [
    [mon('Breloom', 'Poison Heal', ['Seed Bomb', 'Substitute', 'Swords Dance', 'Synthesis'])], teams[0].team]});
  try {
    const encoded = encode(env.observe('p1'));
    assert.notDeepEqual(encoded.x[1], encoded.x[2]);
    assert.equal(encoded.x[1][FEATURE_NAMES.indexOf('substitute')], 1);
    assert.equal(encoded.x[2][FEATURE_NAMES.indexOf('boost_self_atk')], 2/6);
    assert.equal(encoded.x[3][FEATURE_NAMES.indexOf('heal_fraction')], 0.5);
    assert.equal(encoded.x[0].length, FEATURE_NAMES.length);
    assert.equal(encoded.mask.reduce((a,b)=>a+b), 4);
  } finally {env.close();}
});

test('feature vectors cannot distinguish unexposed opponent moves, EVs or item', () => {
  const config = {seed:[1,2,3,4], teams:[teams[0].team, teams[1].team]};
  const changed = JSON.parse(JSON.stringify(config));
  changed.teams[1][0].item = 'Choice Scarf';
  changed.teams[1][0].moves[3] = 'Fire Punch';
  changed.teams[1][0].evs = {hp:252,atk:252,spd:4};
  const a = new BattleEnvironment(config), b = new BattleEnvironment(changed);
  try {assert.deepEqual(encode(a.observe('p1')), encode(b.observe('p1')));}
  finally {a.close();b.close();}
});

test('masked inference never emits inactive actions; sampled policy replays with seed', () => {
  const env = new BattleEnvironment({seed:[1,2,3,4], teams:[[mon('Blissey','Natural Cure',['Soft-Boiled'])],teams[0].team]});
  try {
    const view=env.observe('p1'), encoded=encode(view), m=model();
    assert.deepEqual(infer(m,encoded).probabilities, [1,0,0,0,0,0,0,0,0]);
    const a=networkAgent(m,77,true), b=networkAgent(m,77,true);
    assert.deepEqual(a(view),b(view));
    assert.equal(a(view).action,'move 1');
  } finally {env.close();}
});

test('frozen banks exclude full-team overlap regardless of team order', () => {
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'omni-learning-'));
  const file=path.join(folder,'protocol.json');prepare(file);
  const protocol=JSON.parse(fs.readFileSync(file,'utf8')), seen=new Set();
  for(const bank of Object.values(protocol.banks)) for(const entry of bank){
    const key=entry.team.map(s=>s.species).sort().join(',');
    assert.ok(!seen.has(key));seen.add(key);
  }
  assert.equal(seen.size,56);
  assert.deepEqual(gamesFor(protocol,'development',2),gamesFor(protocol,'development',2));
  assert.throws(()=>prepare(file),/EEXIST/);
  assert.throws(()=>run({mode:'dataset',protocolFile:file,split:'protected',blocks:1,out:path.join(folder,'bad')}),/Protected/);
  assert.throws(()=>run({mode:'evaluate',protocolFile:file,split:'protected',blocks:1,out:path.join(folder,'bad2')}),/selection receipt/);
  // Small temporary files are left for the host's temp cleanup; no recursive deletion.
});

test('selfplay keeps sampled trapping rejections and every rollout still replays', () => {
  const game={id:'train-0-0-0',block:0,config:{seed:[10,20,30,40],maxTurns:100,teams:[
    [mon('Scizor','Technician',['Bullet Punch']),mon('Blissey','Natural Cure',['Soft-Boiled'])],
    [mon('Magnezone','Magnet Pull',['Thunderbolt','Flash Cannon'])]]}};
  const m=model();
  // Bias toward switches so the first stochastic choice reaches the hidden trap.
  m.w[FEATURE_NAMES.indexOf('switch')]=[10,0];m.policy=[10,0];
  const episode=play(game,['network','network'],{collect:true,model:m,selfplay:true});
  const rejected=episode.rows.filter(row=>row.accepted===false);
  assert.ok(rejected.length>0);
  assert.ok(rejected.every(row=>row.oldProbability>0 && row.action>=0));
  assert.deepEqual(verifyReplay(episode.replay),episode.result);
});

test('wrong schema and nonfinite checkpoint weights are rejected', () => {
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'omni-model-'));
  const wrong={...model(),schema:'omni-gen4-observation-action-v1'};
  fs.writeFileSync(path.join(folder,'old.json'),JSON.stringify(wrong));
  assert.throws(()=>loadNetwork(path.join(folder,'old.json')),/schema/);
  const bad=model();bad.w[0][0]=null;
  fs.writeFileSync(path.join(folder,'bad.json'),JSON.stringify(bad));
  assert.throws(()=>loadNetwork(path.join(folder,'bad.json')),/parameters/);
});
