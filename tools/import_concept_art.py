"""Copy selected built-in imagegen PNGs into the project, preserving originals.

Usage: python tools/import_concept_art.py local-path-map.json
The local map is [{"id": prompt_id, "source": absolute_generated_file_path}].
Only the selected art, prompt IDs and content hashes enter the project manifest.
"""
import hashlib, json, shutil, struct, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / 'assets/source/bond-concepts'
prompts = {r['id'] for r in json.loads((folder/'prompts.json').read_text(encoding='utf-8'))['records']}
manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
records = {r['id']: r for r in manifest['records']}
(folder/'images').mkdir(exist_ok=True)
for row in json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')):
    key = row['id']
    assert key in prompts, 'Unknown concept ID'
    source = Path(row['source'])
    raw = source.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n', 'Expected PNG'
    width, height = struct.unpack('>II', raw[16:24])
    target = folder/'images'/f'{key}-v1.png'
    if target.exists():
        assert target.read_bytes() == raw, 'Refusing to overwrite a different selected concept'
    else:
        shutil.copyfile(source, target)
    records[key] = dict(id=key, entry_id='dex:omni:rocket-bond:'+key,
                       path=target.relative_to(root).as_posix(), url=f'/concept-art/{key}-v1.png',
                       sha256=hashlib.sha256(raw).hexdigest(), width=width, height=height,
                       prompt_id=key, created_at='2026-09-19', status='concept_not_approved_final_design',
                       not_source_game_appearance=True)
manifest['records'] = sorted(records.values(), key=lambda r: r['id'])
(folder/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Selected concept illustrations:', len(records))
