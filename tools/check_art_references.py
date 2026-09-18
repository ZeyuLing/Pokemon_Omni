"""Check front sprite reference availability with HEAD; no image files downloaded."""
import concurrent.futures, json, urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=json.loads((root/'content/pokedex/form-art-reference.json').read_text(encoding='utf-8'))
urls=sorted({r['sprites']['front_default'] for r in source['records'] if r['sprites'].get('front_default')})
dest=root/'content/pokedex/art-availability.json'
previous=json.loads(dest.read_text(encoding='utf-8'))['urls'] if dest.exists() else {}
def check(url):
    if url in previous and previous[url]['status'] in (200,404):return url,previous[url]
    try:
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=15) as r:
            return url,{'status':r.status,'content_type':r.headers.get('Content-Type'),'bytes':int(r.headers.get('Content-Length','0'))}
    except Exception as e:return url,{'status':getattr(e,'code',0),'error':str(e)}
results={}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    for i,(url,result) in enumerate(pool.map(check,urls),1):
        results[url]=result
        if i%250==0:print('image HEAD checks',i,'/',len(urls),flush=True)
dest.write_text(json.dumps({'checked_at':'2026-09-18','scope':'front_default only; no binary assets downloaded','urls':results},indent=2)+'\n',encoding='utf-8')
print('DONE',len(results),'URLs;',sum(r['status']==200 for r in results.values()),'available',flush=True)
