"""Snapshot public official Zukan search facts, excluding copyrighted flavor text.
Endpoint is used by https://zukan.pokemon.co.jp/js/mainlist.js.
"""
import concurrent.futures, hashlib, json, urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def page(n):
    url=f'https://zukan.pokemon.co.jp/zukan-api/api/search/?limit=64&page={n}'
    raw=urllib.request.urlopen(url,timeout=25).read()
    return json.loads(raw),{'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
first,source=page(1)
records=first['results'];sources=[source]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for data,source in pool.map(page,range(2,first['paging']['pageCount']+1)):
        records.extend(data['results']);sources.append(source)
assert len(records)==first['paging']['count']
assert len({r['zukan_no'] for r in records})==len(records)
out={'schema_version':1,'checked_at':'2026-09-18','official_site':'https://zukan.pokemon.co.jp/','scope':'Official named form identity, types, measurements and reference image links. No numeric base stats, learnsets or hidden abilities asserted.','sources':sources,'records':records}
(root/'content/pokedex/official-zukan-reference.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Official named records:',len(records))
