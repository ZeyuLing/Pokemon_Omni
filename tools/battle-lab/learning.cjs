'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {BattleEnvironment, digest} = require('./environment.cjs');
const {createAgent, randomSource} = require('./agents.cjs');
const {teams} = require('./fixtures.cjs');
const {encode, FEATURE_NAMES, FEATURE_SCHEMA} = require('./features.cjs');
const {loadNetwork, networkAgent} = require('./network.cjs');
const {summarize} = require('./evaluate.cjs');
const {createHash} = require('node:crypto');
const fileHash = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const clone = x => JSON.parse(JSON.stringify(x));
function write(file, value) { fs.writeFileSync(file, JSON.stringify(value, null, 2), {flag: 'wx'}); }
function sourceHashes() {
  return Object.fromEntries(['features.cjs', 'network.cjs', 'learning.cjs', 'train.py', 'environment.cjs', 'agents.cjs',
    'fixtures.cjs', 'reference.cjs', 'evaluate.cjs', '../legality-reference/pnpm-lock.yaml'].map(file => [file, fileHash(path.join(__dirname, file))]));
}
function prepare(file) {
  const rng = randomSource(61006), pool = teams.flatMap(t => t.team), used = new Set();
  const banks = {};
  for (const [split, count] of [['train', 32], ['development', 12], ['protected', 12]]) {
    banks[split] = [];
    while (banks[split].length < count) {
      const indices = Array.from({length: pool.length}, (_, i) => i);
      for (let i = indices.length - 1; i > 0; --i) { const j = Math.floor(rng() * (i + 1)); [indices[i], indices[j]] = [indices[j], indices[i]]; }
      const selected = indices.slice(0, 6), id = [...selected].sort((a, b) => a - b).join('-');
      if (used.has(id)) continue;
      used.add(id); banks[split].push({id: `${split}-${id}`, team: selected.map(i => clone(pool[i]))});
    }
  }
  const protocol = {schema: 1, featureSchema: FEATURE_SCHEMA, features: FEATURE_NAMES, format: 'gen4ou',
    evidenceClass: 'FIXTURE_NON_EMPIRICAL', trainingMode: 'full_training', banks,
    splitPolicy: 'Disjoint unordered full-team compositions; shared authored species/sets. Not unseen-species or human-data generalization.',
    evaluationPolicy: 'Development feedback only; protected split used once after checkpoint selection by independent audit, never for tuning.',
    seeds: {train: 15000, development: 25000, protected: 35000}, maxTurns: 150};
  fs.mkdirSync(path.dirname(path.resolve(file)), {recursive: true}); write(file, protocol); return {file, hash: fileHash(file)};
}
function gamesFor(protocol, split, blocks, seedOffset = 0) {
  if (!Object.hasOwn(protocol.banks, split)) throw new Error('Unknown split');
  const rng = randomSource(protocol.seeds[split] + seedOffset), bank = protocol.banks[split], games = [];
  for (let block = 0; block < blocks; ++block) {
    const ia = Math.floor(rng() * bank.length); let ib;
    do { ib = Math.floor(rng() * bank.length); } while (ib === ia);
    const selected = [bank[ia], bank[ib]];
    const seed = Array.from({length: 4}, () => Math.floor(rng() * 65536));
    for (let leg = 0; leg < 4; ++leg) {
      const candidateSide = leg % 2, candidateTeam = Math.floor(leg / 2);
      const slots = candidateSide === 0 ? [candidateTeam, 1 - candidateTeam] : [1 - candidateTeam, candidateTeam];
      games.push({id: `${split}-${seedOffset}-${block}-${leg}`, block, candidateSide: `p${candidateSide + 1}`,
        teamIds: slots.map(i => selected[i].id), config: {teams: slots.map(i => selected[i].team), seed, maxTurns: protocol.maxTurns}});
    }
  }
  return games;
}
function play(game, specs, {collect = false, explore = 0, model = null, selfplay = false} = {}) {
  const env = new BattleEnvironment(game.config), rows = [], steps = [];
  const policies = specs.map((name, i) => name === 'network' ? networkAgent(model, 9001 + i + game.block * 2, selfplay) :
    createAgent(name, 9001 + i + game.block * 2));
  const rng = randomSource(7001 + game.block * 4 + Number(game.id.split('-').at(-1)));
  try {
    while (!env.result().terminated && !env.result().truncated) {
      const views = ['p1', 'p2'].map(side => env.observe(side)), choices = {}, candidates = [];
      for (const [i, view] of views.entries()) {
        if (!view.actions.length) continue;
        const learned = specs[i] === 'network' ? policies[i](view) : null;
        let action = learned ? learned.action : policies[i](view);
        if (explore && rng() < explore) action = view.actions[Math.floor(rng() * view.actions.length)].id;
        choices[view.side] = action;
        if (collect) {
          const encoded = learned?.encoded || encode(view), index = encoded.actionIds.indexOf(action);
          candidates.push({id: `${game.id}/${steps.length}/${view.side}`, game: game.id, side: view.side,
            x: encoded.x, mask: encoded.mask, teacher: encoded.teacher, action: index,
            oldProbability: learned?.probabilities[index] ?? null, oldValue: learned?.value ?? null,
            policy: specs[i], observationHash: digest(view)});
        }
      }
      const response = env.step(choices);
      steps.push({observations: views.map(digest), choices, accepted: response.accepted});
      // A rejected, genuinely sampled switch still changes the agent's next
      // information state. Keep it for on-policy gradients; only BC excludes it.
      for (const row of candidates) {
        row.accepted = response.accepted[row.side];
        if (row.accepted || selfplay) rows.push(row);
      }
    }
    const result = env.result();
    for (const row of rows) row.targetValue = result.terminated ? result.winner ? (result.winner === row.side ? 1 : -1) : 0 : null;
    return {rows, result, replay: {schema: 1, scope: 'PRIVATE_DEVELOPMENT_REPLAY', config: env.configuration(),
      agents: specs.map(name => ({name})), steps, result, finalObservations: ['p1', 'p2'].map(side => digest(env.observe(side)))}};
  } finally { env.close(); }
}
function run({mode, protocolFile, split, blocks, out, modelFile, opponent = 'power', seedOffset = 0, selectionFile}) {
  if (!['dataset', 'evaluate', 'selfplay'].includes(mode)) throw new Error('Unsupported run mode');
  if (!Number.isSafeInteger(blocks) || blocks < 1 || blocks > 10000) throw new Error('blocks must be 1..10000');
  if (!Number.isSafeInteger(seedOffset) || seedOffset < 0 || seedOffset > 10000000) throw new Error('Invalid seed offset');
  if (!['power', 'random'].includes(opponent)) throw new Error('Unknown opponent');
  if (split === 'protected' && mode !== 'evaluate') throw new Error('Protected split cannot generate training data');
  const protocol = JSON.parse(fs.readFileSync(protocolFile, 'utf8'));
  if (protocol.featureSchema !== FEATURE_SCHEMA) throw new Error('Protocol feature mismatch');
  const model = modelFile ? loadNetwork(modelFile) : null;
  if (split === 'protected') {
    if (!selectionFile) throw new Error('Protected evaluation requires an immutable checkpoint selection receipt');
    const selection = JSON.parse(fs.readFileSync(selectionFile, 'utf8'));
    const identity = modelFile ? fileHash(modelFile) : 'power-baseline';
    if (selection.protocolHash !== fileHash(protocolFile) || !selection.models.includes(identity) ||
      digest(selection.sourceHashes) !== digest(sourceHashes()) || selection.blocks !== blocks ||
      selection.seedOffset !== seedOffset || !selection.opponents.includes(opponent)) throw new Error('Frozen evaluation contract mismatch');
  }
  if (mode === 'selfplay' && !model) throw new Error('Selfplay requires a checkpoint');
  fs.mkdirSync(out, {recursive: false});
  const manifest = {mode, split, blocks, seedOffset, opponent, protocolHash: fileHash(protocolFile), modelHash: modelFile ? fileHash(modelFile) : null,
    evidenceClass: 'FIXTURE_NON_EMPIRICAL', sourceHashes: sourceHashes(), node: process.version,
    selectionHash: selectionFile ? fileHash(selectionFile) : null};
  write(path.join(out, 'manifest.json'), manifest);
  const fd = mode !== 'evaluate' ? fs.openSync(path.join(out, 'samples.jsonl'), 'wx') : null;
  const results = []; let samples = 0, excludedSamples = 0;
  try {
    for (const game of gamesFor(protocol, split, blocks, seedOffset)) {
      let specs;
      if (mode === 'dataset') specs = game.block % 2 ? ['power', 'power'] : ['power', 'random'];
      else if (mode === 'selfplay') specs = ['network', 'network'];
      else specs = ['p1', 'p2'].map(side => side === game.candidateSide ? model ? 'network' : 'power' : opponent);
      const episode = play(game, specs, {collect: fd !== null, explore: mode === 'dataset' ? 0.15 : 0, model, selfplay: mode === 'selfplay'});
      const {verifyReplay} = require('./episode.cjs');
      verifyReplay(episode.replay);
      write(path.join(out, `${game.id}.replay.json`), episode.replay);
      if (fd !== null) {
        for (const row of episode.rows) {
          if (row.targetValue === null) { ++excludedSamples; continue; }
          fs.writeSync(fd, JSON.stringify(row) + '\n'); ++samples;
        }
      }
      results.push({id: game.id, block: game.block, candidateSide: game.candidateSide, teamIds: game.teamIds, result: episode.result});
    }
  } finally { if (fd !== null) fs.closeSync(fd); }
  const report = {evidenceClass: 'FIXTURE_NON_EMPIRICAL', manifest, samples, excludedSamples,
    sampleHash: fd !== null ? fileHash(path.join(out, 'samples.jsonl')) : null, summary: summarize(results), games: results};
  write(path.join(out, 'report.json'), report);
  return {out, samples, excludedSamples, summary: report.summary};
}
function main(args) {
  const [mode, ...rest] = args, flags = {};
  while (rest.length) { const key = rest.shift(), value = rest.shift();
    if (!['--protocol', '--split', '--blocks', '--out', '--model', '--opponent', '--seed-offset', '--selection'].includes(key) || !value || Object.hasOwn(flags, key)) throw new Error('Invalid arguments');
    flags[key] = value;
  }
  if (mode === 'prepare') return prepare(flags['--protocol']);
  return run({mode, protocolFile: flags['--protocol'], split: flags['--split'] || 'train', blocks: Number(flags['--blocks'] || 8),
    out: flags['--out'], modelFile: flags['--model'], opponent: flags['--opponent'] || 'power', seedOffset: Number(flags['--seed-offset'] || 0), selectionFile: flags['--selection']});
}
if (require.main === module) { try { console.log(JSON.stringify(main(process.argv.slice(2)), null, 2)); } catch (e) { console.error(e.stack); process.exitCode = 1; } }
module.exports = {prepare, gamesFor, play, run, sourceHashes};
