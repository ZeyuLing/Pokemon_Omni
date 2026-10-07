"""Explicit human-review registry. No legacy data discovery or automatic approval."""
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tarfile
import threading

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'build/battle-data/2026-10-07'
WORK = ROOT / 'build/battle-review'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), 'utf-8')
    temp.replace(path)


def action_label(state, action):
    if state.get('battle_won') or state.get('battle_lost'):
        return '对局结束'
    if action == -1:
        return '动作未记录'
    if action < 4:
        moves = sorted(state['player_active_pokemon']['moves'], key=lambda m: m['name'])
        return '招式 · ' + (moves[action]['name'] if action < len(moves) else '特殊强制动作')
    if 4 <= action < 9:
        team = sorted(state['available_switches'], key=lambda p: p['name'])
        return '换入 · ' + (team[action-4]['name'] if action-4 < len(team) else '未知槽位')
    return '特殊机制动作 · ' + str(action)


def validate_trajectory(data, row):
    states,actions=data['states'],data['actions']
    if len(states)!=len(actions) or not states:
        raise ValueError('Empty or misaligned trajectory')
    missing=known=0
    for i,(s,a) in enumerate(zip(states,actions)):
        terminal=bool(s.get('battle_won') or s.get('battle_lost'))
        if terminal!=(i==len(states)-1) or (s.get('battle_won') and s.get('battle_lost')):
            raise ValueError('Invalid terminal boundary')
        if s['format']!=row['format'] or type(a) is not int or a < -1 or a > 8:
            raise ValueError('Format or action schema mismatch')
        mons=[s['player_active_pokemon'],s['opponent_active_pokemon'],*s['available_switches']]
        for p in mons:
            if not math.isfinite(p['hp_pct']) or not 0<=p['hp_pct']<=1 or len(p['moves'])>4:
                raise ValueError('Invalid HP or move count')
        if terminal:continue
        if a==-1:missing+=1;continue
        if (a<4 and (s['forced_switch'] or a>=len(mons[0]['moves']))) or (a>=4 and a-4>=len(s['available_switches'])):
            raise ValueError('Recorded action is outside reconstructed candidates')
        known+=1
    if (known!=row['known_nonterminal_actions'] or missing!=row['missing_nonterminal_actions']
            or len(states)-1!=row['nonterminal_steps']
            or bool(states[-1]['battle_won'])!=(row['result']=='win')):
        raise ValueError('Trajectory content does not match audit index')


class ReviewStore:
    def __init__(self, source=SOURCE, work=WORK, verify=True):
        self.source, self.work = Path(source), Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.review_path = self.work / 'reviews.json'
        self.reviews = json.loads(self.review_path.read_text('utf-8')) if self.review_path.exists() else {}
        if verify:
            inventory = json.loads((ROOT / 'research/battle-data/2026-10-07/artifact-index.json').read_text('utf-8'))
            index_record = next(x for x in inventory['assets'] if x['path'].endswith('/trajectory-index.jsonl'))
            if digest((self.source/'trajectory-index.jsonl').read_bytes()) != index_record['sha256']:
                raise ValueError('Source trajectory index checksum mismatch')
            receipt = json.loads((self.source/'acquisition.json').read_text('utf-8'))
            for key in ['gen4nu.tar.gz','gen4ou-prefix']:
                asset = receipt['assets'][key]
                lock = json.loads((ROOT/'research/battle-data/2026-10-07/acquisition-lock.json').read_text('utf-8'))
                expected = next(x for x in lock['assets'] if x['id'] == key)['expected_sha256']
                if digest((self.source/asset['file']).read_bytes()) != expected:
                    raise ValueError('Source archive checksum mismatch')
        self.rows = {}
        for line in (self.source/'trajectory-index.jsonl').read_text('utf-8').splitlines():
            row = json.loads(line)
            if row['source'] not in ('gen4nu','gen4ou-prefix'):
                raise ValueError('Unregistered data source')
            row['id'] = digest((row['source']+'/'+row['member']).encode())[:20]
            row['missing_fraction'] = row['missing_nonterminal_actions']/max(1,row['nonterminal_steps'])
            row['license'] = 'CC BY-NC 4.0'
            row['provenance'] = 'human_reconstructed'
            self.rows[row['id']] = row

    def status(self, row):
        review = self.reviews.get(row['id'], {})
        return review.get('status','pending') if review.get('sha256') == row['sha256'] else 'pending'

    def summary(self):
        counts = {'pending':0,'approved':0,'rejected':0}
        for row in self.rows.values():
            counts[self.status(row)] += 1
        return {'total':len(self.rows), 'battles':len({r['battle_id'] for r in self.rows.values()}),
                **counts, 'known_actions':sum(r['known_nonterminal_actions'] for r in self.rows.values()),
                'sources':['gen4ou-prefix','gen4nu'], 'scope':'非商业研究试训',
                'legacy_data':'已隔离，训练入口不扫描旧目录'}

    def list_rows(self, query='', source='', status='', missing='', offset=0, limit=30):
        rows = [r for r in self.rows.values() if (not query or query.lower() in (r['battle_id']+' '+r['id']).lower())
                and (not source or r['source']==source) and (not status or self.status(r)==status)
                and (missing != 'yes' or r['missing_nonterminal_actions'] > 0)
                and (missing != 'no' or r['missing_nonterminal_actions'] == 0)]
        rows.sort(key=lambda r:(r['source'] != 'gen4ou-prefix',r['battle_id'],r['id']))
        return {'total':len(rows), 'rows':[{**r,'review_status':self.status(r)} for r in rows[offset:offset+limit]]}

    @lru_cache(maxsize=12)
    def load(self, case_id):
        row = self.rows[case_id]
        if row['source']=='gen4ou-prefix':
            raw=(self.source/'ou-samples'/(row['sha256']+'.json.lz4')).read_bytes()
        else:
            with tarfile.open(self.source/'metamon/gen4nu.tar.gz') as archive:
                member = archive.getmember(row['member'])
                if not member.isfile() or member.size > 10_000_000:
                    raise ValueError('Invalid trajectory member')
                raw=archive.extractfile(member).read()
        if digest(raw) != row['sha256']:
            raise ValueError('Trajectory checksum mismatch; cannot review or train')
        sys.path.insert(0,str(self.source/'runtime/lz4-4.4.5')) if str(self.source/'runtime/lz4-4.4.5') not in sys.path else None
        import lz4.frame
        data=json.loads(lz4.frame.decompress(raw))
        validate_trajectory(data,row)
        return data

    def detail(self, case_id):
        data=self.load(case_id);row=self.rows[case_id]
        return {'record':{**row,'review_status':self.status(row)},'review':self.reviews.get(case_id),
                'states':data['states'],'actions':data['actions'],
                'action_labels':[action_label(s,a) for s,a in zip(data['states'],data['actions'])],
                'limitations':['人类旁观录像重建；我方配置也可能经过推测补全',
                    '只有种族值，缺少培养后的完整实际能力值',
                    '候选动作范围不是引擎确认的精确合法动作',
                    '缺失动作必须屏蔽；本页为状态序列回放，不是原始战斗动画',
                    '仅非商业研究；审批不改变来源许可或缺失字段']}

    def review(self, case_id, status, sha256, note, acknowledged=False):
        with self.lock:
            row=self.rows[case_id]
            if sha256 != row['sha256']:
                raise ValueError('Content changed; reload before reviewing')
            if status not in ('pending','approved','rejected'):
                raise ValueError('Invalid review status')
            if status=='approved':
                if not acknowledged or len(note.strip())<4:
                    raise ValueError('请确认研究用途及缺失信息，并填写审核依据（至少 4 个字符）')
                if row['result'] not in ('win','loss') or row['out_of_candidate_range'] or row['known_nonterminal_actions']<4:
                    raise ValueError('未通过基础完整性检查，不能批准训练')
                self.load.cache_clear()
                self.load(case_id)
            record={'status':status,'sha256':sha256,'note':note[:2000],
                    'scope':'noncommercial_research_only','actor':'human_review_ui',
                    'updated_at':datetime.now(timezone.utc).isoformat()}
            self.reviews[case_id]=record
            write_json(self.review_path,self.reviews)
            with (self.work/'review-events.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps({'id':case_id,**record},ensure_ascii=False)+'\n')
            return record

    def training_snapshot(self):
        self.load.cache_clear()
        rows=[r for r in self.rows.values() if self.status(r)=='approved']
        groups=sorted({r['battle_id'] for r in rows},key=lambda b:digest(b.encode()))
        if len(groups)<4:
            raise ValueError(f'需要人工批准至少 4 个不同对局；当前 {len(groups)} 个。未批准数据不会用于训练。')
        # A fresh run's holdout is explicit and battle-grouped, never POV-random.
        dev=set(groups[:max(1,len(groups)//5)])
        cases=[]
        for row in rows:
            self.load(row['id'])
            cases.append({'id':row['id'],'sha256':row['sha256'],'battle_id':row['battle_id'],
                          'split':'development' if row['battle_id'] in dev else 'train',
                          'review':self.reviews[row['id']]})
        return {'schema':1,'scope':'NONCOMMERCIAL_RESEARCH_PILOT',
                'algorithm':'Monte Carlo advantage-weighted regression (offline RL pilot)',
                'limitations':['reconstructed observations','missing action loss masked','not exact-state deployment agent'],
                'cases':cases}

    def validate_snapshot(self, snapshot):
        """Read persisted approvals again: another process may have revoked them."""
        reviews=json.loads(self.review_path.read_text('utf-8')) if self.review_path.exists() else {}
        for case in snapshot['cases']:
            row=self.rows.get(case['id'])
            if (not row or row['sha256']!=case['sha256']
                    or reviews.get(case['id'])!=case['review']
                    or case['review'].get('status')!='approved'):
                raise ValueError('Human approval changed; training artifact is invalid')

    def invalidate_runs(self):
        """Persist withdrawal across server restarts and all historical runs."""
        for path in (self.work/'runs').glob('*/snapshot.json'):
            try:
                self.validate_snapshot(json.loads(path.read_text('utf-8')))
            except (ValueError, KeyError):
                write_json(path.parent/'INVALIDATED.json',{'reason':'human review changed'})
