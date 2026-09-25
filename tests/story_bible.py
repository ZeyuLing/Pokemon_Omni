"""Continuity errors that must fail before dossiers are regenerated."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bible',ROOT/'tools/build_story_bible.py')
bible=importlib.util.module_from_spec(spec);spec.loader.exec_module(bible)


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.world=bible.read('content/story/worldline.json')
        self.people=bible.read('content/story/characters.json')['characters']
        self.atlas=bible.read('content/story/atlas.json')
        self.media=bible.read('research/narrative/reference-media.json')['media']

    def validate(self):
        bible.validate(self.world,self.people,self.atlas,self.media)

    def test_current_registry(self):
        self.validate()

    def test_unknown_actor(self):
        self.world['events'][0]['participants']['unknown']='Unregistered role'
        with self.assertRaisesRegex(AssertionError,'Unregistered'):self.validate()

    def test_dead_character_cannot_reappear(self):
        self.world['events'][-1]['participants']['juan']='Alive in 1967'
        with self.assertRaisesRegex(AssertionError,'Post-death'):self.validate()

    def test_candidate_not_silently_adopted(self):
        self.world['events'][-1]['participants']['wallace']='Unwritten future'
        with self.assertRaisesRegex(AssertionError,'Proposal became'):self.validate()

    def test_missing_npc_instance(self):
        actor=next(c for c in self.people if c['id']=='aide-2')
        actor['runtime_bindings']=[]
        with self.assertRaisesRegex(AssertionError,'coverage drift'):self.validate()

    def test_unwritten_stays_blank(self):
        self.world['unwritten'][0]['text']='Invented war ending'
        with self.assertRaisesRegex(AssertionError,'silently filled'):self.validate()

    def test_no_unreviewed_global_position(self):
        self.atlas['regions'][0]['global_coordinates']=[12,30]
        with self.assertRaisesRegex(AssertionError,'Global coordinates'):self.validate()

    def test_reference_tampering(self):
        old=bible.OUT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                bible.OUT=Path(tmp);(bible.OUT/'media').mkdir()
                m=copy.deepcopy(self.media[0]);(bible.OUT/'media'/m['local_name']).write_bytes(b'wrong content')
                with self.assertRaisesRegex(AssertionError,'Reference changed'):bible.fetch_media([m])
        finally:bible.OUT=old

    def test_authored_position_needs_compatibility_not_official_coordinates(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            doc=Path(tmp)/'review.md'
            doc.write_text('Fixture: local terrain compatibility reviewed.',encoding='utf-8')
            r=self.atlas['regions'][0]
            r['global_coordinates']=[12,30]
            r['placement_review']={'status':'reviewed','basis':'omni_authored','document':doc.relative_to(ROOT).as_posix()}
            self.validate()
            doc.unlink()
            with self.assertRaisesRegex(AssertionError,'Missing placement'):self.validate()

    def test_invalid_global_coordinate(self):
        for xy in ([True,20],[float('nan'),20],[1,2,3]):
            self.atlas['regions'][0]['global_coordinates']=xy
            with self.assertRaisesRegex(AssertionError,'finite 2D'):self.validate()


if __name__=='__main__':unittest.main()
