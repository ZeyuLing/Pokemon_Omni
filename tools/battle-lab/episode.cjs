'use strict';
const assert = require('node:assert/strict');
const {BattleEnvironment, digest, SCHEMA} = require('./environment.cjs');
const {createAgent} = require('./agents.cjs');
const SIDES = ['p1', 'p2'];
function runEpisode(config, agentSpecs, {onTransition, decisionOrder = SIDES} = {}) {
  if (!Array.isArray(agentSpecs) || agentSpecs.length !== 2) throw new Error('Two agent specifications required');
  if (!['p1,p2', 'p2,p1'].includes(decisionOrder.join(','))) throw new Error('Invalid decision order');
  const agents = agentSpecs.map(spec => createAgent(spec.name, spec.seed));
  const env = new BattleEnvironment(config);
  const replay = {schema: SCHEMA, scope: 'PRIVATE_DEVELOPMENT_REPLAY', config: env.configuration(),
    agents: agentSpecs, steps: []};
  try {
    while (!env.result().terminated && !env.result().truncated) {
      // Materialize BOTH immutable views before invoking either agent or submitting a choice.
      const views = Object.fromEntries(SIDES.map(side => [side, env.observe(side)]));
      const choices = {};
      for (const side of decisionOrder) {
        if (views[side].actions.length) choices[side] = agents[SIDES.indexOf(side)](views[side]);
      }
      const step = env.step(choices);
      replay.steps.push({observations: SIDES.map(side => digest(views[side])), choices, accepted: step.accepted});
      if (onTransition) {
        // Per-side step records. A pending/forced-switch frame is not necessarily a turn.
        // Store terminal outcomes on both sides, including a side waiting this frame.
        for (const side of SIDES) {
          const next = env.observe(side);
          onTransition({schema: SCHEMA, side, step: replay.steps.length, observation: views[side],
            action: choices[side] ?? null, accepted: step.accepted[side] ?? null,
            reward: next.reward, terminated: next.terminated, truncated: next.truncated,
            nextObservation: next});
        }
      }
    }
    replay.result = env.result();
    replay.finalObservations = SIDES.map(side => digest(env.observe(side)));
    return replay;
  } finally { env.close(); }
}
function verifyReplay(replay) {
  if (replay.schema !== SCHEMA || replay.scope !== 'PRIVATE_DEVELOPMENT_REPLAY') throw new Error('Unsupported replay');
  if (replay.config.reference !== 'pokemon-showdown@0.11.11') throw new Error('Reference version mismatch');
  const env = new BattleEnvironment(replay.config);
  try {
    for (const [i, step] of replay.steps.entries()) {
      assert.deepEqual(SIDES.map(side => digest(env.observe(side))), step.observations, `Observation mismatch at step ${i + 1}`);
      assert.deepEqual(env.step(step.choices).accepted, step.accepted, `Acceptance mismatch at step ${i + 1}`);
    }
    assert.deepEqual(env.result(), replay.result, 'Result mismatch');
    assert.deepEqual(SIDES.map(side => digest(env.observe(side))), replay.finalObservations, 'Final observation mismatch');
    if (!replay.result.terminated && !replay.result.truncated) throw new Error('Incomplete episode');
    return replay.result;
  } finally { env.close(); }
}
module.exports = {runEpisode, verifyReplay};
