'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {performance} = require('node:perf_hooks');
const {randomSource} = require('./agents.cjs');
const {runEpisode, verifyReplay} = require('./episode.cjs');
const {teams} = require('./fixtures.cjs');

function schedule({blocks = 12, seed = 20261006, agents = ['power', 'random'], maxTurns = 200} = {}) {
  if (!Number.isSafeInteger(blocks) || blocks < 1 || blocks > 10000) throw new Error('blocks must be 1..10000');
  if (!Array.isArray(agents) || agents.length !== 2 || agents.some(a => !['power', 'random'].includes(a))) {
    throw new Error('Two supported agent names required');
  }
  if (!Number.isSafeInteger(maxTurns) || maxTurns < 1) throw new Error('maxTurns must be a positive integer');
  const random = randomSource(seed);
  const pairs = [[0, 1], [0, 2], [1, 2]];
  const games = [];
  for (let block = 0; block < blocks; ++block) {
    const pair = pairs[block % pairs.length];
    const environmentSeed = Array.from({length: 4}, () => Math.floor(random() * 65536));
    const agentSeeds = [Math.floor(random() * 0x100000000), Math.floor(random() * 0x100000000)];
    // Each agent uses each team in each player slot. Four legs form ONE sampling
    // block; do not pretend these correlated games are independent CI samples.
    for (let leg = 0; leg < 4; ++leg) {
      const candidateSide = leg % 2;
      const candidateTeam = pair[Math.floor(leg / 2)];
      const opponentTeam = pair[1 - Math.floor(leg / 2)];
      const teamIndices = candidateSide === 0 ? [candidateTeam, opponentTeam] : [opponentTeam, candidateTeam];
      const agentSpecs = [0, 1].map(side => {
        const index = side === candidateSide ? 0 : 1;
        return {name: agents[index], seed: agentSeeds[index]};
      });
      games.push({id: `b${String(block).padStart(5, '0')}-l${leg}`, block, leg,
        candidateSide: `p${candidateSide + 1}`, teamIds: teamIndices.map(i => teams[i].id), agentSpecs,
        config: {teams: teamIndices.map(i => teams[i].team), seed: environmentSeed, maxTurns}});
    }
  }
  return games;
}

function summarize(games) {
  const completed = games.filter(g => g.result.terminated);
  const score = g => g.result.winner ? Number(g.result.winner === g.candidateSide) : 0.5;
  const wins = completed.filter(g => g.result.winner === g.candidateSide).length;
  const draws = completed.filter(g => !g.result.winner).length;
  const points = wins + draws / 2;
  const blocks = new Map();
  for (const game of games) {
    if (!blocks.has(game.block)) blocks.set(game.block, []);
    blocks.get(game.block).push(game);
  }
  const completeBlocks = [...blocks.values()].filter(block => block.length === 4 && block.every(g => g.result.terminated));
  const blockScores = completeBlocks.map(block => block.reduce((sum, g) => sum + score(g), 0) / 4);
  let interval = null;
  // A percentile bootstrap on unanimous outcomes gives a misleading [1, 1]
  // (or [0, 0]). Report that interval as unavailable, not certainty of strength.
  const varyingBlocks = new Set(blockScores).size > 1;
  if (blockScores.length >= 2 && varyingBlocks) {
    const random = randomSource(0x4349);
    const bootstrap = Array.from({length: 2000}, () => {
      let sum = 0;
      for (let i = 0; i < blockScores.length; ++i) sum += blockScores[Math.floor(random() * blockScores.length)];
      return sum / blockScores.length;
    }).sort((a, b) => a - b);
    interval = [bootstrap[49], bootstrap[1949]];
  }
  return {
    games: games.length, completed: completed.length, truncated: games.length - completed.length,
    wins, losses: completed.length - wins - draws, draws,
    completedWinRate: completed.length ? wins / completed.length : null,
    completedScore: completed.length ? points / completed.length : null,
    allGameScoreBounds: games.length ? [points / games.length, (points + games.length - completed.length) / games.length] : null,
    completeBlocks: blockScores.length,
    completeBlockScore: blockScores.length ? blockScores.reduce((a, b) => a + b, 0) / blockScores.length : null,
    completeBlockScoreCI95: interval,
    intervalUnavailableReason: blockScores.length < 2 ? 'fewer than two complete blocks' :
      !varyingBlocks ? 'no observed between-block variation; percentile bootstrap is uninformative' : null,
    intervalMethod: '2000-resample percentile bootstrap over complete four-leg blocks; conditional on completion; approximate on this synthetic fixture schedule only',
  };
}

function sourceManifest() {
  const files = ['reference.cjs', 'environment.cjs', 'agents.cjs', 'fixtures.cjs', 'episode.cjs', 'evaluate.cjs', 'cli.cjs', 'serve.cjs',
    '../legality-reference/package.json', '../legality-reference/pnpm-lock.yaml'];
  return Object.fromEntries(files.map(file => [file, createHash('sha256').update(
    fs.readFileSync(path.join(__dirname, file), 'utf8').replace(/\r\n/g, '\n')).digest('hex')]));
}

function evaluate(options) {
  const games = schedule(options);
  const output = path.resolve(options.out || path.join(__dirname, '../../build/battle-lab', new Date().toISOString().replace(/[:.]/g, '-')));
  // A run is immutable. Never silently overwrite a previous benchmark or user file.
  fs.mkdirSync(path.dirname(output), {recursive: true});
  fs.mkdirSync(output);
  const fd = options.trajectories ? fs.openSync(path.join(output, 'transitions.jsonl'), 'wx') : null;
  const results = [];
  const started = performance.now();
  try {
    fs.writeFileSync(path.join(output, 'manifest.json'), JSON.stringify({schema: 1, reference: 'pokemon-showdown@0.11.11',
      format: 'gen4ou', node: process.version, platform: process.platform, architecture: process.arch,
      options: {blocks: options.blocks ?? 12, seed: options.seed ?? 20261006, agents: options.agents ?? ['power', 'random'],
        maxTurns: options.maxTurns ?? 200, trajectories: !!options.trajectories},
      sourceHashes: sourceManifest(),
      scope: 'Synthetic integration evaluation, not evidence of competitive human-level strength. Replays are privileged; transitions contain separate player observations.',
    }, null, 2));
    for (const game of games) {
      const replay = runEpisode(game.config, game.agentSpecs, {onTransition: fd === null ? undefined : transition => {
        fs.writeSync(fd, JSON.stringify({game: game.id, ...transition}) + '\n');
      }});
      // Independent action-driven replay: verifies result AND every observation hash.
      verifyReplay(replay);
      fs.writeFileSync(path.join(output, `${game.id}.replay.json`), JSON.stringify(replay));
      const {config, agentSpecs, ...metadata} = game;
      results.push({...metadata, result: replay.result});
    }
    const seconds = (performance.now() - started) / 1000;
    const report = {schema: 1, summary: summarize(results),
      throughput: {seconds, gamesPerSecond: results.length / seconds,
        decisionFramesPerSecond: results.reduce((sum, g) => sum + g.result.steps, 0) / seconds,
        scope: 'Sequential full episodes including validation, observation hashing, independent replay and file IO; not raw simulator throughput'},
      games: results};
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    return {output, ...report};
  } finally { if (fd !== null) fs.closeSync(fd); }
}
module.exports = {schedule, summarize, sourceManifest, evaluate};
