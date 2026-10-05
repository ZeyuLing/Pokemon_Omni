'use strict';
const {Dex} = require('./reference.cjs');
const dex = Dex.mod('gen4');
function randomSource(seed) {
  if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) throw new Error('Agent seed must be uint32');
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let x = Math.imul(state ^ (state >>> 15), state | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}
function createAgent(name, seed) {
  if (!['random', 'power'].includes(name)) throw new Error(`Unknown agent: ${name}`);
  const random = randomSource(seed);
  // Closure has public species/move data and its own RNG, never an environment.
  return observation => {
    const actions = observation.actions;
    if (!actions.length) return null;
    if (name === 'random') return actions[Math.floor(random() * actions.length)].id;
    const active = observation.request.side.pokemon.find(mon => mon.active);
    const species = active && dex.species.get(active.details.split(',')[0]);
    const ownTypes = species?.types || [];
    let foeTypes = [];
    const foe = observation.side === 'p1' ? 'p2' : 'p1';
    for (const line of observation.history) {
      const parts = line.split('|');
      if (['switch', 'drag', 'replace', 'detailschange'].includes(parts[1]) && parts[2]?.startsWith(foe)) {
        foeTypes = dex.species.get(parts[3].split(',')[0]).types || [];
      }
    }
    // Intentionally modest baseline: base power × nominal accuracy × STAB ×
    // public species typing. Not a damage calculator; ignores boosts, abilities,
    // variable-power effects, temporary types, status strategy and switching value.
    const scored = actions.map(action => {
      if (action.kind !== 'move') return {action, score: -1};
      const move = dex.moves.get(action.move);
      const immunity = foeTypes.some(type => !dex.getImmunity(move.type, type));
      const multiplier = immunity ? 0 : 2 ** dex.getEffectiveness(move.type, foeTypes);
      const score = move.basePower * (move.accuracy === true ? 1 : move.accuracy / 100) *
        (ownTypes.includes(move.type) ? 1.5 : 1) * multiplier;
      return {action, score};
    });
    const best = Math.max(...scored.map(x => x.score));
    const tied = scored.filter(x => x.score === best);
    return tied[Math.floor(random() * tied.length)].action.id;
  };
}
module.exports = {createAgent, randomSource};
