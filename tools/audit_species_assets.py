"""Generate per-species and per-catalog-entry coverage without conflating uses."""
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = {1,4,7,25,16,19,109,13,111,59,128,131}


def main():
    national = json.loads((ROOT/'content/species/national-index.json').read_text('utf8'))['species']
    catalog = json.loads((ROOT/'content/pokedex/catalog.json').read_text('utf8'))['entries']
    prepared = json.loads((ROOT/'assets/source/species-preparation.json').read_text('utf8'))
    candidates = {}
    names = {n['name_zh_hans']:n['national_number'] for n in national}
    for source in prepared['sources']:
        for r in source['records']:
            n = names.get(r.get('source_name'))
            if n:
                candidates.setdefault(n, []).append(source['id']+':'+str(r['sid']))
    field_roster=json.loads((ROOT/'assets/source/travel-roster.json').read_text('utf8'))['species']
    field={r['species'] for r in field_roster if r['status']=='native_source_prepared'}
    rows=[]
    for n in national:
        number=n['national_number']
        entries=[e for e in catalog if e['national_number']==number]
        base=next((e for e in entries if e['category']=='base'), {})
        variants=base.get('art_reference',{}).get('variants',{})
        rows.append(dict(national=number,name=n['name_zh_hans'],
            field='integrated_native_four_directions_visual_review_pending' if number in field else 'missing',
            battle='integrated_base_front_back' if number in RUNTIME else 'not_integrated',
            party_icon='integrated_native_first_frame' if number in field else 'not_integrated',
            dex_front='reference_mapped' if variants.get('front_default') else 'missing',
            dex_back='reference_mapped' if variants.get('back_default') else 'missing',
            source_candidates=';'.join(candidates.get(number,[])),
            candidate_status='name_match_only_identity_and_visual_review_pending',
            catalog_entries=len(entries)))
    out=ROOT/'docs/assets';out.mkdir(exist_ok=True)
    def write(name, rows):
        stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
        (out/name).write_text(stream.getvalue(),'utf8')
    write('species-coverage.csv', rows)
    forms=[]
    for e in catalog:
        v=e.get('art_reference',{}).get('variants',{})
        forms.append(dict(entry_id=e['entry_id'],national=e['national_number'],name=e['name_zh_hans'],category=e['category'],
            dex_front=v.get('front_default') or '',dex_back=v.get('back_default') or '',
            field_form_acceptance='not_individually_verified',battle_form_acceptance='not_individually_verified'))
    write('form-coverage.csv', forms)
    summary={'national_species':len(rows),'catalog_entries':len(forms),
        'runtime_field_species':len(field),'runtime_battle_base_species':len(RUNTIME),'runtime_party_icons':len(field),
        'base_dex_front_mapped':sum(r['dex_front']=='reference_mapped' for r in rows),
        'base_dex_back_mapped':sum(r['dex_back']=='reference_mapped' for r in rows),
        'species_with_unverified_source_name_candidates':sum(bool(r['source_candidates']) for r in rows),
        'source_slot_counts':{s['id']:s['counts'] for s in prepared['sources']},
        'remaining':'Field animations, mounting art, per-form identity and visual review, missing palettes, gameplay integration.'}
    (out/'coverage-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__':
    main()
