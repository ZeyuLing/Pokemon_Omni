"""CPU NumPy policy/value learning. No downloads or environment mutation.

All current corpora are authored simulator fixtures: real parameter learning,
but FIXTURE_NON_EMPIRICAL evidence, never a human-strength benchmark.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

# Set before NumPy import to avoid tiny matrices oversubscribing BLAS threads.
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np

HERE = Path(__file__).resolve().parent
PARAMS = ('w', 'b', 'policy', 'value', 'valueBias')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)

def initialize(protocol, hidden, seed):
    rng = np.random.default_rng(seed)
    return dict(schema=protocol['featureSchema'], features=protocol['features'],
                w=rng.normal(0, 1 / np.sqrt(len(protocol['features'])), (len(protocol['features']), hidden)),
                b=np.zeros(hidden), policy=rng.normal(0, 0.1, hidden), value=rng.normal(0, 0.1, hidden), valueBias=np.array(0.0))

def load_model(path):
    model = json.loads(Path(path).read_text(encoding='utf-8'))
    for key in PARAMS:
        model[key] = np.asarray(model[key], dtype=np.float64)
        if not np.isfinite(model[key]).all():
            raise ValueError('Nonfinite checkpoint')
    return model

def save_model(path, model):
    write(path, {k: model[k].tolist() if k in PARAMS else model[k] for k in model})

def forward(model, x, mask):
    h = np.tanh(x @ model['w'] + model['b'])
    logits = h @ model['policy']
    logits = np.where(mask, logits, -1e30)
    probabilities = np.exp(logits - logits.max(axis=1, keepdims=True)) * mask
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    counts = mask.sum(axis=1, keepdims=True)
    pooled = (h * mask[:, :, None]).sum(axis=1) / counts
    value = np.tanh(pooled @ model['value'] + model['valueBias'])
    return probabilities, value, (h, pooled, counts)

def objective(model, batch, mode='bc', value_weight=0.25, entropy_weight=0.01):
    x, mask, target, returns, actions = batch
    p, v, (h, pooled, counts) = forward(model, x, mask)
    n = len(x)
    logp = np.log(np.maximum(p, 1e-30))
    if mode == 'bc':
        policy_loss = -(target * logp).sum(axis=1).mean()
        dlogits = (p - target) / n
    else:
        # One Monte Carlo actor-critic update on the collecting checkpoint.
        # Stop-gradient advantage; no stale multi-epoch REINFORCE updates.
        advantage = returns - v
        chosen = np.zeros_like(p)
        chosen[np.arange(n), actions] = 1
        policy_loss = -(advantage * logp[np.arange(n), actions]).mean()
        dlogits = (p - chosen) * advantage[:, None] / n
    neg_entropy = (p * logp).sum(axis=1)
    policy_loss += entropy_weight * neg_entropy.mean()
    dlogits += entropy_weight * p * (logp - neg_entropy[:, None]) / n
    value_loss = np.mean((v - returns) ** 2)
    dv = value_weight * 2 * (v - returns) * (1 - v * v) / n
    gradients = {'policy': np.einsum('nah,na->h', h, dlogits),
                 'value': pooled.T @ dv, 'valueBias': dv.sum()}
    dh = dlogits[:, :, None] * model['policy'] + (dv[:, None] * model['value'])[:, None, :] * mask[:, :, None] / counts[:, :, None]
    dz = dh * (1 - h * h)
    gradients['w'] = np.einsum('nad,nah->dh', x, dz)
    gradients['b'] = dz.sum(axis=(0, 1))
    loss = policy_loss + value_weight * value_loss
    if not np.isfinite(loss) or any(not np.isfinite(g).all() for g in gradients.values()):
        raise FloatingPointError('Nonfinite loss/gradient')
    return float(loss), gradients

class Adam:
    def __init__(self, model, lr):
        self.lr, self.t = lr, 0
        self.m = {k: np.zeros_like(model[k]) for k in PARAMS}
        self.v = {k: np.zeros_like(model[k]) for k in PARAMS}

    def step(self, model, gradients):
        self.t += 1
        norm = np.sqrt(sum(np.sum(g * g) for g in gradients.values()))
        scale = min(1.0, 5.0 / max(norm, 1e-30))
        for k in PARAMS:
            g = gradients[k] * scale
            self.m[k] = 0.9 * self.m[k] + 0.1 * g
            self.v[k] = 0.999 * self.v[k] + 0.001 * g * g
            model[k] -= self.lr * (self.m[k] / (1 - 0.9 ** self.t)) / (np.sqrt(self.v[k] / (1 - 0.999 ** self.t)) + 1e-8)

def read_data(path, protocol, split):
    path = Path(path)
    report = json.loads((path.parent / 'report.json').read_text(encoding='utf-8'))
    if report['sampleHash'] != sha(path) or report['manifest']['protocolHash'] != sha(protocol):
        raise ValueError('Data or protocol hash mismatch')
    if report['manifest']['split'] != split or split not in ('train', 'development'):
        raise ValueError('Training must never read protected data')
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    if len(rows) != report['samples'] or len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Bad sample count or duplicate IDs')
    if not rows:
        raise ValueError('No eligible completed-episode samples')
    x = np.asarray([r['x'] for r in rows], dtype=np.float64)
    mask = np.asarray([r['mask'] for r in rows], dtype=np.float64)
    teacher = np.asarray([r['teacher'] for r in rows], dtype=np.float64)
    returns = np.asarray([r['targetValue'] for r in rows], dtype=np.float64)
    actions = np.asarray([r['action'] for r in rows], dtype=np.int64)
    spec = json.loads(Path(protocol).read_text(encoding='utf-8'))
    if x.shape != (len(rows), 9, len(spec['features'])) or mask.shape != x.shape[:2] or teacher.shape != mask.shape:
        raise ValueError('Bad feature dimensions')
    if not all(np.isfinite(a).all() for a in (x, mask, teacher, returns)) or not np.isin(mask, [0, 1]).all():
        raise ValueError('Nonfinite data or bad mask')
    if not (mask.sum(axis=1) > 0).all() or (actions < 0).any() or (actions >= 9).any() or not mask[np.arange(len(rows)), actions].all():
        raise ValueError('Invalid action labels')
    if not np.allclose(teacher.sum(axis=1), 1) or (teacher < 0).any() or (teacher * (1-mask)).any() or (np.abs(returns) > 1).any():
        raise ValueError('Invalid learning targets')
    return (x, mask, teacher, returns, actions), rows, report

def take(data, indices):
    return tuple(a[indices] for a in data)

def metrics(model, data):
    sums = np.zeros(3)
    for start in range(0, len(data[0]), 512):
        x, mask, teacher, returns, _ = take(data, slice(start, start+512))
        p, v, _ = forward(model, x, mask)
        correct = teacher[np.arange(len(p)), p.argmax(axis=1)] > 0
        sums += [-(teacher*np.log(np.maximum(p, 1e-30))).sum(), ((v-returns)**2).sum(), correct.sum()]
    ce, mse, acc = sums / len(data[0])
    return {'samples': len(data[0]), 'policyCrossEntropy': float(ce), 'valueMSE': float(mse), 'teacherAgreement': float(acc)}

def sanity(protocol, data, out):
    # Choose distinct nontrivial decisions; single legal actions cannot prove learning.
    seen, indices = set(), []
    for i, (x, mask) in enumerate(zip(data[0], data[1])):
        key = x.tobytes()
        if mask.sum() > 1 and key not in seen:
            seen.add(key); indices.append(i)
        if len(indices) == 32:
            break
    if len(indices) < 32:
        raise ValueError('Need 32 distinct multi-action sanity examples')
    tiny = take(data, indices[:8])
    model = initialize(protocol, 64, 91)
    loss, gradients = objective(model, tiny)
    assert loss == objective(model, tiny)[0]
    max_error = 0.0
    for key in PARAMS:
        for j in [0, model[key].size//2, model[key].size-1]:
            original = model[key].flat[j]
            model[key].flat[j] = original + 1e-5; plus = objective(model, tiny)[0]
            model[key].flat[j] = original - 1e-5; minus = objective(model, tiny)[0]
            model[key].flat[j] = original
            max_error = max(max_error, abs((plus-minus)/2e-5 - np.asarray(gradients[key]).flat[j]))
    assert max_error < 1e-6, max_error
    before = {k: model[k].copy() for k in PARAMS}
    Adam(model, 0.003).step(model, gradients)
    deltas = {k: float(np.linalg.norm(model[k]-before[k])) for k in PARAMS}
    assert all(delta > 0 for delta in deltas.values()), deltas
    save_model(out/'roundtrip.json', model)
    restored = load_model(out/'roundtrip.json')
    for a, b in zip(forward(model, tiny[0], tiny[1])[:2], forward(restored, tiny[0], tiny[1])[:2]):
        np.testing.assert_array_equal(a, b)
    write(out/'inference-input.json', {'x': tiny[0][0].tolist(), 'mask': tiny[1][0].tolist()})
    javascript = "const fs=require('fs');const n=require('./tools/battle-lab/network.cjs');console.log(JSON.stringify(n.infer(n.loadNetwork(process.argv[1]),JSON.parse(fs.readFileSync(process.argv[2],'utf8')))));"
    actual = json.loads(subprocess.check_output(['node', '-e', javascript, str(out/'roundtrip.json'), str(out/'inference-input.json')], cwd=HERE.parent.parent, text=True))
    p, v, _ = forward(model, tiny[0][:1], tiny[1][:1])
    np.testing.assert_allclose(actual['probabilities'], p[0], atol=1e-10, rtol=1e-10)
    np.testing.assert_allclose(actual['value'], v[0], atol=1e-10, rtol=1e-10)
    ladder = []
    for n in (1, 8, 32):
        subset = take(data, indices[:n]); m = initialize(protocol, 64, 90+n)
        initial = metrics(m, subset); optimizer = Adam(m, 0.01)
        for _ in range(1200):
            _, g = objective(m, subset, entropy_weight=0)
            optimizer.step(m, g)
        final = metrics(m, subset)
        assert final['teacherAgreement'] >= 0.99 and final['valueMSE'] < 0.03, (n, final)
        assert final['policyCrossEntropy'] < initial['policyCrossEntropy'], (n, initial, final)
        ladder.append({'examples': n, 'initial': initial, 'final': final})
    # No-update negative control must stay bit-identical, not silently learn.
    control = initialize(protocol, 64, 91); control_before = metrics(control, tiny)
    for _ in range(10): objective(control, tiny)
    assert control_before == metrics(control, tiny)
    return {'evidenceClass': 'ENGINEERING_VALIDATION', 'finiteDifferenceMaxError': max_error, 'parameterDeltas': deltas,
            'checkpointRoundtrip': True, 'javascriptParity': True, 'noUpdateControl': True, 'tinyOverfit': ladder}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['sanity', 'train', 'rl'])
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--validation')
    parser.add_argument('--out', required=True)
    parser.add_argument('--model')
    parser.add_argument('--hidden', type=int, default=64)
    parser.add_argument('--seed', type=int, default=13)
    parser.add_argument('--epochs', type=int, default=16)
    parser.add_argument('--batch', type=int, default=128)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--lr', type=float, default=0.003)
    args = parser.parse_args()
    if args.hidden < 1 or args.epochs < 1 or args.batch < 1 or args.lr <= 0 or (args.limit is not None and args.limit < 1):
        raise ValueError('Invalid training parameters')
    protocol = json.loads(Path(args.protocol).read_text(encoding='utf-8'))
    data, rows, source_report = read_data(args.data, args.protocol, 'train')
    if args.limit: data = take(data, slice(0, args.limit)); rows = rows[:args.limit]
    validation = read_data(args.validation, args.protocol, 'development')[0] if args.validation else None
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    environment = {'python': sys.version, 'executableHash': sha(sys.executable), 'numpy': np.__version__,
                   'packages': sorted([[d.metadata['Name'], d.version] for d in importlib.metadata.distributions()]),
                   'bootstrap': 'not required: existing runtime; no installation or fallback',
                   'blas': np.__config__.CONFIG}
    write(out/'environment.json', environment)
    manifest = {'trainingMode': 'full_training', 'evidenceClass': 'FIXTURE_NON_EMPIRICAL', 'args': vars(args),
                'dataHash': sha(args.data), 'validationHash': sha(args.validation) if args.validation else None,
                'protocolHash': sha(args.protocol), 'trainerHash': sha(__file__), 'dataSource': source_report['manifest'],
                'initialModelHash': sha(args.model) if args.model else None, 'sampleCount': len(rows),
                'sampleIdsHash': hashlib.sha256('\n'.join(r['id'] for r in rows).encode()).hexdigest()}
    write(out/'manifest.json', manifest)
    started = time.perf_counter()
    if args.mode == 'sanity':
        report = sanity(protocol, data, out); write(out/'sanity.json', report)
        print(json.dumps(report)); return
    model = load_model(args.model) if args.model else initialize(protocol, args.hidden, args.seed)
    if model['features'] != protocol['features'] or model['schema'] != protocol['featureSchema']:
        raise ValueError('Checkpoint schema mismatch')
    save_model(out/'initial.json', model)
    initial = {k: model[k].copy() for k in PARAMS}
    before = {'train': metrics(model, data), 'development': metrics(model, validation) if validation else None}
    optimizer = Adam(model, args.lr); rng = np.random.default_rng(args.seed); history = []
    if args.mode == 'rl':
        if not args.model or source_report['manifest']['mode'] != 'selfplay' or source_report['manifest']['modelHash'] != sha(args.model):
            raise ValueError('On-policy update requires trajectories collected by this exact checkpoint')
        if args.epochs != 1: raise ValueError('REINFORCE permits one full-batch update per fresh collection')
        if source_report['summary']['truncated']:
            raise ValueError('Cannot condition on completed rollouts for on-policy learning; censored batches require an explicit bootstrap implementation')
        p, v, _ = forward(model, data[0], data[1])
        np.testing.assert_allclose(p[np.arange(len(rows)), data[4]], [r['oldProbability'] for r in rows], atol=1e-10)
        np.testing.assert_allclose(v, [r['oldValue'] for r in rows], atol=1e-10)
        loss, gradient = objective(model, data, mode='rl')
        optimizer.step(model, gradient); history.append({'epoch': 1, 'loss': loss})
    else:
        for epoch in range(args.epochs):
            order = rng.permutation(len(data[0])); total = 0.0
            for start in range(0, len(order), args.batch):
                indices = order[start:start+args.batch]
                loss, gradient = objective(model, take(data, indices))
                optimizer.step(model, gradient); total += loss * len(indices)
            entry = {'epoch': epoch+1, 'loss': total/len(order)}
            history.append(entry)
            print(json.dumps(entry), flush=True)
    save_model(out/'model.json', model)
    # Optimizer state is preserved for audits; subsequent RL stages deliberately
    # start a fresh Adam state and record this, rather than claiming exact resume.
    np.savez(out/'optimizer.npz', **{f'm_{k}': v for k,v in optimizer.m.items()},
             **{f'v_{k}': v for k,v in optimizer.v.items()}, steps=optimizer.t, learning_rate=optimizer.lr)
    after = {'train': metrics(model, data), 'development': metrics(model, validation) if validation else None}
    report = {'evidenceClass': 'FIXTURE_NON_EMPIRICAL', 'before': before, 'after': after, 'history': history,
              'optimizerSteps': optimizer.t, 'parameterCount': sum(model[k].size for k in PARAMS),
              'parameterDeltas': {k: float(np.linalg.norm(model[k]-initial[k])) for k in PARAMS},
              'modelHash': sha(out/'model.json'), 'seconds': time.perf_counter()-started}
    write(out/'report.json', report); print(json.dumps(report, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
