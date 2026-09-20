const http=require('node:http'),fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const root=path.resolve(__dirname,'..'),port=Number(process.env.OMNI_DEX_PORT||4173);
const paths={'/':['adapters/pokedex-preview/index.html','text/html; charset=utf-8'],'/app.js':['adapters/pokedex-preview/app.js','text/javascript; charset=utf-8'],'/style.css':['adapters/pokedex-preview/style.css','text/css; charset=utf-8'],'/catalog.json':['build/pokedex/catalog.json','application/json; charset=utf-8'],'/pokedex.wasm':['build/pokedex/pokedex.wasm','application/wasm'],'/coverage.json':['content/pokedex/coverage.json','application/json; charset=utf-8'],'/gaps.json':['content/pokedex/gaps.json','application/json; charset=utf-8']};
for(const row of JSON.parse(fs.readFileSync(path.join(root,'assets/source/bond-concepts/manifest.json'),'utf8')).records)paths[row.url]=[row.path,'image/png'];
for(const row of JSON.parse(fs.readFileSync(path.join(root,'content/bond/rom-reference.json'),'utf8')).records)for(const asset of Object.values(row.variants)){
 if(!asset.path.startsWith('assets/imported/rocket-user/bond-sprites/')||asset.path.includes('..')||!asset.url.startsWith('/rocket-art/'))throw Error('Invalid ROM artwork path');
 paths[asset.url]=[asset.path,'image/png'];
}
paths['/features.js']=['adapters/pokedex-preview/features.js','text/javascript; charset=utf-8'];
paths['/plans.json']=['content/training/plans.json','application/json; charset=utf-8'];
for(const [url,file,mime] of [['/gba','adapters/pokedex-preview/gba.html','text/html; charset=utf-8'],['/gba-player.js','adapters/pokedex-preview/gba-player.js','text/javascript; charset=utf-8'],['/emulator/mgba.js','.cache/toolchains/mgba-wasm/dist/mgba/mgba.js','text/javascript; charset=utf-8'],['/emulator/mgba.wasm','.cache/toolchains/mgba-wasm/dist/mgba/mgba.wasm','application/wasm'],['/omni-dex.gba','build/gba/omni-dex.gba','application/octet-stream']])paths[url]=[file,mime];
paths['/gba-save.js']=['adapters/pokedex-preview/gba-save.js','text/javascript; charset=utf-8'];
paths['/play']=['adapters/pokedex-preview/play.html','text/html; charset=utf-8'];
paths['/pallet-save.js']=['adapters/pokedex-preview/pallet-save.js','text/javascript; charset=utf-8'];
paths['/pallet-scene.json']=['build/pallet/scene-audit.json','application/json; charset=utf-8'];
paths['/omni-pallet.gba']=['build/pallet/omni-pallet.gba','application/octet-stream'];
const cache=new Map();
const server=http.createServer((req,res)=>{const pathname=new URL(req.url,'http://127.0.0.1').pathname,item=paths[pathname];if(req.method!=='GET'||!item){res.writeHead(404);res.end('Not found');return;}try{const file=path.join(root,item[0]),stat=fs.statSync(file);let data=cache.get(file);if(!data||data.mtime!==stat.mtimeMs){const bytes=fs.readFileSync(file);data={mtime:stat.mtimeMs,bytes,gzip:zlib.gzipSync(bytes)};cache.set(file,data);}const compressed=/\bgzip\b/.test(req.headers['accept-encoding']||'');res.writeHead(200,{'Content-Type':item[1],'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' https://play.pokemonshowdown.com https://raw.githubusercontent.com https://zukan.pokemon.co.jp https://www.pokemon.co.jp https://www.serebii.net https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com; connect-src 'self'; object-src 'none'; base-uri 'none'",...(compressed?{'Content-Encoding':'gzip','Vary':'Accept-Encoding'}:{})});res.end(compressed?data.gzip:data.bytes);}catch(e){res.writeHead(503,{'Content-Type':'text/plain; charset=utf-8'});res.end('图鉴构建文件缺失。请运行 tools/build_pokedex.ps1。');}});
server.listen(port,'127.0.0.1',()=>console.log(`Omni Pokedex preview: http://127.0.0.1:${port}`));
