"""Bounded fresh-rollout / actor-critic loop. Logs every command and checkpoint."""
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
    p = argparse.ArgumentParser()
    p.add_argument('--protocol', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--rounds', type=int, default=16)
    p.add_argument('--blocks', type=int, default=16)
    args = p.parse_args()
    if not 1 <= args.rounds <= 100 or not 1 <= args.blocks <= 256:
        raise ValueError('Bounded rounds 1..100 and blocks 1..256 required')
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    model = str(Path(args.model).resolve()); protocol = str(Path(args.protocol).resolve())
    manifest = {'evidenceClass': 'FIXTURE_NON_EMPIRICAL', 'args': vars(args), 'protocolHash': sha(protocol),
                'initialModelHash': sha(model), 'trainerHash': sha(HERE/'train.py'), 'runnerHash': sha(__file__),
                'algorithm': 'Fresh selfplay, one full-batch Monte Carlo actor-critic update per round, fresh Adam lr=0.0003'}
    write(out/'manifest.json', manifest)
    started = time.perf_counter(); receipts = []
    for r in range(args.rounds):
        rollout = out/f'rollout-{r:03d}'; update = out/f'update-{r:03d}'
        commands = [
            ['node', str(HERE/'learning.cjs'), 'selfplay', '--protocol', protocol, '--split', 'train',
             '--blocks', str(args.blocks), '--seed-offset', str(100000+r*1000), '--model', model, '--out', str(rollout)],
            [sys.executable, str(HERE/'train.py'), 'rl', '--protocol', protocol, '--data', str(rollout/'samples.jsonl'),
             '--model', model, '--epochs', '1', '--lr', '0.0003', '--out', str(update)],
        ]
        for operation, command in zip(('collect', 'update'), commands):
            begin = time.perf_counter()
            with (out/f'{r:03d}-{operation}.log').open('x', encoding='utf-8') as log:
                result = subprocess.run(command, cwd=HERE.parent.parent, stdout=log, stderr=subprocess.STDOUT, text=True)
            receipt = {'round': r, 'operation': operation, 'argv': command, 'exitCode': result.returncode, 'seconds': time.perf_counter()-begin}
            receipts.append(receipt); write(out/f'{r:03d}-{operation}.receipt.json', receipt)
            if result.returncode:
                raise RuntimeError(f'Round {r} {operation} failed; immutable logs preserved')
        report = json.loads((update/'report.json').read_text(encoding='utf-8'))
        model = str(update/'model.json')
        print(json.dumps({'round': r+1, 'model': model, 'optimizerSteps': report['optimizerSteps'],
                          'valueMSE': report['after']['train']['valueMSE']}), flush=True)
    write(out/'report.json', {'evidenceClass': 'FIXTURE_NON_EMPIRICAL', 'rounds': args.rounds, 'games': args.rounds*args.blocks*4,
                              'optimizerSteps': args.rounds, 'finalModel': model, 'finalModelHash': sha(model),
                              'seconds': time.perf_counter()-started, 'receipts': receipts})

if __name__ == '__main__':
    main()
