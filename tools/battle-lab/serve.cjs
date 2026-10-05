'use strict';
const readline = require('node:readline');
const {BattleEnvironment} = require('./environment.cjs');

// JSONL bridge for a future Python/PyTorch learner. This is trusted orchestration,
// not an isolation sandbox for arbitrary plugins. No omniscient snapshot endpoint.
async function serve(input = process.stdin, output = process.stdout) {
  const lines = readline.createInterface({input, crlfDelay: Infinity});
  let env;
  try {
    for await (const line of lines) {
      let id = null;
      try {
        const message = JSON.parse(line);
        id = message.id ?? null;
        let data;
        if (message.op === 'reset') {
          // Validate/create first so a failed reset preserves the previous episode.
          const replacement = new BattleEnvironment(message.config);
          env?.close();
          env = replacement;
          data = env.result();
        } else if (message.op === 'close') {
          env?.close();
          env = undefined;
          data = {closed: true};
        } else {
          if (!env) throw new Error('reset is required before observation or action');
          if (message.op === 'observe') data = env.observe(message.side);
          else if (message.op === 'step') data = env.step(message.choices);
          else throw new Error(`Unknown operation: ${message.op}`);
        }
        output.write(JSON.stringify({id, ok: true, data}) + '\n');
      } catch (error) {
        output.write(JSON.stringify({id, ok: false, error: error.message}) + '\n');
      }
    }
  } finally { env?.close(); lines.close(); }
}
module.exports = {serve};
