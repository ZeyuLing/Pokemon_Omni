'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'research/catalog-sources');
const manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
for(const f of manifest.files){const bytes=fs.readFileSync(path.join(dir,f.file));assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),f.sha256,`Source hash changed: ${f.file}`);}
// RFC4180 quoting, including quoted commas and newlines; BOM and CRLF accepted.
function csv(text){let rows=[],row=[],field='',quote=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quote&&text[i+1]==='"'){field+='"';i++;}else quote=!quote;}else if(c===','&&!quote){row.push(field);field='';}else if(c==='\n'&&!quote){row.push(field.replace(/\r$/,''));rows.push(row);row=[];field='';}else field+=c;}if(field||row.length){row.push(field);rows.push(row);}assert(!quote,'Unterminated CSV quote');return rows;}
const out={};for(const [file,key] of [['pokemon_species_names.csv','species'],['ability_names.csv','abilities'],['move_names.csv','moves']]){
 const [header,...rows]=csv(fs.readFileSync(path.join(dir,file),'utf8').replace(/^\uFEFF/,''));
 const language=header.indexOf('local_language_id'),name=header.indexOf('name');assert(language>=0&&name>=0);
 out[key]=Object.fromEntries(rows.filter(r=>r[language]==='12').map(r=>[r[0],r[name]]));
}
for(let i=1;i<=1025;i++)assert(out.species[i],`Missing Chinese species ${i}`);
fs.writeFileSync(path.join(root,'content/pokedex/localization.zh-Hans.json'),JSON.stringify(out,null,2)+'\n');
console.log('PASS: source hashes and Chinese names 1–1025; localization rebuilt from vendored CSV');
