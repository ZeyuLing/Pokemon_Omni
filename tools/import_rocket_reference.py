"""Import factual values from the author's locally supplied Fuertes Vínculo.txt.

Usage: python tools/import_rocket_reference.py path/to/document.txt
The document is not redistributed; source hashes make the import auditable.
"""
import hashlib, json, re, sys
from pathlib import Path

source = Path(sys.argv[1])
assert hashlib.sha256(source.read_bytes()).hexdigest() == '41fca3a03df6042865905db0b57f3fb582cf3f2f897b25294c580cedfd8321d8', 'Document differs from pinned author archive; review provenance before importing a new version'
text = source.read_text(encoding='utf-8-sig')
names = {'EN (FLAREON-&)':'Flareon EN','RAI (JOLTEON-&)':'Jolteon RAI','SUI (VAPOREON-&)':'Vaporeon SUI','CROBAT-& PROTAGONISTA':'Crobat Protagonist','CROBAT-& ANDRA':'Crobat Andra','DRAGÓN SAGRADO (DUN-&)':'Sacred Dragon Dun'}
types = dict(zip(['Acero','Tierra','Psíquico','Fuego','Volador','Siniestro','Agua','Lucha','Normal','Hielo','Eléctrico','Fantasma','Veneno','Bicho','Dragón','Hada'],['Steel','Ground','Psychic','Fire','Flying','Dark','Water','Fighting','Normal','Ice','Electric','Ghost','Poison','Bug','Dragon','Fairy']))
abilities = dict(zip(['Impulso','Espejomágico','Pelaje Recio','Adaptable','Respondón','Absorber Eléctrico','Puño Férreo','Mutatipo','Piel Helada','Mandíbula Fuerte','Potencia Bruta','Indefenso','Muro Mágico','Ojocompuesto','Levitación','Psicogénesis'],['Speed Boost','Magic Bounce','Fur Coat','Adaptability','Contrary','Volt Absorb','Iron Fist','Protean','Refrigerate','Strong Jaw','Sheer Force','No Guard','Magic Guard','Compound Eyes','Levitate','Psychic Surge']))
records=[]; heading=None; values=None
for block in re.split(r'\n\s*\n',text):
    block=block.strip()
    if '&' in block and '\n' not in block and ': Ps' not in block and not block.startswith('FUERTES'):
        heading=names.get(block,block.split('-&')[0].title())
    if ': Ps' in block:
        matches=re.findall(r'Ps (\d+), At (\d+), Def (\d+), At\.esp (\d+), Def\.esp (\d+), Velocid (\d+)\. Total (\d+)',block)
        if matches: values=list(map(int,matches[-1]))
    if block.startswith('Tipo:'):
        match=re.search(r'Tipo: (.*?) \| Habilidad: (.*)',block)
        assert match and heading and values
        issues=[]
        if sum(values[:6])!=values[6]: issues.append('Author stated total differs from sum of six stats')
        if heading=='Mamoswine': issues.append('Author uses Mamoswine-M in the stat line under MAMOSWINE-&')
        records.append({'name':heading,'stats':dict(zip(['hp','atk','def','spa','spd','spe'],values[:6])),'reported_total':values[6],'computed_total':sum(values[:6]),'types':[types[t.strip()] for t in match[1].split('/')],'ability':abilities[match[2].strip()],'source_issues':issues})
        heading=None;values=None
assert len(records)==23
out={'schema_version':1,'source_url':'https://www.mediafire.com/file/jagpq55gx21rv8d/Pkmn_Edicion_Team_Rocket_-_Dragonsden_-_.zip/file','author_post':'https://whackahack.com/foro/threads/31-12-2024-pokemon-edicion-team-rocket-4-regiones-kanto-archi7-johto-y-hoenn.65493/','archive_sha256':'311c6aebcc34fd9b2a6fb1c59be1d95c2822c2ebe2e4a463b43b09f4614a8224','document_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'document':'Fuertes Vínculo.txt','retrieved_at':'2026-09-18','version_status':'Author-linked archive; document has no explicit 2.1 marker. Exact 2.1 equivalence remains unverified.','records':records}
dest=Path(__file__).resolve().parents[1]/'content/bond/author-reference.json'
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Imported',len(records),'author-documented bonds; issues:',[(r['name'],r['source_issues']) for r in records if r['source_issues']])
