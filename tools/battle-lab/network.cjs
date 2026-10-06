'use strict';
const fs = require('node:fs');
const {encode, FEATURE_SCHEMA, FEATURE_NAMES} = require('./features.cjs');
const {randomSource} = require('./agents.cjs');
function loadNetwork(file) {
  const model = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (model.schema !== FEATURE_SCHEMA || JSON.stringify(model.features) !== JSON.stringify(FEATURE_NAMES)) throw new Error('Model feature schema mismatch');
  const {w, b, policy, value, valueBias} = model;
  const h = b?.length;
  if (!h || w?.length !== FEATURE_NAMES.length || w.some(row => row.length !== h) || policy?.length !== h || value?.length !== h ||
    [...w.flat(), ...b, ...policy, ...value, valueBias].some(x => !Number.isFinite(x))) throw new Error('Invalid model parameters');
  return model;
}
function infer(model, encoded) {
  const logits = [], pooled = Array(model.b.length).fill(0);
  const count = encoded.mask.reduce((a, b) => a + b, 0);
  if (!count) throw new Error('No active actions');
  for (let a = 0; a < encoded.x.length; ++a) {
    if (!encoded.mask[a]) { logits.push(-1e30); continue; }
    let logit = 0;
    for (let j = 0; j < model.b.length; ++j) {
      let z = model.b[j];
      for (let k = 0; k < model.w.length; ++k) z += encoded.x[a][k] * model.w[k][j];
      const hidden = Math.tanh(z);
      logit += hidden * model.policy[j]; pooled[j] += hidden / count;
    }
    logits.push(logit);
  }
  const max = Math.max(...logits), exp = logits.map((x, i) => encoded.mask[i] ? Math.exp(x - max) : 0);
  const sum = exp.reduce((a, b) => a + b, 0);
  const probabilities = exp.map(x => x / sum);
  const v = Math.tanh(model.valueBias + pooled.reduce((s, x, j) => s + x * model.value[j], 0));
  return {probabilities, value: v};
}
function networkAgent(model, seed, sample = false) {
  const rng = randomSource(seed);
  return observation => {
    const encoded = encode(observation), prediction = infer(model, encoded);
    let index;
    if (sample) {
      let draw = rng(); index = encoded.actionIds.length - 1;
      for (let i = 0; i < encoded.actionIds.length; ++i) { draw -= prediction.probabilities[i]; if (draw < 0) { index = i; break; } }
    } else {
      const max = Math.max(...prediction.probabilities);
      const tied = prediction.probabilities.map((p, i) => p === max ? i : -1).filter(i => i >= 0);
      index = tied[Math.floor(rng() * tied.length)];
    }
    return {action: encoded.actionIds[index], index, encoded, ...prediction};
  };
}
module.exports = {loadNetwork, infer, networkAgent};
