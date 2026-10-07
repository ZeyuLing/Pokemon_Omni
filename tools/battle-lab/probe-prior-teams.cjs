'use strict';
// These are NEW synthetic configurations sampled from marginal usage statistics.
// They are not recovered human teams or samples from the true joint distribution.
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {TeamValidator, version} = require('./reference.cjs');
const {randomSource} = require('./agents.cjs');
const {runEpisode, verifyReplay} = require('./episode.cjs');

function weighted(entries, rng) {
  const available = entries.filter(([,w]) => Number.isFinite(w) && w > 0);
  if (!available.length) throw new Error('Empty positive-weight distribution');
  let cursor = rng() * available.reduce((s,[,w]) => s+w, 0);
  for (const [key,weight] of available) { cursor -= weight; if (cursor < 0) return key; }
  return available.at(-1)[0];
}
function build(statistics, count = 32) {
  if (statistics.info.metagame !== 'gen4ou') throw new Error('Probe restricted to gen4ou');
  const rng = randomSource(20261007), validator = new TeamValidator('gen4ou');
  const candidates = [], rejected = {}, seen = new Set();
  const speciesWeights = Object.entries(statistics.data).map(([species,row]) => [species,row.usage]);
  let attempts = 0;
  while (candidates.length < 256 && attempts++ < 10000) {
    const species = weighted(speciesWeights,rng), row = statistics.data[species];
    const item = weighted(Object.entries(row.Items),rng), ability = weighted(Object.entries(row.Abilities),rng);
    const [nature, spread] = weighted(Object.entries(row.Spreads),rng).split(':');
    if (!spread) throw new Error('Unsupported spread format');
    const stats = ['hp','atk','def','spa','spd','spe'];
    const values = spread.split('/').map(Number);
    if (values.length !== 6 || values.some(x => !Number.isInteger(x) || x < 0)) throw new Error('Invalid spread');
    const moves = [], options = Object.entries(row.Moves).filter(([name,w]) => name && name !== 'nothing' && w > 0);
    for (let i=0;i<4 && options.length;i++) {
      const move = weighted(options,rng); moves.push(move); options.splice(options.findIndex(([m])=>m===move),1);
    }
    const set = {species, item:item === 'nothing' ? '' : item, ability, nature,
      evs:Object.fromEntries(stats.map((s,i)=>[s,values[i]])), moves, level:100};
    // IVs are generated defaults, with any Hidden Power normalization applied by
    // the validator. They are never claimed to have been observed in human teams.
    const errors = validator.validateTeam([set]);
    if (errors) { for (const e of errors) rejected[e] = (rejected[e] || 0)+1; continue; }
    const id = JSON.stringify(set);
    if (!seen.has(id)) {seen.add(id);candidates.push(set);}
  }
  const teams = [];
  for (let i=0;i<count;i++) {
    const selected = [], species = new Set();
    for (let j=0;j<10000 && selected.length<6;j++) {
      const set = candidates[Math.floor(rng()*candidates.length)];
      if (!set || species.has(set.species)) continue;
      species.add(set.species); selected.push(JSON.parse(JSON.stringify(set)));
    }
    if (selected.length !== 6) throw new Error('Insufficient distinct valid species');
    const errors = validator.validateTeam(selected);
    if (errors) throw new Error(errors.join('; '));
    teams.push(selected);
  }
  return {evidenceClass:'ENGINEERING_VALIDATION',origin:'SYNTHETIC_FROM_MARGINAL_USAGE_STATS',
    reference:`pokemon-showdown@${version}`,format:'gen4ou',seed:20261007,
    attempts,acceptedSets:candidates.length,uniqueSpecies:new Set(candidates.map(x=>x.species)).size,
    uniqueItems:new Set(candidates.map(x=>x.item)).size,uniqueMoves:new Set(candidates.flatMap(x=>x.moves)).size,
    uniqueSpreads:new Set(candidates.map(x=>JSON.stringify([x.nature,x.evs]))).size,
    rejected,teams};
}
if (require.main === module) {
  const [input,out] = process.argv.slice(2);
  if (!input || !out) throw new Error('Usage: node probe-prior-teams.cjs STATS.json OUT_DIR');
  fs.mkdirSync(out,{recursive:true});
  const bytes=fs.readFileSync(input), result=build(JSON.parse(bytes));
  result.sourceSha256=createHash('sha256').update(bytes).digest('hex');
  fs.writeFileSync(path.join(out,'generated-teams.json'),JSON.stringify(result,null,2));
  const probes=[];
  for(let i=0;i<4;i++) {
    const replay=runEpisode({teams:result.teams.slice(i*2,i*2+2),seed:[2026,10,7,i+1],maxTurns:150},
      [{name:'power',seed:i+1},{name:'power',seed:i+10}]);
    verifyReplay(replay);
    fs.writeFileSync(path.join(out,`probe-${i}.replay.json`),JSON.stringify(replay));
    probes.push(replay.result);
  }
  const {teams,...summary}=result;
  summary.teamCount=teams.length;summary.probes=probes;
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(summary,null,2));
  console.log(JSON.stringify(summary,null,2));
}
module.exports={build,weighted};
