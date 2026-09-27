"""Compile player-safe initialization dialogue, independent of presentation."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    p=json.loads((R/'content/pallet-town/initialization.json').read_text('utf8'))
    assert p['visibility']=='player_safe' and p['date'] is None
    actions=['none','wake_done','gifts','gary_enter','gary_leave','gary_battle','old_choice','old_tutorial','old_battle','weedle']
    assert len({s['id'] for s in p['sequences']})==len(p['sequences'])
    for s in p['sequences']:
        for b in s['beats']:
            assert bool(b.get('text')) != bool(b.get('action')), 'Use a separate beat for dialogue and actions'
            if b.get('text'):assert b.get('actor'), 'Every dialogue speaker needs a registry identity'
    out=['/* Generated from player-safe initialization.json. */','#ifndef OMNI_INITIALIZATION_DATA_H','#define OMNI_INITIALIZATION_DATA_H','typedef struct {const char *text;unsigned char action;} OmniStoryBeat;']
    rows=[];offset=0
    for i,s in enumerate(p['sequences']):
        out.append(f'#define STORY_{s["id"].upper()} {i}')
        rows.append('{'+f'{offset},{len(s["beats"])}'+'}');offset+=len(s['beats'])
    out.append('static const unsigned short omni_story_ranges[][2]={'+','.join(rows)+'};')
    out.append('static const OmniStoryBeat omni_story_beats[]={')
    for s in p['sequences']:
        for b in s['beats']:out.append('{'+json.dumps(b.get('text',''),ensure_ascii=False)+','+str(actions.index(b.get('action','none')))+'},')
    out.append('};')
    for i,a in enumerate(actions):out.append(f'#define STORY_ACTION_{a.upper()} {i}')
    out.append('static const char *omni_research_dialogue(unsigned person){switch(person){')
    for k,v in p['research_dialogue'].items():out.append('case '+k+':return '+json.dumps(v,ensure_ascii=False)+';')
    out.append('default:return 0;}}\n#endif\n')
    (R/'build/pallet/initialization_data.h').write_text('\n'.join(out),encoding='utf8')
    print(f'Initialization: {len(p["sequences"])} sequences, {offset} authored beats')
if __name__=='__main__':main()
