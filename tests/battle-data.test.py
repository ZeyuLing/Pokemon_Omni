"""Data audit contracts; no network or external datasets required."""
import gzip
import importlib.util
import io
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('inspect_data', Path(__file__).resolve().parents[1] / 'tools/battle-lab/inspect-data.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
spec = importlib.util.spec_from_file_location('acquire_data', Path(__file__).resolve().parents[1] / 'tools/battle-lab/acquire-data.py')
acquisition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acquisition)


class AuditTests(unittest.TestCase):
    def test_missing_action_is_not_terminal_or_a_move(self):
        state = {'player_active_pokemon': {'moves': [1,2,3,4]}, 'available_switches': [], 'forced_switch': False}
        counts, result = audit.inspect_trajectory({'states': [state, state, {**state, 'battle_won': True}], 'actions': [0,-1,-1]})
        self.assertEqual(result, 'win')
        self.assertEqual(counts['nonterminal_steps'], 2)
        self.assertEqual(counts['missing_nonterminal_actions'], 1)
        self.assertEqual(counts['known_nonterminal_actions'], 1)

    def test_rejects_misaligned_sequence(self):
        with self.assertRaises(ValueError):
            audit.inspect_trajectory({'states': [{}], 'actions': []})

    def test_prefix_only_yields_complete_members(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w') as tar:
            for name, payload in [('first', b'a'*64), ('second', b'b'*2048)]:
                member = tarfile.TarInfo(name); member.size = len(payload)
                tar.addfile(member, io.BytesIO(payload))
        # Ends inside second member; a readable header is not a complete sample.
        partial_tar = buf.getvalue()[:1800]
        self.assertEqual(list(audit.complete_prefix_members(gzip.compress(partial_tar))), [('first',b'a'*64)])

    def test_cached_prefix_cannot_be_promoted_to_full_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = b'prefix'
            (root/'asset').write_bytes(payload)
            record = {'status':'materialized', 'url':'https://example.com/data', 'bytes':len(payload),
                      'sha256':hashlib.sha256(payload).hexdigest(), 'coverage':'archive_prefix_only'}
            (root/'acquisition.json').write_text(json.dumps({'schema':1,'assets':{'test':record}}))
            asset = {'id':'test','file':'asset','url':record['url'],'max_bytes':100,'acquisition_allowed':True}
            with self.assertRaisesRegex(ValueError, 'prefix cannot satisfy a full asset'):
                acquisition.acquire({'assets':[asset],'max_total_bytes':100}, root)
            asset['range_bytes'] = 8
            with self.assertRaisesRegex(ValueError, 'differs from declared prefix'):
                acquisition.acquire({'assets':[asset],'max_total_bytes':100}, root)
            asset['range_bytes'] = len(payload)
            asset['expected_sha256'] = 'wrong'
            with self.assertRaisesRegex(ValueError, 'differs from declared checksum'):
                acquisition.acquire({'assets':[asset],'max_total_bytes':100}, root)


if __name__ == '__main__':
    unittest.main()
