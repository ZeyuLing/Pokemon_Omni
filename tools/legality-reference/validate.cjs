'use strict';
const {TeamValidator} = require('pokemon-showdown');
function validate(team, format) {
  if (typeof format !== 'string' || !format) throw new Error('An explicit Showdown format is required. Omni is not a Showdown format.');
  if (!Array.isArray(team) || !team.length || team.length > 6) return {valid:false, errors:['Expected 1–6 sets.']};
  const errors = [];
  for (const [i,s] of team.entries()) {
    if (!s || typeof s !== 'object' || Array.isArray(s)) {errors.push(`Set ${i+1}: expected object`); continue;}
    for (const [field,min,max] of [['level',1,100],['happiness',0,255]]) {
      if (s[field] !== undefined && (!Number.isInteger(s[field]) || s[field]<min || s[field]>max)) errors.push(`Set ${i+1}: invalid ${field}`);
    }
    for (const [field,max] of [['evs',252],['ivs',31]]) {
      if (s[field] !== undefined) {
        if (!s[field] || typeof s[field] !== 'object' || Array.isArray(s[field])) {errors.push(`Set ${i+1}: invalid ${field}`); continue;}
        for (const [stat,n] of Object.entries(s[field])) if (!['hp','atk','def','spa','spd','spe'].includes(stat) || !Number.isInteger(n) || n<0 || n>max) errors.push(`Set ${i+1}: invalid ${field}.${stat}`);
      }
    }
  }
  if (errors.length) return {valid:false,errors};
  const validator = new TeamValidator(format);
  if (!validator.format.exists) throw new Error(`Unknown format: ${format}`);
  const result = validator.validateTeam(JSON.parse(JSON.stringify(team)));
  return {valid:!result,errors:result || [],format:validator.format.id,reference:'pokemon-showdown@0.11.11',scope:'Reference format only; excludes Omni capture gates and custom forms.'};
}
module.exports = {validate};
if (require.main === module) {
  try {
    const args = process.argv.slice(2);
    const value = flag => args[args.indexOf(flag)+1];
    if (!args.includes('--format') || !args.includes('--team')) throw new Error('Usage: node validate.cjs --format gen9nationaldexag --team team.json');
    const result = validate(JSON.parse(require('fs').readFileSync(value('--team'),'utf8')),value('--format'));
    console.log(JSON.stringify(result,null,2)); process.exitCode = result.valid ? 0 : 1;
  } catch(e) {console.error(JSON.stringify({error:e.message})); process.exitCode=2;}
}
