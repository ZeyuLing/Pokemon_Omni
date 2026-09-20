/* Fixed upstream reference descriptions, not a declaration of Omni battle rules. */
'use strict';
const {Dex}=require('pokemon-showdown');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'content/pokedex/catalog.json'),'utf8'));
const description=(collection,id)=>{const v=collection.get(id);return v.exists?(v.desc||v.shortDesc||''):'';};
process.stdout.write(JSON.stringify({source:'pokemon-showdown@0.11.11; default generation 9 descriptions',
 abilities:Object.fromEntries(Object.keys(catalog.abilities).map(id=>[id,description(Dex.abilities,id)])),
 moves:Object.fromEntries(Object.keys(catalog.moves).map(id=>[id,description(Dex.moves,id)]))}));
