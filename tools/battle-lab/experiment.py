"""Reproducible engineering training run, with bounded compute and immutable logs.

Does not install dependencies, download data, or consume protected evaluation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from train import sha, write

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--train-blocks', type=int, default=64)
    parser.add_argument('--rounds', type=int, default=16)
    parser.add_argument('--selfplay-blocks', type=int, default=16)
    args = parser.parse_args()
    if not 8 <= args.train_blocks <= 256 or not 1 <= args.rounds <= 100 or not 1 <= args.selfplay_blocks <= 256:
        raise ValueError('Invalid bounded experiment budget')
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    (out/'data').mkdir(); (out/'runs').mkdir(); (out/'logs').mkdir()
    budget = {'evidenceClass': 'FIXTURE_NON_EMPIRICAL', 'trainingMode': 'full_training', 'args': vars(args),
              'sourceHashes': {p.name: sha(p) for p in HERE.iterdir() if p.suffix in ('.py', '.cjs')},
              'protectedEvaluation': 'Not invoked by this implementation/selection runner',
              'inferenceComputeScale': 'not_applicable: single feedforward pass, no search or sample-budget study',
              'scientificClaims': 'None. Establish parameter learning and auditable rollout/update execution on authored fixtures.'}
    write(out/'experiment.json', budget)
    def execute(name, command):
        started = time.perf_counter()
        print(f'RUN {name}', flush=True)
        with (out/'logs'/f'{name}.log').open('x', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=HERE.parent.parent, stdout=log, stderr=subprocess.STDOUT, text=True)
        write(out/'logs'/f'{name}.receipt.json', {'argv': command, 'exitCode': result.returncode,
                                                'seconds': time.perf_counter()-started})
        if result.returncode: raise RuntimeError(f'{name} failed; inspect immutable logs')
    protocol = str(out/'data'/'protocol.json')
    execute('prepare', ['node', str(HERE/'learning.cjs'), 'prepare', '--protocol', protocol])
    for split, blocks in [('train', args.train_blocks), ('development', 8)]:
        execute(f'data-{split}', ['node', str(HERE/'learning.cjs'), 'dataset', '--protocol', protocol, '--split', split,
                                '--blocks', str(blocks), '--out', str(out/'data'/split)])
    data = str(out/'data'/'train'/'samples.jsonl'); validation = str(out/'data'/'development'/'samples.jsonl')
    common = ['--protocol', protocol, '--data', data]
    execute('sanity', [sys.executable, str(HERE/'train.py'), 'sanity', *common, '--out', str(out/'runs'/'sanity')])
    # No downstream scheduling before all production-path checks have passed.
    sanity = json.loads((out/'runs'/'sanity'/'sanity.json').read_text(encoding='utf-8'))
    if not all(sanity[key] for key in ('checkpointRoundtrip', 'javascriptParity', 'noUpdateControl')):
        raise RuntimeError('Learning gate failed')
    for hidden in (16, 64):
        for size in ('small', 'full'):
            name = f'bc-h{hidden}-{size}'
            execute(name, [sys.executable, str(HERE/'train.py'), 'train', *common, '--validation', validation,
                           '--hidden', str(hidden), '--epochs', '16', '--out', str(out/'runs'/name),
                           *(['--limit', '2815'] if size == 'small' else [])])
    bc = out/'runs'/'bc-h64-full'/'model.json'
    execute('selfplay', [sys.executable, str(HERE/'selfplay.py'), '--protocol', protocol, '--model', str(bc),
                         '--rounds', str(args.rounds), '--blocks', str(args.selfplay_blocks), '--out', str(out/'runs'/'selfplay')])
    rl = out/'runs'/'selfplay'/f'update-{args.rounds-1:03d}'/'model.json'
    candidates = {'initial': out/'runs'/'bc-h64-full'/'initial.json', 'bc': bc, 'rl': rl, 'power': None}
    for name, model in candidates.items():
        execute(f'dev-{name}', ['node', str(HERE/'learning.cjs'), 'evaluate', '--protocol', protocol,
                                '--split', 'development', '--blocks', '24', '--out', str(out/'runs'/f'dev-{name}'),
                                *(['--model', str(model)] if model else [])])
    write(out/'complete.json', {'evidenceClass': 'FIXTURE_NON_EMPIRICAL', 'stage': 'learning-engineering-complete',
                               'candidates': {name: {'path': str(p), 'sha256': sha(p)} for name,p in candidates.items() if p},
                               'next': 'Independent protected evaluation and real-data/strong-baseline acquisition; no superhuman claim'})
    print(json.dumps({'complete': str(out/'complete.json'), 'model': str(bc)}), flush=True)

if __name__ == '__main__':
    main()
