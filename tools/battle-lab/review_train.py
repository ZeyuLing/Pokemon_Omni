"""Human-approved research pilot. Offline AWR, never PPO on historical logs.

Compact history summaries + action scorer, not the final full-state game agent.
No heuristic action teacher. Missing/terminal action labels are excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from review_data import ReviewStore, write_json, digest
from train import initialize, forward, Adam, PARAMS

SCHEMA='omni-reviewed-human-awr-v1'


def tokens(values, width=32):
    result=np.zeros(width)
    for value in values:
        h=hashlib.sha256(str(value).encode()).digest()
        result[int.from_bytes(h[:2],'little')%width] += 1 if h[2]%2 else -1
    return result.tolist()


def mon(p):
    if not p:
        return [0.0]*49
    return [p.get('hp_pct',0),p.get('lvl',100)/100,
        *[p.get('base_'+s,0)/200 for s in ['hp','atk','def','spa','spd','spe']],
        *[p.get(s+'_boost',0)/6 for s in ['atk','def','spa','spd','spe']],
        float(p.get('item')!='unknownitem'),float(p.get('ability')!='unknownability'),
        float(p.get('status')!='nostatus'),1.0,
        *tokens(['species:'+p['name'],'types:'+p.get('types',''), 'item:'+p.get('item',''),
                 'ability:'+p.get('ability',''),'status:'+p.get('status',''),'effect:'+p.get('effect','')])]


def encode(data):
    rows=[];seen={}
    last=data['states'][-1]
    outcome=1 if last.get('battle_won') else -1 if last.get('battle_lost') else None
    if outcome is None:
        raise ValueError('No terminal outcome')
    for step,(s,a) in enumerate(zip(data['states'],data['actions'])):
        foe=s['opponent_active_pokemon'];seen[foe['name']]=foe
        if s.get('battle_won') or s.get('battle_lost') or a == -1:
            continue
        active=s['player_active_pokemon'];bench=sorted(s['available_switches'],key=lambda p:p['name'])
        context=mon(active)+mon(foe)
        context+=(np.sum([mon(p) for p in bench],axis=0)/6).tolist() if bench else [0.0]*49
        context+=(np.sum([mon(p) for p in seen.values()],axis=0)/6).tolist()
        context += [float(s['forced_switch']),s['opponents_remaining']/6,min(step,200)/200]
        context += tokens([s['format'],s['weather'],s['battle_field'],s['player_conditions'],s['opponent_conditions'],
                           s['player_prev_move']['name'],s['opponent_prev_move']['name']])
        x=[];mask=[]
        moves=sorted(active['moves'],key=lambda m:m['name'])
        for i in range(9):
            if i<4 and i<len(moves) and not s['forced_switch']:
                m=moves[i]
                action=[1,0,m['base_power']/200,float(m['accuracy']),m['priority']/5,
                        m['current_pp']/max(1,m['max_pp']),float(m['category']=='physical'),float(m['category']=='special')]
                action+=tokens(['move:'+m['name'],'type:'+m['move_type']])+mon(active)
                valid=1
            elif i>=4 and i-4<len(bench):
                action=[0,1,0,0,0,0,0,0]+[0.0]*32+mon(bench[i-4]);valid=1
            else:
                action=[0.0]*89;valid=0
            x.append(context+action);mask.append(valid)
        if not 0<=a<9 or not mask[a]:
            raise ValueError('Known label is outside candidate range')
        rows.append((x,mask,a,outcome))
    return rows


def objective(model,x,mask,actions,returns,awr, fixed_weights=None):
    p,v,(h,pooled,counts)=forward(model,x,mask)
    n=len(x);logp=np.log(np.maximum(p,1e-30))
    weights=fixed_weights if fixed_weights is not None else np.exp(np.clip((returns-v)/0.5,-3,3)) if awr else np.ones(n)
    weights=weights/weights.mean()  # treated as fixed targets for this update
    chosen=np.zeros_like(p);chosen[np.arange(n),actions]=1
    dlogits=(p-chosen)*weights[:,None]/n
    dv=.5*(v-returns)*(1-v*v)/n
    gradients={'policy':np.einsum('nah,na->h',h,dlogits),'value':pooled.T@dv,'valueBias':dv.sum()}
    dh=dlogits[:,:,None]*model['policy']+(dv[:,None]*model['value'])[:,None,:]*mask[:,:,None]/counts[:,:,None]
    dz=dh*(1-h*h)
    gradients.update(w=np.einsum('nad,nah->dh',x,dz),b=dz.sum(axis=(0,1)))
    loss=-(weights*logp[np.arange(n),actions]).mean()+.25*np.mean((v-returns)**2)
    if not np.isfinite(loss) or any(not np.isfinite(g).all() for g in gradients.values()):
        raise ValueError('Nonfinite learning result')
    return float(loss),gradients


def metrics(model,batch):
    x,mask,a,r=batch;p,v,_=forward(model,x,mask)
    return {'samples':len(a),'action_nll':float(-np.log(np.maximum(p[np.arange(len(a)),a],1e-30)).mean()),
            'action_accuracy':float((p.argmax(axis=1)==a).mean()),'value_mse':float(((v-r)**2).mean())}


def batch(rows):
    x,m,a,r=zip(*rows)
    return np.asarray(x),np.asarray(m),np.asarray(a,dtype=int),np.asarray(r)


def run(snapshot_path,out,source=None,work=None):
    kwargs={k:v for k,v in [('source',source),('work',work)] if v is not None}
    store=ReviewStore(**kwargs)
    snapshot=json.loads(Path(snapshot_path).read_text('utf-8'))
    if snapshot.get('scope')!='NONCOMMERCIAL_RESEARCH_PILOT':
        raise ValueError('Unsupported training scope')
    store.validate_snapshot(snapshot)
    if sum(store.rows[c['id']]['known_nonterminal_actions'] for c in snapshot['cases'])>10000:
        raise ValueError('CPU pilot limit: 10,000 known decisions; approve a smaller batch')
    rows={'train':[],'development':[]};groups={};ids=set()
    for case in snapshot['cases']:
        row=store.rows[case['id']]
        if case['id'] in ids or case['sha256']!=row['sha256'] or store.status(row)!='approved' or store.reviews[row['id']]!=case['review']:
            raise ValueError('Missing, stale, duplicated or revoked human approval')
        ids.add(case['id'])
        if case['battle_id']!=row['battle_id'] or case['split'] not in rows:
            raise ValueError('Invalid split metadata')
        if groups.setdefault(row['battle_id'],case['split'])!=case['split']:
            raise ValueError('Both POVs must remain in same split')
        rows[case['split']].extend(encode(store.load(case['id'])))
    if len(groups)<4 or not all(rows.values()):
        raise ValueError('Need four approved battle groups and nonempty training/development data')
    sets={k:batch(v) for k,v in rows.items()};dim=sets['train'][0].shape[-1]
    protocol={'featureSchema':SCHEMA,'features':['feature_'+str(i) for i in range(dim)]}
    model=initialize(protocol,32,61008);optimizer=Adam(model,.001);rng=np.random.default_rng(61008)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    write_json(out/'snapshot.json',snapshot)
    before={k:metrics(model,v) for k,v in sets.items()}
    write_json(out/'progress.json',{'status':'training','epoch':0,'epochs':40,'before':before})
    initial={k:np.array(model[k],copy=True) for k in PARAMS};history=[]
    for epoch in range(40):
        store.validate_snapshot(snapshot)
        if (out/'INVALIDATED.json').exists():raise ValueError('Run invalidated by review change')
        order=rng.permutation(len(sets['train'][0]))
        for start in range(0,len(order),128):
            idx=order[start:start+128];b=[v[idx] for v in sets['train']]
            loss,g=objective(model,*b,awr=epoch>=10);optimizer.step(model,g)
        history.append({'epoch':epoch+1,'phase':'BC warmup' if epoch<10 else 'offline AWR','loss':loss})
        write_json(out/'progress.json',{'status':'training',**history[-1],'epochs':40})
    changed=sum(float(np.square(model[k]-initial[k]).sum()) for k in PARAMS)
    if changed<=0:raise ValueError('No parameter update')
    store.validate_snapshot(snapshot)
    model_path=out/'model.json'
    write_json(model_path,{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in model.items()})
    report={'status':'complete','evidence':'REVIEWED_RECONSTRUCTED_DATA_RESEARCH_PILOT',
            'algorithm':'10 epochs BC warmup + 30 epochs Monte Carlo AWR; no on-policy claim',
            'snapshot_sha256':digest(Path(snapshot_path).read_bytes()),'model_sha256':digest(model_path.read_bytes()),
            'parameter_delta_squared':changed,'before':before,'after':{k:metrics(model,v) for k,v in sets.items()},
            'battle_groups':len(groups),'approved_trajectories':len(ids),'history':history,
            'environment':{'python':sys.version,'numpy':np.__version__},
            'code_sha256':{name:digest(Path(__file__).with_name(name).read_bytes()) for name in ['review_train.py','review_data.py','train.py']},
            'limitations':['not a battle-strength evaluation','no exact cultivated stats','candidate mask only',
                          'hashed categorical features and history summaries are pilot representation','noncommercial research only']}
    write_json(out/'report.json',report);write_json(out/'progress.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--out',required=True)
    args=p.parse_args()
    try:print(json.dumps(run(args.snapshot,args.out)))
    except Exception as exc:
        write_json(Path(args.out)/'progress.json',{'status':'failed','error':str(exc)})
        raise
