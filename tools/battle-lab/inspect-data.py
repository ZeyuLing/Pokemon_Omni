"""Audit acquired Metamon samples without importing/running its training stack.

The OU byte prefix is not a downloaded dataset: only complete tar members are
inspected. NU is a fully checksum-verified archive. No missing actions are filled.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile
import zlib


def complete_prefix_members(data):
    raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(data, 64 * 1024 * 1024)
    offset = 0
    while offset + 512 <= len(raw):
        block = raw[offset:offset + 512]
        if not block.strip(b'\0'):
            return
        info = tarfile.TarInfo.frombuf(block, 'utf-8', 'surrogateescape')
        start, end = offset + 512, offset + 512 + info.size
        if end > len(raw):
            return
        if info.isfile():
            yield info.name, raw[start:end]
        offset = start + ((info.size + 511) // 512) * 512


def inspect_trajectory(data):
    states, actions = data['states'], data['actions']
    if not states or len(states) != len(actions):
        raise ValueError('State/action length mismatch or empty trajectory')
    counts = Counter(states=len(states), nonterminal_steps=0, missing_nonterminal_actions=0,
                     known_nonterminal_actions=0, out_of_candidate_range=0, exact_stats_states=0)
    for state, action in zip(states, actions):
        if not isinstance(action, int) or action < -1:
            raise ValueError('Invalid action encoding')
        if state.get('battle_won') and state.get('battle_lost'):
            raise ValueError('Conflicting outcome flags')
        counts['exact_stats_states'] += int('stats' in state['player_active_pokemon'])
        if state.get('battle_won') or state.get('battle_lost'):
            counts['terminal_states'] += 1
            continue
        counts['nonterminal_steps'] += 1
        if action == -1:
            counts['missing_nonterminal_actions'] += 1
        else:
            counts['known_nonterminal_actions'] += 1
            # This is only upstream's MAYBE-valid candidate range, NOT engine legality.
            candidates = set(range(4, 4 + len(state['available_switches'])))
            if not state['forced_switch']:
                n = len(state['player_active_pokemon']['moves'])
                candidates.update(range(n))
                if state.get('can_tera'):
                    candidates.update(range(9, 9 + n))
            counts['out_of_candidate_range'] += int(action not in candidates)
    last = states[-1]
    result = 'win' if last.get('battle_won') else 'loss' if last.get('battle_lost') else 'unresolved'
    return counts, result


def main(root):
    import lz4.frame
    root = Path(root)
    receipt = json.loads((root / 'acquisition.json').read_text('utf-8'))
    for asset in receipt['assets'].values():
        if asset['status'] == 'materialized':
            assert hashlib.sha256((root / asset['file']).read_bytes()).hexdigest() == asset['sha256']
    summary = {'schema': 1, 'purpose': 'data readiness audit, not model training or performance evaluation',
               'lz4_version': __import__('lz4').__version__, 'datasets': {}, 'statistics': {}}
    index = []
    ou_dir = root / 'ou-samples'
    ou_dir.mkdir(exist_ok=True)
    for group in ['gen4nu', 'gen4ou-prefix']:
        if group == 'gen4nu':
            archive = tarfile.open(root / 'metamon/gen4nu.tar.gz')
            members = ((m.name, archive.extractfile(m).read()) for m in archive if m.isfile())
        else:
            archive = None
            members = complete_prefix_members((root / 'metamon/gen4ou.tar.gz.prefix').read_bytes())
        total, results, formats = Counter(), Counter(), Counter()
        battle_ids, state_keys, pokemon_keys = set(), set(), set()
        for name, compressed in members:
            if not name.endswith('.json.lz4'):
                continue
            blob = lz4.frame.decompress(compressed)
            data = json.loads(blob)
            counts, result = inspect_trajectory(data)
            total.update(counts)
            total['trajectories'] += 1
            results[result] += 1
            fmt = data['states'][0]['format']
            formats[fmt] += 1
            state_keys.update(data['states'][0])
            pokemon_keys.update(data['states'][0]['player_active_pokemon'])
            match = re.search(r'((?:smogtours-)?gen\d+[a-z0-9]*-\d+)_', name)
            if not match:
                raise ValueError(f'Cannot identify battle: {name}')
            battle_id = match[1]
            battle_ids.add(battle_id)
            # Both viewpoints of one battle always share the same proposed split.
            bucket = int(hashlib.sha256(battle_id.encode()).hexdigest()[:8], 16) % 10
            row = {'source': group, 'member': name, 'battle_id': battle_id, 'format': fmt,
                   'sha256': hashlib.sha256(compressed).hexdigest(), 'result': result,
                   'candidate_split': 'development' if bucket == 0 else 'train', **dict(counts)}
            index.append(row)
            if group == 'gen4ou-prefix':
                dest = ou_dir / (row['sha256'] + '.json.lz4')
                if dest.exists():
                    assert dest.read_bytes() == compressed
                else:
                    dest.write_bytes(compressed)
        if archive:
            archive.close()
        summary['datasets'][group] = {**dict(total), 'unique_battles': len(battle_ids),
            'outcomes': dict(results), 'formats': dict(formats), 'state_fields': sorted(state_keys),
            'pokemon_fields': sorted(pokemon_keys), 'selection': 'whole archive' if archive else 'complete members in first 2 MiB; nonrandom convenience sample',
            'missing_action_fraction': total['missing_nonterminal_actions'] / max(1, total['nonterminal_steps'])}
    for file in sorted((root / 'stats').glob('*.json')):
        data = json.loads(file.read_text('utf-8'))
        summary['statistics'][file.name] = {'info': data['info'], 'species': len(data['data']),
            'fields': list(next(iter(data['data'].values())))}
    with tarfile.open(root / 'metamon/replay_stats.tar.gz') as archive:
        summary['replay_statistics'] = [{'file': m.name, 'bytes': m.size} for m in archive if m.isfile()]
    (root / 'trajectory-index.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in index), 'utf-8')
    (root / 'inspection.json').write_text(json.dumps(summary, indent=2), 'utf-8')
    print(json.dumps({k: {n:v for n,v in x.items() if n not in ['state_fields','pokemon_fields']} for k,x in summary['datasets'].items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--lz4-path', help='isolated, checksum-verified lz4 wheel extraction')
    args = parser.parse_args()
    if args.lz4_path:
        sys.path.insert(0, str(Path(args.lz4_path).resolve()))
    main(args.root)
