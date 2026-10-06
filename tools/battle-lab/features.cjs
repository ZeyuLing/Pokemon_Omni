'use strict';
const {Dex} = require('./reference.cjs');
const dex = Dex.mod('gen4');
const MAX_ACTIONS = 9;
const STATS = ['atk', 'def', 'spa', 'spd', 'spe'];
const STATUS = ['par', 'brn', 'psn', 'tox', 'slp', 'frz'];
const CONTEXT = ['own_hp', 'foe_hp', 'foe_known', 'own_alive', 'own_team_hp', 'foe_seen', 'foe_fainted', 'turn', 'forced',
  ...STATUS.map(x => `own_${x}`), ...STATUS.map(x => `foe_${x}`),
  ...STATS.map(x => `own_boost_${x}`), ...STATS.map(x => `foe_boost_${x}`), 'sand', 'rain', 'sun', 'hail'];
const ACTION = ['move', 'switch', 'power', 'accuracy', 'stab', 'effectiveness', 'priority', 'physical', 'special', 'status',
  'pp', 'power_prior', 'switch_hp', 'switch_worst_stab', ...STATS.map(x => `base_${x}`),
  'targets_self', ...STATUS.map(x => `inflict_${x}`), ...STATS.map(x => `boost_self_${x}`), ...STATS.map(x => `boost_target_${x}`),
  'heal_fraction', 'substitute', 'protect', 'wish', 'rest', 'leech_seed', 'hazard', 'hazard_removal', 'pivot', 'phaze', 'contact', 'recoil', 'drain'];
const FEATURE_NAMES = [...CONTEXT, ...ACTION];
const FEATURE_SCHEMA = 'omni-gen4-observation-action-v2';
const clamp = x => Math.max(-1, Math.min(1, x));
function condition(text = '') {
  const [hp, status = ''] = text.split(' ');
  const [a, b] = hp.split('/').map(Number);
  return {hp: Number.isFinite(a) && b > 0 ? a / b : 0, status};
}
function multiplier(type, types) {
  return dex.getImmunity(type, types) ? 2 ** dex.getEffectiveness(type, types) : 0;
}
function publicState(observation) {
  const own = observation.side, foe = own === 'p1' ? 'p2' : 'p1';
  const state = {species: null, hp: 0, status: '', seen: new Set(), fainted: new Set(), weather: '',
    ownBoost: Object.fromEntries(STATS.map(x => [x, 0])), foeBoost: Object.fromEntries(STATS.map(x => [x, 0]))};
  for (const line of observation.history) {
    const p = line.split('|'), who = p[2]?.slice(0, 2);
    if (['switch', 'drag', 'replace'].includes(p[1])) {
      if (who === own) for (const stat of STATS) state.ownBoost[stat] = 0;
      if (who === foe) {
        state.species = dex.species.get(p[3].split(',')[0]);
        Object.assign(state, condition(p[4]));
        state.seen.add(p[2]);
        for (const stat of STATS) state.foeBoost[stat] = 0;
      }
    }
    if (p[1] === 'detailschange' && who === foe) state.species = dex.species.get(p[3].split(',')[0]);
    if (['-damage', '-heal'].includes(p[1]) && who === foe) Object.assign(state, condition(p[3]));
    if (p[1] === '-status' && who === foe) state.status = p[3];
    if (p[1] === '-curestatus' && who === foe) state.status = '';
    if (p[1] === 'faint' && who === foe) { state.fainted.add(p[2]); state.hp = 0; }
    if (p[1] === '-weather') state.weather = p[2];
    if (p[1] === '-clearallboost') {
      for (const stat of STATS) { state.ownBoost[stat] = 0; state.foeBoost[stat] = 0; }
    }
    if (who === own || who === foe) {
      const boosts = who === own ? state.ownBoost : state.foeBoost;
      if (STATS.includes(p[3])) {
        if (p[1] === '-boost') boosts[p[3]] += Number(p[4]);
        if (p[1] === '-unboost') boosts[p[3]] -= Number(p[4]);
        if (p[1] === '-setboost') boosts[p[3]] = Number(p[4]);
      }
      if (p[1] === '-clearboost') for (const stat of STATS) boosts[stat] = 0;
    }
  }
  return state;
}
function encode(observation) {
  if (observation.format !== 'gen4ou' || !observation.actions.length) throw new Error('Expected an active gen4ou decision');
  const party = observation.request.side.pokemon;
  const active = party.find(p => p.active);
  const ownSpecies = active ? dex.species.get(active.details.split(',')[0]) : null;
  const own = condition(active?.condition);
  const foe = publicState(observation);
  const context = [own.hp, foe.hp, Number(!!foe.species), party.filter(p => !p.condition.endsWith(' fnt')).length / 6,
    party.reduce((s, p) => s + condition(p.condition).hp, 0) / 6, foe.seen.size / 6, foe.fainted.size / 6,
    Math.min(observation.turn, 200) / 200, Number(!!observation.request.forceSwitch?.[0]),
    ...STATUS.map(x => Number(own.status === x)), ...STATUS.map(x => Number(foe.status === x)),
    ...STATS.map(x => clamp(foe.ownBoost[x] / 6)), ...STATS.map(x => clamp(foe.foeBoost[x] / 6)),
    ...['Sandstorm', 'RainDance', 'SunnyDay', 'Hail'].map(x => Number(foe.weather === x))];
  const rows = [], scores = [];
  for (const action of observation.actions) {
    const move = action.kind === 'move' ? dex.moves.get(action.move) : null;
    const target = action.kind === 'switch' ? party[action.slot - 1] : active;
    const species = target ? dex.species.get(target.details.split(',')[0]) : ownSpecies;
    const accuracy = move ? move.accuracy === true ? 1 : move.accuracy / 100 : 0;
    const stab = move && ownSpecies?.types.includes(move.type) ? 1.5 : 1;
    const effectiveness = move ? multiplier(move.type, foe.species?.types || []) : 0;
    const score = move ? move.basePower * accuracy * stab * effectiveness : -1;
    const requestedMove = move && observation.request.active?.[0]?.moves[Number(action.id.split(' ')[1]) - 1];
    const healing = move?.heal ? move.heal[0] / move.heal[1] :
      ['synthesis', 'moonlight', 'morningsun'].includes(move?.id) ?
        foe.weather === 'SunnyDay' ? 2/3 : foe.weather && foe.weather !== 'none' ? 1/4 : 1/2 : 0;
    const values = [Number(!!move), Number(!move), (move?.basePower || 0) / 200, accuracy, move ? stab / 1.5 : 0,
      effectiveness / 4, (move?.priority || 0) / 5, Number(move?.category === 'Physical'),
      Number(move?.category === 'Special'), Number(move?.category === 'Status'),
      requestedMove ? (requestedMove.pp ?? 1) / (requestedMove.maxpp || requestedMove.pp || 1) : 0,
      score / 400, !move ? condition(target.condition).hp : 0,
      !move && foe.species ? Math.max(...foe.species.types.map(type => multiplier(type, species.types))) / 4 : 0,
      ...STATS.map(stat => (species?.baseStats[stat] || 0) / 200),
      Number(move?.target === 'self'), ...STATUS.map(status => Number(move?.status === status)),
      ...STATS.map(stat => (move?.target === 'self' ? move.boosts?.[stat] || 0 : move?.self?.boosts?.[stat] || 0) / 6),
      ...STATS.map(stat => (move?.target !== 'self' ? move?.boosts?.[stat] || 0 : 0) / 6),
      healing, Number(move?.volatileStatus === 'substitute'),
      Number(move?.volatileStatus === 'protect'), Number(move?.id === 'wish'), Number(move?.id === 'rest'),
      Number(move?.volatileStatus === 'leechseed'), Number(!!move?.sideCondition), Number(move?.id === 'rapidspin'),
      Number(!!move?.selfSwitch), Number(!!move?.forceSwitch), Number(!!move?.flags.contact),
      move?.recoil ? move.recoil[0] / move.recoil[1] : 0, move?.drain ? move.drain[0] / move.drain[1] : 0];
    rows.push([...context, ...values]); scores.push(score);
  }
  if (rows.length > MAX_ACTIONS || rows.some(row => row.length !== FEATURE_NAMES.length || row.some(x => !Number.isFinite(x)))) {
    throw new Error('Invalid feature dimensions or values');
  }
  const best = Math.max(...scores), ties = scores.filter(x => x === best).length;
  const teacher = scores.map(x => x === best ? 1 / ties : 0);
  const mask = rows.map(() => 1);
  while (rows.length < MAX_ACTIONS) { rows.push(Array(FEATURE_NAMES.length).fill(0)); mask.push(0); teacher.push(0); }
  return {schema: FEATURE_SCHEMA, x: rows, mask, teacher, actionIds: observation.actions.map(a => a.id)};
}
module.exports = {encode, FEATURE_SCHEMA, FEATURE_NAMES, MAX_ACTIONS};
