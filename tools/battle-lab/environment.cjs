'use strict';
const {createHash} = require('node:crypto');
const {Battle, TeamValidator, extractChannelMessages, version} = require('./reference.cjs');
const {validate} = require('../legality-reference/validate.cjs');
const FORMAT = 'gen4ou';
const SCHEMA = 1;
const SIDES = ['p1', 'p2'];
const clone = value => JSON.parse(JSON.stringify(value));
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
function freeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

// This is the *advertised* action set, never a probe against hidden battle state.
// A hidden trapping ability can cause Showdown to reject a switch and update only
// that player's request. The peer's already committed action stays private.
function actionsFor(request) {
  if (!request || request.wait) return [];
  if (request.teamPreview || (request.active && request.active.length !== 1)) {
    throw new Error('This adapter supports gen4ou singles without team preview only');
  }
  const actions = [];
  const forced = request.forceSwitch?.[0];
  const active = request.active?.[0];
  if (!forced && active) {
    active.moves.forEach((move, i) => {
      if (!move.disabled && move.pp !== 0) actions.push({id: `move ${i + 1}`, kind: 'move', move: move.id});
    });
  }
  if (forced || (active && !active.trapped)) {
    request.side.pokemon.forEach((mon, i) => {
      if (!mon.active && !mon.condition.endsWith(' fnt')) actions.push({id: `switch ${i + 1}`, kind: 'switch', slot: i + 1});
    });
  }
  if (!actions.length) throw new Error('Unsupported request: no advertised actions');
  return actions;
}

class BattleEnvironment {
  #battle;
  #requests = {p1: null, p2: null};
  #history = {p1: [], p2: []};
  #errors = {p1: null, p2: null};
  #config;
  #steps = 0;
  constructor({teams, seed, maxTurns = 200, maxSteps = 2000, format = FORMAT}) {
    if (format !== FORMAT) throw new Error(`Only ${FORMAT} is supported; Omni rules are not implemented`);
    if (!Array.isArray(seed) || seed.length !== 4 || seed.some(n => !Number.isInteger(n) || n < 0 || n > 65535)) {
      throw new Error('Environment seed must contain four uint16 integers');
    }
    if (!Number.isSafeInteger(maxTurns) || maxTurns < 1 || !Number.isSafeInteger(maxSteps) || maxSteps < 1) {
      throw new Error('Positive integer turn and decision limits are required');
    }
    if (!Array.isArray(teams) || teams.length !== 2) throw new Error('Exactly two teams required');
    const normalized = teams.map(team => {
      const result = validate(team, format);
      if (!result.valid) throw new Error(`Illegal reference team: ${result.errors.join('; ')}`);
      const copy = clone(team);
      // Validator normalizes defaults/forms on its input; use those exact sets.
      const errors = new TeamValidator(format).validateTeam(copy);
      if (errors) throw new Error(errors.join('; '));
      return copy;
    });
    this.#config = {schema: SCHEMA, reference: `pokemon-showdown@${version}`, format, teams: normalized,
      seed: [...seed], maxTurns, maxSteps};
    this.#battle = new Battle({formatid: format, seed: [...seed], send: this.#receive.bind(this)});
    SIDES.forEach((side, i) => this.#battle.setPlayer(side, {name: side, team: clone(normalized[i])}));
    this.#battle.sendUpdates();
  }
  #receive(type, data) {
    if (Array.isArray(data)) data = data.join('\n');
    if (type === 'update') {
      const channels = extractChannelMessages(data, [1, 2]);
      SIDES.forEach((side, i) => {
        // Wall-clock timestamps are not game information and prevent deterministic replay.
        this.#history[side].push(...channels[i + 1].filter(line => line && !line.startsWith('|t:|')));
      });
    } else if (type === 'sideupdate') {
      const newline = data.indexOf('\n');
      const side = data.slice(0, newline);
      if (!SIDES.includes(side)) throw new Error('Unsupported player channel');
      for (const line of data.slice(newline + 1).split('\n')) {
        if (line.startsWith('|request|')) this.#requests[side] = JSON.parse(line.slice(9));
        else if (line.startsWith('|error|')) this.#errors[side] = line.slice(7);
      }
    }
    // The omniscient end payload includes both teams and RNG; never route it to agents.
  }
  result() {
    const terminated = this.#battle.ended;
    // At turn N+1, N turns have finished. Forced replacements within N are allowed.
    const truncated = !terminated && (this.#battle.turn > this.#config.maxTurns || this.#steps >= this.#config.maxSteps);
    return freeze({terminated, truncated, winner: terminated ? this.#battle.winner || null : null,
      reason: terminated ? (this.#battle.winner ? 'win' : 'draw') : truncated ?
        (this.#steps >= this.#config.maxSteps ? 'decision-limit' : 'turn-limit') : null,
      turn: this.#battle.turn, steps: this.#steps});
  }
  observe(side) {
    if (!SIDES.includes(side)) throw new Error('Expected p1 or p2');
    const result = this.result();
    // Accepted actions stay locked while a peer retries an unavailable action.
    const waiting = this.#battle.getSide(side).isChoiceDone();
    const request = result.terminated || result.truncated || waiting ? null : this.#requests[side];
    return freeze(clone({schema: SCHEMA, format: FORMAT, side, turn: this.#battle.turn,
      request, actions: actionsFor(request), history: this.#history[side], error: this.#errors[side],
      terminated: result.terminated, truncated: result.truncated,
      reward: result.terminated ? result.winner === side ? 1 : result.winner ? -1 : 0 : 0}));
  }
  step(choices) {
    const result = this.result();
    if (result.terminated || result.truncated) throw new Error('Episode is finished');
    if (!choices || typeof choices !== 'object' || Object.keys(choices).some(k => !SIDES.includes(k))) {
      throw new Error('Expected choices keyed by player');
    }
    // Validate the entire joint submission before mutating anything. Never query
    // engine legality with speculative opponent configurations to generate a mask.
    const views = SIDES.map(side => this.observe(side));
    views.forEach(view => {
      if (view.actions.length) {
        if (!view.actions.some(a => a.id === choices[view.side])) throw new Error(`Action not advertised for ${view.side}`);
      } else if (choices[view.side] !== undefined && choices[view.side] !== null) {
        throw new Error(`${view.side} is not awaiting an action`);
      }
    });
    if (!views.some(view => view.actions.length)) throw new Error('Deadlock: no active requests');
    ++this.#steps;
    const accepted = {};
    for (const view of views) {
      if (!view.actions.length) continue;
      this.#errors[view.side] = null;
      accepted[view.side] = this.#battle.choose(view.side, choices[view.side]);
    }
    this.#battle.sendUpdates();
    return {accepted, result: this.result()};
  }
  // Privileged harness/search infrastructure only. Snapshots contain hidden sets,
  // pending actions and environment RNG and MUST NOT become agent inputs.
  snapshot() {
    return clone({schema: SCHEMA, config: this.#config, battle: this.#battle.toJSON(),
      requests: this.#requests, history: this.#history, errors: this.#errors, steps: this.#steps});
  }
  static restore(snapshot) {
    if (snapshot.schema !== SCHEMA || snapshot.config.reference !== `pokemon-showdown@${version}`) {
      throw new Error('Incompatible snapshot');
    }
    const data = clone(snapshot);
    const env = new BattleEnvironment(data.config);
    env.#battle.destroy();
    env.#requests = data.requests;
    env.#history = data.history;
    env.#errors = data.errors;
    env.#steps = data.steps;
    env.#battle = Battle.fromJSON(data.battle);
    env.#battle.send = env.#receive.bind(env);
    return env;
  }
  fork() { return BattleEnvironment.restore(this.snapshot()); }
  configuration() { return freeze(clone(this.#config)); }
  close() { this.#battle.destroy(); }
}
module.exports = {BattleEnvironment, actionsFor, digest, FORMAT, SCHEMA};
