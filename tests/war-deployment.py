"""Tactical blocking checks: coherent depth, partners, rescue lanes and fire lanes."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
b=json.loads((ROOT/'content/opening/battlefield.json').read_text('utf8'));a=b['actors']
def depth(u):
    x,y=u['to'];return [y,x,-y,-x][u['team']]
def segment_distance(p,start,end):
    dx,dy=end[0]-start[0],end[1]-start[1]
    t=max(0,min(1,((p[0]-start[0])*dx+(p[1]-start[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(p[0]-start[0]-t*dx,p[1]-start[1]-t*dy)
for team in range(4):
    fighters=[u for u in a if u['team']==team and u['attack']]
    commander=a[20+team*5]
    assert depth(commander)<min(map(depth,fighters)), 'Commander must be behind the combat formation'
    point=fighters[0]
    assert all(depth(u)<=depth(point) for u in fighters), 'Point must lead its formation'
    assert max(depth(u) for u in fighters[3:])<min(depth(u) for u in fighters[:3]), 'Support must remain behind the shoulders'
    trainer,medic,partner=a[22+team*5:25+team*5]
    assert trainer['target']==medic['target']==a.index(partner) and partner['target']==a.index(trainer)
    assert math.dist(trainer['to'],partner['to'])<=40
    assert math.dist(medic['to'],partner['to'])<=48
    assert depth(medic)<min(map(depth,fighters[:3])), 'Rescue route must remain behind the front and shoulders'
    for u in fighters:
        target=a[u['target']]
        assert target['target']==a.index(u), 'Opening contact pairs must be deliberate and reciprocal'
        for friend in a:
            if friend is u or friend['team']!=team:continue
            assert segment_distance(friend['to'],u['to'],target['to'])>=12,(u['id'],friend['id'],'Friendly unit in firing lane')
for u in a:
    assert u['deployment']['station'] and u['deployment']['purpose']
print('PASS: 40 assigned stations, 4 formation depths, 10 reciprocal contacts, partner/rescue distances and friendly fire lanes')
