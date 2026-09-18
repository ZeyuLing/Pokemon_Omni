"""Collect sprite URLs from a commit-pinned PokeAPI form metadata snapshot.
Downloads metadata only, never images; repeat runs reuse verified local cache.
"""
import concurrent.futures, csv, hashlib, json, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COMMIT='e845bb4f69a652cd80fef614b26320036f6287b4'
SPRITES='1dce80ceb372675e9fc7e9f101b71845ef587de2'
CACHE=ROOT/'.cache/form-metadata'/COMMIT
CACHE.mkdir(parents=True,exist_ok=True)
forms=list(csv.DictReader((ROOT/'research/catalog-sources/pokemon_forms.csv').open(encoding='utf-8')))
def fetch(f):
    url=f'https://raw.githubusercontent.com/PokeAPI/api-data/{COMMIT}/data/api/v2/pokemon-form/{f["id"]}/index.json'
    dest=CACHE/(f['id']+'.json')
    try:
        if dest.exists(): raw=dest.read_bytes()
        else:
            for attempt in range(3):
                try:
                    raw=urllib.request.urlopen(url,timeout=20).read();break
                except Exception:
                    if attempt==2:raise
                    time.sleep(.3)
            dest.write_bytes(raw)
        data=json.loads(raw)
        assert data['id']==int(f['id']) and data['name']==f['identifier']
        sprites={k:v.replace('/master/','/'+SPRITES+'/') for k,v in data.get('sprites',{}).items() if isinstance(v,str) and v.startswith('https://raw.githubusercontent.com/PokeAPI/sprites/')}
        return {'form_id':data['id'],'identifier':data['name'],'metadata_url':url,'metadata_sha256':hashlib.sha256(raw).hexdigest(),'sprites':sprites}
    except Exception as exc:return {'form_id':int(f['id']),'identifier':f['identifier'],'metadata_url':url,'error':str(exc),'sprites':{}}
records=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    for i,r in enumerate(pool.map(fetch,forms),1):
        records.append(r)
        if i%200==0:print('metadata',i,'/',len(forms),flush=True)
out={'schema_version':1,'metadata_commit':COMMIT,'sprites_commit':SPRITES,'notice':'Reference URLs from pinned metadata; binary image availability and production asset rights are not implied. No images downloaded.','records':records}
(ROOT/'content/pokedex/form-art-reference.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('DONE',len(records),'forms;',sum(bool(r.get('error')) for r in records),'metadata failures',flush=True)
