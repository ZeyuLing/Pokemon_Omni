"""Disposable engineering fixtures only; never approve production trajectories."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import numpy as np
from review_data import ReviewStore, write_json, validate_trajectory
from review_server import App, make_handler
from review_train import objective, metrics, encode, run
from train import initialize, forward, Adam, PARAMS, load_model


def fixture():
    move=dict(name='testmove',move_type='normal',category='physical',base_power=50,
              accuracy=1.,priority=0,current_pp=10,max_pp=10)
    p=dict(name='testmon',hp_pct=1.,lvl=100,moves=[move],types='normal',item='unknownitem',ability='unknownability',status='nostatus')
    state=dict(format='gen4ou',player_active_pokemon=p,opponent_active_pokemon=p,
               available_switches=[],forced_switch=False,opponents_remaining=6,weather='none',
               battle_field='none',player_conditions='none',opponent_conditions='none',
               player_prev_move=move,opponent_prev_move=move,battle_won=False,battle_lost=False)
    states=[copy.deepcopy(state) for _ in range(5)];states[-1]['battle_won']=True
    return dict(states=states,actions=[0,0,0,0,-1])


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name);self.source=root/'source';self.work=root/'work'
        self.source.mkdir()
        rows=[dict(source='gen4ou-prefix',member=f'test/{i}',battle_id=f'battle-{i//2}',
                   sha256=str(i)*64,nonterminal_steps=4,missing_nonterminal_actions=0,
                   known_nonterminal_actions=4,result='win',out_of_candidate_range=0) for i in range(8)]
        (self.source/'trajectory-index.jsonl').write_text('\n'.join(map(json.dumps,rows)),'utf-8')
        self.store=ReviewStore(self.source,self.work,verify=False)
        self.fake=patch.object(ReviewStore,'load',return_value={})
        self.fake.start()

    def tearDown(self):self.fake.stop();self.tmp.cleanup()

    def approve(self):
        for r in self.store.rows.values():
            self.store.review(r['id'],'approved',r['sha256'],'TEST ONLY fixture approval',True)

    def test_pending_and_ack_gate(self):
        with self.assertRaises(ValueError):self.store.training_snapshot()
        r=next(iter(self.store.rows.values()))
        with self.assertRaises(ValueError):self.store.review(r['id'],'approved',r['sha256'],'test',False)
        with self.assertRaises(ValueError):self.store.review(r['id'],'approved','wrong','test',True)
        self.assertEqual(self.store.summary()['approved'],0)

    def test_battle_group_split_and_withdrawal_after_restart(self):
        self.approve();snapshot=self.store.training_snapshot();groups={}
        for c in snapshot['cases']:
            self.assertEqual(groups.setdefault(c['battle_id'],c['split']),c['split'])
        self.assertEqual(set(groups.values()),{'train','development'})
        for name in ['run-a','run-b']:write_json(self.work/'runs'/name/'snapshot.json',snapshot)
        r=next(iter(self.store.rows.values()))
        self.store.review(r['id'],'pending',r['sha256'],'revoke fixture',False)
        with self.assertRaises(ValueError):self.store.validate_snapshot(snapshot)
        restarted=App(ReviewStore(self.source,self.work,verify=False))
        self.assertEqual(restarted.job_status()['status'],'invalidated')
        for name in ['run-a','run-b']:self.assertTrue((self.work/'runs'/name/'INVALIDATED.json').exists())

    def test_only_registered_sources(self):
        (self.source/'trajectory-index.jsonl').write_text(json.dumps({'source':'legacy-simulator'}),'utf-8')
        with self.assertRaises(ValueError):ReviewStore(self.source,self.work,verify=False)

    def test_http_write_origin_token_and_pending_gate(self):
        app=App(self.store);server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base+'/api/info') as response:self.assertEqual(json.load(response)['summary']['approved'],0)
            for headers,code in [({},403),({'Origin':base,'X-Review-Token':app.token},400)]:
                with self.assertRaises(HTTPError) as caught:urlopen(Request(base+'/api/train',data=b'{}',headers=headers))
                self.assertEqual(caught.exception.code,code)
                caught.exception.close()
            self.assertIsNone(app.process)
        finally:server.shutdown();server.server_close();thread.join()

    def test_disposable_full_training_and_stale_snapshot(self):
        self.approve();snapshot=self.store.training_snapshot()
        request=Path(self.tmp.name)/'request.json';write_json(request,snapshot)
        with patch('review_train.ReviewStore',return_value=self.store),patch.object(self.store,'load',return_value=fixture()):
            report=run(request,Path(self.tmp.name)/'test-run')
            self.assertEqual(report['status'],'complete')
            self.assertEqual(len(report['history']),40)
            self.assertGreater(report['parameter_delta_squared'],0)
            r=next(iter(self.store.rows.values()))
            self.store.review(r['id'],'pending',r['sha256'],'revoke fixture',False)
            with self.assertRaises(ValueError):run(request,Path(self.tmp.name)/'forbidden-run')

    def test_missing_and_future_outcome_not_features(self):
        data=fixture();data['actions'][1]=-1
        first=encode(data);self.assertEqual(len(first),3)
        data['states'][-1]['battle_won']=False;data['states'][-1]['battle_lost']=True
        second=encode(data)
        np.testing.assert_array_equal(first[0][0],second[0][0])
        self.assertEqual(first[0][3],-second[0][3])
        row=dict(format='gen4ou',known_nonterminal_actions=3,missing_nonterminal_actions=1,nonterminal_steps=4,result='loss')
        validate_trajectory(data,row)
        data['states'][0]['player_active_pokemon']['hp_pct']=float('nan')
        with self.assertRaises(ValueError):validate_trajectory(data,row)


class LearningTests(unittest.TestCase):
    def problem(self,n):
        rng=np.random.default_rng(701+n)
        x=rng.normal(size=(n,9,12));mask=np.ones((n,9));mask[:,-1]=0
        a=rng.integers(0,8,n);r=rng.choice([-1.,1.],n)
        model=initialize({'featureSchema':'TEST_ONLY','features':list(range(12))},24,123)
        return model,(x,mask,a,r)

    def test_frozen_awr_weight_gradient(self):
        model,b=self.problem(3)
        _,v,_=forward(model,*b[:2]);weights=np.exp(np.clip((b[3]-v)/.5,-3,3))
        _,g=objective(model,*b,awr=True,fixed_weights=weights)
        for k in PARAMS:
            for index in list(np.ndindex(model[k].shape))[:5]:
                old=model[k][index];eps=1e-5
                model[k][index]=old+eps;plus=objective(model,*b,awr=True,fixed_weights=weights)[0]
                model[k][index]=old-eps;minus=objective(model,*b,awr=True,fixed_weights=weights)[0]
                model[k][index]=old
                self.assertAlmostEqual((plus-minus)/(2*eps),g[k][index],places=6)

    def test_tiny_overfit_mask_and_checkpoint(self):
        results=[]
        for n in [1,8,32]:
            model,b=self.problem(n);before=metrics(model,b);opt=Adam(model,.01)
            initial={k:model[k].copy() for k in PARAMS}
            # No-update control: evaluating loss cannot mutate parameters.
            objective(model,*b,awr=True)
            for k in PARAMS:np.testing.assert_array_equal(initial[k],model[k])
            for i in range(400):
                _,g=objective(model,*b,awr=i>=100);opt.step(model,g)
            after=metrics(model,b)
            self.assertEqual(after['action_accuracy'],1)
            self.assertLess(after['action_nll'],before['action_nll']*.05)
            self.assertGreater(sum(np.square(model[k]-initial[k]).sum() for k in PARAMS),0)
            p,v,_=forward(model,*b[:2]);self.assertTrue((p[:,-1]==0).all())
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'test-model.json'
                write_json(path,{k:a.tolist() if isinstance(a,np.ndarray) else a for k,a in model.items()})
                reload=load_model(path)
                np.testing.assert_array_equal(forward(reload,*b[:2])[0],p)
            results.append({'synthetic_samples':n,'before':before,'after':after})
        print(json.dumps({'engineering_sanity_only':results}))


if __name__=='__main__':unittest.main(verbosity=2)
