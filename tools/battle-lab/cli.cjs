#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const {evaluate} = require('./evaluate.cjs');
const {verifyReplay} = require('./episode.cjs');
const help = `Battle Lab: development-host Gen 4 OU reference environment (not Omni/GBA AI)
  node tools/battle-lab/cli.cjs evaluate [--blocks 12] [--seed 20261006]
    [--agents power,random] [--max-turns 200] [--out build/battle-lab/my-run] [--trajectories]
  node tools/battle-lab/cli.cjs replay --file build/battle-lab/my-run/b00000-l0.replay.json
  node tools/battle-lab/cli.cjs serve  # JSONL reset/observe/step/close on stdin/stdout
  node --test tests/battle-lab.test.cjs
Each block has four games swapping team assignments and player slots.
Output directories must not already exist. Dependencies: tools/legality-reference/pnpm-lock.yaml.`;
function main(argv) {
  const command = argv.shift();
  if (!command || command === '--help') return console.log(help);
  if (command === 'serve') {
    if (argv.length) throw new Error('serve takes no flags');
    return require('./serve.cjs').serve();
  }
  const flags = {};
  const allowed = command === 'evaluate' ? ['--blocks', '--seed', '--agents', '--max-turns', '--out', '--trajectories'] :
    command === 'replay' ? ['--file'] : [];
  if (!allowed.length) throw new Error(`Unknown command: ${command}`);
  while (argv.length) {
    const flag = argv.shift();
    if (!allowed.includes(flag) || flag in flags) throw new Error(`Unknown or duplicate flag: ${flag}`);
    if (flag === '--trajectories') flags[flag] = true;
    else {
      const value = argv.shift();
      if (!value || value.startsWith('--')) throw new Error(`Missing value for ${flag}`);
      flags[flag] = value;
    }
  }
  if (command === 'replay') {
    if (!flags['--file']) throw new Error('--file is required');
    console.log(JSON.stringify({verified: true, result: verifyReplay(JSON.parse(fs.readFileSync(flags['--file'], 'utf8')))}, null, 2));
    return;
  }
  const options = {};
  for (const [flag, key] of [['--blocks', 'blocks'], ['--seed', 'seed'], ['--max-turns', 'maxTurns']]) {
    if (flags[flag] !== undefined) {
      if (!/^\d+$/.test(flags[flag])) throw new Error(`${flag} must be an integer`);
      options[key] = Number(flags[flag]);
    }
  }
  if (flags['--agents']) options.agents = flags['--agents'].split(',');
  if (flags['--out']) options.out = flags['--out'];
  options.trajectories = !!flags['--trajectories'];
  const {output, summary, throughput} = evaluate(options);
  console.log(JSON.stringify({output, summary, throughput}, null, 2));
}
if (require.main === module) {
  try { Promise.resolve(main(process.argv.slice(2))).catch(error => { console.error(error.stack); process.exitCode = 1; }); }
  catch (error) { console.error(error.stack); process.exitCode = 1; }
}
module.exports = {main};
