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

    def test_opening_actor_requires_dossier_binding(self):
        next(c for c in self.people if c['id']=='oak')['presentation_bindings']=[]
        with self.assertRaisesRegex(AssertionError,'Opening actor coverage drift'):self.validate()

    def test_montage_cannot_fill_unknown_date(self):
        self.world['opening_presentation']['date']='1974-01-01'
        with self.assertRaisesRegex(AssertionError,'Opening montage was dated'):self.validate()

    def test_cast_assets_require_dossier(self):
        next(c for c in self.people if c['id']=='silver')['game_assets']['portrait_actor']='missing'
        with self.assertRaisesRegex(AssertionError,'Cast dossier coverage drift'):self.validate()

    def test_player_opening_keeps_identity_secret(self):
        opening=bible.read('content/opening/prologue.json')
        runtime=' '.join(t for s in opening['scenes'] for t in [s['title'],*(line for b in s['beats'] for line in b.get('lines',[]))])
        for secret in ['AI','VLM','PROMPT','人工智能','人造','机器人','不会长大','赤红']:
            self.assertNotIn(secret,runtime)
        self.assertIsNone(opening['date'])
        self.assertEqual(opening['visibility'],'player_safe')

    def test_opening_supporting_roles_do_not_invent_life_history(self):
        for c in self.people:
            if c['id'].startswith('opening-'):
                self.assertTrue(all(v is None for v in c['biography'].values()))
                self.assertIsNone(c['birth_year'])
                self.assertFalse(any(c['id'] in e['participants'] for e in self.world['events']))
        oak=bible.render(self.world,self.people,self.atlas,self.media)[bible.DOCS/'characters/oak.md']
        self.assertIn('开场中的演绎',oak)

    def test_past_championship_does_not_remove_giovanni_legal_barrier(self):
        case=next(c for c in self.world['institutions']['world_federation']['eligibility']['known_cases'] if c['actor']=='giovanni')
        case['legal_status']='eligible';case['registration_completed']=True
        next(c for c in self.people if c['id']=='giovanni')['competition_status']={k:v for k,v in case.items() if k!='actor'}
        with self.assertRaisesRegex(AssertionError,'Giovanni eligibility obstacle'):self.validate()

    def test_unregistered_rival_cannot_enter_casting_pool(self):
        self.world['rival_program']['casting_groups'][0]['actors'].append('unregistered-heir')
        with self.assertRaisesRegex(AssertionError,'Unregistered or duplicate rival'):self.validate()

    def test_proposed_sponsor_is_not_adopted_allegiance(self):
        next(c for c in self.people if c['id']=='silver')['rival_design']['selected_faction']='rocket'
        with self.assertRaisesRegex(AssertionError,'proposal silently became affiliation'):self.validate()

    def test_rival_source_facts_do_not_fill_omni_life(self):
        for c in self.people:
            if c.get('rival_design') and c['status']=='candidate':
                self.assertTrue(all(v is None for v in c['biography'].values()),c['id'])
                self.assertFalse(any(c['id'] in e['participants'] for e in self.world['events']),c['id'])
        outputs=bible.render(self.world,self.people,self.atlas,self.media)
        silver=outputs[bible.DOCS/'characters/silver.md']
        self.assertIn('原作身份参考（不计入本作生平）',silver)
        self.assertIn('父子',silver)
        self.assertNotIn('事件 ID',silver)
        self.assertIn('报名受阻',outputs[bible.DOCS/'rivals.md'])

    def test_unknown_actor(self):
        self.world['events'][0]['participants']['unknown']='Unregistered role'
        with self.assertRaisesRegex(AssertionError,'Unregistered'):self.validate()

    def test_dead_character_cannot_reappear(self):
        self.world['events'][-1]['participants']['juan']='Alive after Cinnabar'
        with self.assertRaisesRegex(AssertionError,'Post-death'):self.validate()

    def test_unknown_epoch_stays_unknown(self):
        self.world['calendar']['epoch_year']=1967
        with self.assertRaisesRegex(AssertionError,'Undetermined mainline'):self.validate()

    def test_departure_does_not_receive_an_invented_date(self):
        next(e for e in self.world['events'] if e['id']=='ash-departure')['date']='1974-05-01'
        with self.assertRaisesRegex(AssertionError,'Undetermined mainline'):self.validate()

    def test_unwritten_history_stays_undated(self):
        self.world['unwritten'][0]['date']='1974-12-31'
        with self.assertRaisesRegex(AssertionError,'Unwritten history was dated'):self.validate()

    def test_established_outcome_is_not_a_date(self):
        next(e for e in self.world['events'] if e['id']=='oak-leaves-institute')['date']='1944-03-31'
        with self.assertRaisesRegex(AssertionError,'Undetermined event was dated'):self.validate()

    def test_invalid_calendar_date(self):
        self.world['events'][0]['date']='1942-02-30'
        with self.assertRaisesRegex(AssertionError,'Invalid calendar'):self.validate()

    def test_reversed_window(self):
        next(e for e in self.world['events'] if e['id']=='relic-surveys')['end_date']='1942-01-01'
        with self.assertRaisesRegex(AssertionError,'Reversed event'):self.validate()

    def test_consequence_cannot_precede_cause(self):
        event=next(e for e in self.world['events'] if e['id']=='rocket-outlawed')
        event.update(date='1943-05-01',date_status='assigned')
        with self.assertRaisesRegex(AssertionError,'Chronology prerequisite'):self.validate()

    def test_institution_calendar_stays_open(self):
        self.world['institutions']['world_federation']['first_tournament_date']='1976-09-01'
        with self.assertRaisesRegex(AssertionError,'Undetermined institution'):self.validate()

    def test_four_year_tournament_cycle(self):
        self.world['institutions']['world_federation']['tournament_cycle_years']=3
        with self.assertRaisesRegex(AssertionError,'Tournament cycle drift'):self.validate()

    def test_cycle_does_not_invent_executive_term_or_schedule(self):
        federation=self.world['institutions']['world_federation']
        self.assertIsNone(federation['executive']['term_years'])
        self.assertEqual(federation['tournament_schedule'],[])
        self.assertIn('不自动决定行政任期',bible.institution_calendar(federation))

    def test_second_generation_cannot_precede_first(self):
        next(e for e in self.world['events'] if e['id']=='red-developed').update(date='1970-01-01',date_status='assigned')
        next(e for e in self.world['events'] if e['id']=='ash-developed').update(date='1969-03-21',date_status='assigned')
        with self.assertRaisesRegex(AssertionError,'Chronology prerequisite'):self.validate()

    def test_unknown_dates_do_not_allow_causal_cycles(self):
        self.world['chronology_constraints'].append({'earlier':'ash-developed','later':'red-developed','relation':'ends_before_or_same_day'})
        with self.assertRaisesRegex(AssertionError,'Chronology cycle'):self.validate()

    def test_editorial_order_does_not_create_history(self):
        self.world['events'].reverse()
        self.validate()

    def test_ash_does_not_grow_up_before_transition(self):
        next(c for c in self.people if c['id']=='ash')['body_profile']['aging']='normal'
        with self.assertRaisesRegex(AssertionError,'Ash body baseline'):self.validate()

    def test_future_age_stages_require_body_transition(self):
        art=bible.read('assets/source/ash-age-design.json')
        self.assertEqual(art['body_growth'],'after_ash_human_body')
        self.assertTrue(all(s['status']=='withdrawn' for s in art['retired_age_stages']))
        self.assertEqual([s['id'] for s in art['stages']],['ash.kanto.young','ash.human.youth','ash.human.young_adult','ash.human.middle_aged'])
        for stage in art['stages'][1:]:
            self.assertEqual(stage['requires_design'],'ash-human-body')
            self.assertIsNone(stage['age_range'])
            self.assertIsNone(stage['unlock_date'])

    def test_nonaging_has_no_invented_mechanism(self):
        ash=next(c for c in self.people if c['id']=='ash')
        for field in ('implementation','longevity_limit','recognition_story'):
            self.assertIsNone(ash['body_profile'][field])

    def test_future_body_allows_growth(self):
        ash=next(c for c in self.people if c['id']=='ash')
        ash['body_profile']['after_transition']['aging']='does_not_grow_up'
        with self.assertRaisesRegex(AssertionError,'future growth'):self.validate()

    def test_body_transition_requires_registered_direction(self):
        self.world['future_designs']=[]
        with self.assertRaisesRegex(AssertionError,'Missing human-body'):self.validate()

    def test_future_direction_does_not_gain_a_date(self):
        self.world['future_designs'][0]['date']='1980-01-01'
        with self.assertRaisesRegex(AssertionError,'Unwritten future direction'):self.validate()

    def test_future_direction_does_not_gain_a_scene(self):
        self.world['future_designs'][0]['scene_text']='Unrequested sacrifice scene'
        with self.assertRaisesRegex(AssertionError,'Unwritten future direction'):self.validate()

    def test_recommended_giver_is_not_selected_giver(self):
        self.world['future_designs'][0]['selected_actor']='xerneas'
        with self.assertRaisesRegex(AssertionError,'Unassigned future role'):self.validate()

    def test_future_candidates_are_registered(self):
        self.world['future_designs'][0]['candidate_actors'].append('unknown-deity')
        with self.assertRaisesRegex(AssertionError,'Unregistered future actor'):self.validate()

    def test_new_candidates_do_not_have_written_history(self):
        for id in ('xerneas','arceus','ash-life-giver'):
            self.assertFalse(any(id in e['participants'] for e in self.world['events']))
            c=next(c for c in self.people if c['id']==id)
            self.assertTrue(all(v is None for v in c['biography'].values()))
        self.world['events'][-1]['participants']['xerneas']='Already gave Ash his body'
        with self.assertRaisesRegex(AssertionError,'Proposal became biography'):self.validate()

    def test_future_direction_is_separate_in_generated_dossiers(self):
        outputs=bible.render(self.world,self.people,self.atlas,self.media)
        dossier=outputs[bible.DOCS/'characters/xerneas.md']
        self.assertIn('仅作为执行者候选',dossier)
        self.assertNotIn('事件 ID',dossier)
        ash=outputs[bible.DOCS/'characters/ash.md']
        self.assertIn('后续方向（尚未写入生平）',ash)
        self.assertIn('青年和中年',ash)

    def test_deferred_arcs_do_not_become_biography(self):
        ids={x['id'] for x in self.world['unwritten']}
        self.assertTrue({'old-kanto-government-fall','kanto-current-elites','silph-transformation','oak-departure-details','silph-split-details','oak-giovanni-evolution'}<=ids)
        for id in ('oak','giovanni','lance'):
            self.assertIsNone(next(c for c in self.people if c['id']==id)['biography']['unwritten_intervals'])

    def test_render_preserves_unknown_dates_and_body_rule(self):
        outputs=bible.render(self.world,self.people,self.atlas,self.media)
        self.assertIn('具体间隔未定',outputs[bible.DOCS/'worldline.md'])
        self.assertIn('身体设定',outputs[bible.DOCS/'characters/ash.md'])
        self.assertIn('不会长大',outputs[bible.DOCS/'characters/ash.md'])
        self.assertNotIn('1975-09-01',outputs[bible.DOCS/'worldline.md'])

    def test_secret_does_not_spread_to_other_characters(self):
        self.world['secrets'][0]['known_by'].append('delia')
        with self.assertRaisesRegex(AssertionError,'only to Oak'):self.validate()

    def test_protagonist_does_not_know_his_identity(self):
        self.world['secrets'][0]['subject_knows']=True
        with self.assertRaisesRegex(AssertionError,'Secret knowledge'):self.validate()

    def test_appearance_is_not_ai_birth(self):
        next(c for c in self.people if c['id']=='ash')['birth_year']=1957
        with self.assertRaisesRegex(AssertionError,'biological birth'):self.validate()

    def test_world_champion_is_inside_four(self):
        self.world['institutions']['world_federation']['executive']['member_count']=5
        with self.assertRaisesRegex(AssertionError,'within four'):self.validate()

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
