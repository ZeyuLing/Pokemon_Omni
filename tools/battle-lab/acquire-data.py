"""Bounded, manifest-driven acquisition. No training or dependency installation.

Range assets are explicitly archive prefixes, NEVER complete verified archives.
Unknown-license sources can be inventoried, but payload acquisition is excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from datetime import datetime, timezone


def sha(data):
    return hashlib.sha256(data).hexdigest()


def acquire(plan, root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt_path = root / 'acquisition.json'
    receipt = json.loads(receipt_path.read_text('utf-8')) if receipt_path.exists() else {'schema': 1, 'assets': {}}
    if sum(a.get('range_bytes', a['max_bytes']) for a in plan['assets']) > plan['max_total_bytes']:
        raise ValueError('Declared assets exceed total byte budget')
    for asset in plan['assets']:
        if not asset.get('acquisition_allowed'):
            raise ValueError(f"Acquisition not authorized: {asset['id']}")
        dest = (root / asset['file']).resolve()
        if not dest.is_relative_to(root):
            raise ValueError('Asset path escapes acquisition root')
        previous = receipt['assets'].get(asset['id'])
        if dest.exists():
            if not previous or previous.get('status') != 'materialized' or sha(dest.read_bytes()) != previous['sha256'] or previous['url'] != asset['url']:
                raise ValueError(f'Existing asset cannot be verified: {dest}')
            if asset.get('expected_sha256') and previous['sha256'] != asset['expected_sha256']:
                raise ValueError('Cached asset differs from declared checksum')
            if asset.get('expected_bytes') is not None and previous['bytes'] != asset['expected_bytes']:
                raise ValueError('Cached asset differs from declared size')
            if previous['bytes'] > asset['max_bytes']:
                raise ValueError('Cached asset exceeds current size bound')
            if 'range_bytes' in asset and (previous['bytes'] != asset['range_bytes'] or previous.get('coverage') != 'archive_prefix_only'):
                raise ValueError('Cached asset differs from declared prefix')
            if 'range_bytes' not in asset and previous.get('coverage') != 'complete_response':
                raise ValueError('A cached prefix cannot satisfy a full asset')
            print(f"cached {asset['id']}", flush=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        headers = {'User-Agent': 'Pokemon-Omni-data-audit/1.0', 'Accept-Encoding': 'identity'}
        limit = asset.get('range_bytes', asset['max_bytes'])
        if 'range_bytes' in asset:
            headers['Range'] = f'bytes=0-{limit - 1}'
        record = {'url': asset['url'], 'file': asset['file'], 'license': asset['license'],
                  'purpose': asset['purpose'], 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                  'attempt_errors': []}
        for attempt in range(2):
            try:
                with urllib.request.urlopen(urllib.request.Request(asset['url'], headers=headers), timeout=45) as response:
                    if 'range_bytes' in asset and (response.status != 206 or not response.headers.get('Content-Range', '').startswith(f'bytes 0-{limit-1}/')):
                        raise ValueError('Server did not honor exact byte range')
                    if int(response.headers.get('Content-Length', '0')) > limit:
                        raise ValueError('Response exceeds declared bound')
                    data = response.read(limit + 1)
                    if len(data) > limit:
                        raise ValueError('Response exceeds declared bound')
                    if 'range_bytes' in asset and len(data) != limit:
                        raise ValueError('Incomplete range response')
                    if asset.get('expected_bytes') is not None and len(data) != asset['expected_bytes']:
                        raise ValueError('Size mismatch')
                    if asset.get('expected_sha256') and sha(data) != asset['expected_sha256']:
                        raise ValueError('Checksum mismatch')
                    record.update(status='materialized', bytes=len(data), sha256=sha(data),
                                  content_range=response.headers.get('Content-Range'),
                                  coverage='archive_prefix_only' if 'range_bytes' in asset else 'complete_response')
                dest.write_bytes(data)
                break
            except Exception as exc:
                record.update(status='failed', error=str(exc))
                record['attempt_errors'].append(str(exc))
                if attempt == 0:
                    time.sleep(1)
        receipt['assets'][asset['id']] = record
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), 'utf-8')
        print(f"{record['status']} {asset['id']} {record.get('bytes', record.get('error'))}", flush=True)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    receipt = acquire(json.loads(Path(args.plan).read_text('utf-8')), args.out)
    raise SystemExit(1 if any(a['status'] != 'materialized' for a in receipt['assets'].values()) else 0)
