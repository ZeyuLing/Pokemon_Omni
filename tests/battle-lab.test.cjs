'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {BattleEnvironment, actionsFor, digest} = require('../tools/battle-lab/environment.cjs');
const {createAgent} = require('../tools/battle-lab/agents.cjs');
const {teams} = require('../tools/battle-lab/fixtures.cjs');
const {runEpisode, verifyReplay} = require('../tools/battle-lab/episode.cjs');
const {schedule, summarize} = require('../tools/battle-lab/evaluate.cjs');
const clone = x => JSON.parse(JSON.stringify(x));
const base = () => ({teams: [teams[0].team, teams[1].team], seed: [1, 2, 3, 4]});
const mon = (species, ability, moves) => ({species, ability, moves, level: 100, evs: {hp: 1}});
const agentSpecs = [{name: 'power', seed: 7}, {name: 'random', seed: 11}];
function trapConfig() {
  return {seed: [10, 20, 30, 40], teams: [
    [mon('Scizor', 'Technician', ['Bullet Punch']), mon('Blissey', 'Natural Cure', ['Soft-Boiled'])],
    [mon('Magnezone', 'Magnet Pull', ['Thunderbolt', 'Flash Cannon'])],
  ]};
}

test('all synthetic fixture teams play complete reference matches and action-only replays', () => {
  for (let i = 0; i < teams.length; ++i) {
    const replay = runEpisode({...base(), teams: [teams[i].team, teams[(i + 1) % teams.length].team]}, agentSpecs);
    assert.equal(replay.result.terminated, true);
    assert.deepEqual(verifyReplay(replay), replay.result);
  }
});

test('hidden moves, items, EVs and unrevealed bench do not change the other view or agent', () => {
  const original = base();
  const changed = clone(original);
  changed.teams[1][0].moves = ['Crunch', 'Stone Edge', 'Earthquake', 'Fire Punch'];
  changed.teams[1][0].item = 'Choice Scarf';
  changed.teams[1][0].evs = {hp: 252, atk: 252, spd: 4};
  changed.teams[1][5] = mon('Jolteon', 'Volt Absorb', ['Thunderbolt']);
  const a = new BattleEnvironment(original), b = new BattleEnvironment(changed);
  try {
    assert.deepEqual(a.observe('p1'), b.observe('p1'));
    assert.notDeepEqual(a.observe('p2'), b.observe('p2'));
    for (const name of ['random', 'power']) {
      assert.equal(createAgent(name, 17)(a.observe('p1')), createAgent(name, 17)(b.observe('p1')));
    }
    assert.ok(!JSON.stringify(a.observe('p1')).includes('Vaporeon'));
    assert.ok(!JSON.stringify(b.observe('p1')).includes('Choice Scarf'));
  } finally { a.close(); b.close(); }
});

test('observation is deeply immutable and cannot mutate environment state', () => {
  const env = new BattleEnvironment(base());
  try {
    const view = env.observe('p1'), before = digest(view);
    assert.throws(() => { view.request.side.pokemon[0].moves[0] = 'splash'; }, TypeError);
    assert.throws(() => view.history.push('secret'), TypeError);
    assert.equal(digest(env.observe('p1')), before);
    assert.equal('seed' in view, false);
    assert.equal('battle' in view, false);
  } finally { env.close(); }
});

test('extra policy calls and reversed agent evaluation order do not advance environment RNG', () => {
  const env = new BattleEnvironment(base());
  try {
    const before = env.snapshot().battle.prng;
    const agent = createAgent('random', 99);
    for (let i = 0; i < 100; ++i) agent(env.observe('p1'));
    assert.deepEqual(env.snapshot().battle.prng, before);
  } finally { env.close(); }
  const a = runEpisode(base(), agentSpecs);
  const b = runEpisode(base(), agentSpecs, {decisionOrder: ['p2', 'p1']});
  assert.deepEqual(a, b);
});

test('both advertised choices are checked before any state mutation', () => {
  const env = new BattleEnvironment(base());
  try {
    const before = env.snapshot();
    assert.throws(() => env.step({p1: 'move 1', p2: 'move 99'}), /not advertised/);
    assert.deepEqual(env.snapshot(), before);
    assert.throws(() => env.step({p1: 'move 1'}), /not advertised/);
    assert.deepEqual(env.snapshot(), before);
  } finally { env.close(); }
});

test('hidden trapping rejection preserves opponent commitment without leaking which move', () => {
  const a = new BattleEnvironment(trapConfig()), b = new BattleEnvironment(trapConfig());
  try {
    assert.ok(a.observe('p1').actions.some(x => x.id === 'switch 2'));
    assert.equal(a.step({p1: 'switch 2', p2: 'move 1'}).accepted.p1, false);
    assert.equal(b.step({p1: 'switch 2', p2: 'move 2'}).accepted.p1, false);
    assert.deepEqual(a.observe('p1'), b.observe('p1'));
    assert.match(a.observe('p1').error, /trapped/i);
    assert.ok(!a.observe('p1').actions.some(x => x.kind === 'switch'));
    assert.deepEqual(a.observe('p2').actions, []);
    const fork = a.fork();
    try {
      assert.deepEqual(fork.observe('p1'), a.observe('p1'));
      assert.deepEqual(fork.observe('p2'), a.observe('p2'));
      assert.deepEqual(a.step({p1: 'move 1'}), fork.step({p1: 'move 1'}));
      assert.deepEqual(a.observe('p1'), fork.observe('p1'));
    } finally { fork.close(); }
  } finally { a.close(); b.close(); }
});

test('state fork reproduces continuation and independent branch cannot change parent', () => {
  const env = new BattleEnvironment(base());
  const fork = env.fork();
  try {
    const before = digest(env.observe('p1'));
    fork.step({p1: 'move 1', p2: 'move 1'});
    assert.equal(digest(env.observe('p1')), before);
    env.step({p1: 'move 1', p2: 'move 1'});
    for (const side of ['p1', 'p2']) assert.deepEqual(env.observe(side), fork.observe(side));
  } finally { env.close(); fork.close(); }
});

test('U-turn requests only the pivoting player, with legal reserve slots', () => {
  const env = new BattleEnvironment({seed: [1, 2, 3, 4], teams: [
    [mon('Infernape', 'Blaze', ['U-turn']), mon('Starmie', 'Natural Cure', ['Surf'])],
    [mon('Blissey', 'Natural Cure', ['Soft-Boiled'])],
  ]});
  try {
    env.step({p1: 'move 1', p2: 'move 1'});
    assert.deepEqual(env.observe('p1').actions.map(x => x.id), ['switch 2']);
    assert.deepEqual(env.observe('p2').actions, []);
    env.step({p1: 'switch 2'});
    assert.ok(env.observe('p1').request.side.pokemon.find(p => p.active).details.startsWith('Starmie'));
  } finally { env.close(); }
});

test('public opponent HP uses the simulator channel instead of private exact HP', () => {
  const env = new BattleEnvironment(base());
  try {
    env.step({p1: 'move 1', p2: 'move 1'});
    const p1 = env.observe('p1'), p2 = env.observe('p2');
    const publicDamage = p1.history.filter(line => line.startsWith('|-damage|p2'));
    const privateDamage = p2.history.filter(line => line.startsWith('|-damage|p2'));
    assert.ok(publicDamage.length > 0);
    assert.ok(publicDamage.every(line => /\|\d+\/100(?:\||$| )/.test(line) || line.includes('0 fnt')));
    assert.notDeepEqual(publicDamage, privateDamage);
  } finally { env.close(); }
});

test('turn cutoff is truncation, never a fabricated draw or win', () => {
  const config = {seed: [1, 2, 3, 4], maxTurns: 1, teams: [
    [mon('Blissey', 'Natural Cure', ['Soft-Boiled'])],
    [mon('Blissey', 'Natural Cure', ['Soft-Boiled'])],
  ]};
  const transitions = [];
  const replay = runEpisode(config, agentSpecs, {onTransition: x => transitions.push(x)});
  assert.equal(replay.result.truncated, true);
  assert.equal(replay.result.terminated, false);
  assert.equal(replay.result.winner, null);
  assert.equal(replay.result.reason, 'turn-limit');
  assert.ok(transitions.every(x => x.reward === 0));
  assert.deepEqual(verifyReplay(replay), replay.result);
});

test('terminal training rewards are zero-sum and only legal per-side observations are exported', () => {
  const transitions = [];
  const replay = runEpisode(base(), agentSpecs, {onTransition: x => transitions.push(x)});
  const terminal = transitions.filter(x => x.terminated);
  assert.equal(terminal.length, 2);
  assert.equal(terminal.reduce((sum, x) => sum + x.reward, 0), 0);
  assert.equal(terminal.find(x => x.side === replay.result.winner).reward, 1);
  assert.ok(transitions.filter(x => !x.terminated).every(x => x.reward === 0));
  assert.ok(transitions.every(x => x.observation.side === x.side && !('config' in x.observation)));
});

test('replay corruption is detected instead of accepting just the same final winner', () => {
  const replay = runEpisode(base(), agentSpecs);
  replay.steps[0].observations[0] = 'tampered';
  assert.throws(() => verifyReplay(replay), /Observation mismatch/);
});

test('four-leg schedule balances both team assignment and side', () => {
  const games = schedule({blocks: 3});
  assert.equal(games.length, 12);
  for (let block = 0; block < 3; ++block) {
    const subset = games.filter(g => g.block === block);
    const seen = new Set(subset.map(g => [g.candidateSide, g.teamIds[Number(g.candidateSide[1]) - 1]].join('/')));
    assert.equal(seen.size, 4);
    assert.ok(subset.every(g => digest(g.config.seed) === digest(subset[0].config.seed)));
  }
});

test('summary reports truncations separately and uncertainty uses complete blocks', () => {
  const games = Array.from({length: 8}, (_, i) => ({block: Math.floor(i / 4), candidateSide: 'p1',
    result: {terminated: true, winner: i < 4 ? 'p1' : 'p2'}}));
  let result = summarize(games);
  assert.equal(result.completedScore, 0.5);
  assert.deepEqual(result.completeBlockScoreCI95, [0, 1]);
  games[0].result = {terminated: false, truncated: true, winner: null};
  result = summarize(games);
  assert.equal(result.truncated, 1);
  assert.deepEqual(result.allGameScoreBounds, [3 / 8, 4 / 8]);
  assert.equal(result.completeBlocks, 1);
  assert.equal(result.completeBlockScoreCI95, null);
  const unanimous = summarize(games.slice(4));
  assert.equal(unanimous.completeBlockScoreCI95, null);
});

test('PP exhaustion exposes Struggle and an actual draw retains terminal semantics', () => {
  const team = [mon('Blissey', 'Natural Cure', ['Soft-Boiled'])];
  const rows = [];
  const replay = runEpisode({teams: [team, team], seed: [1, 2, 3, 4]}, agentSpecs,
    {onTransition: row => rows.push(row)});
  assert.ok(rows.some(row => row.observation.actions.some(action => action.move === 'struggle')));
  assert.equal(replay.result.terminated, true);
  assert.equal(replay.result.truncated, false);
  assert.equal(replay.result.reason, 'draw');
  assert.equal(replay.result.winner, null);
  assert.ok(rows.filter(row => row.terminated).every(row => row.reward === 0));
  assert.deepEqual(verifyReplay(replay), replay.result);
});

test('decision cap bounds retry loops independently from turn count', () => {
  const env = new BattleEnvironment({...trapConfig(), maxSteps: 1});
  try {
    env.step({p1: 'switch 2', p2: 'move 1'});
    assert.equal(env.result().truncated, true);
    assert.equal(env.result().reason, 'decision-limit');
    assert.equal(env.observe('p1').reward, 0);
    assert.throws(() => env.step({p1: 'move 1'}), /finished/);
  } finally { env.close(); }
});

test('JSONL bridge returns per-side views, recovers from bad requests and closes cleanly', async () => {
  const {Readable, Writable} = require('node:stream');
  const {serve} = require('../tools/battle-lab/serve.cjs');
  const messages = [
    {id: 1, op: 'reset', config: base()},
    {id: 2, op: 'observe', side: 'p1'},
    {id: 3, op: 'step', choices: {p1: 'move 99', p2: 'move 1'}},
    {id: 4, op: 'observe', side: 'p1'},
    {id: 5, op: 'step', choices: {p1: 'move 1', p2: 'move 1'}},
    {id: 6, op: 'reset', config: {...base(), format: 'invalid'}},
    {id: 7, op: 'observe', side: 'p1'},
    {id: 8, op: 'close'},
    {id: 9, op: 'observe', side: 'p1'},
  ];
  let output = '';
  await serve(Readable.from(messages.map(x => JSON.stringify(x) + '\n')),
    new Writable({write(chunk, encoding, callback) { output += chunk; callback(); }}));
  const rows = output.trim().split('\n').map(JSON.parse);
  assert.equal(rows.length, messages.length);
  assert.deepEqual(rows.filter(x => !x.ok).map(x => x.id), [3, 6, 9]);
  assert.deepEqual(rows[1].data, rows[3].data);
  assert.equal(rows[6].data.turn, 2);
  assert.equal(rows[1].data.side, 'p1');
  assert.equal('config' in rows[1].data, false);
});

test('invalid rules, teams, seeds, limits and unsupported request shapes fail explicitly', () => {
  assert.throws(() => new BattleEnvironment({...base(), format: 'gen9ou'}), /Only gen4ou/);
  assert.throws(() => new BattleEnvironment({...base(), seed: [1, 2, 3, -1]}), /uint16/);
  assert.throws(() => new BattleEnvironment({...base(), maxTurns: 0}), /Positive/);
  const invalid = clone(base());
  invalid.teams[0][0].ability = 'Wonder Guard';
  assert.throws(() => new BattleEnvironment(invalid), /Illegal reference team/);
  assert.throws(() => actionsFor({teamPreview: true}), /supports gen4ou/);
  assert.throws(() => schedule({blocks: -1}), /blocks/);
  assert.throws(() => createAgent('random', -1), /uint32/);
});
