"""Source-running-frame and actual Omni ROM comparisons, plus blocking regressions."""
import json,sys,struct,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from opening_blocking import route,tile,clear
from build_rocket_dialogue import width
OUT=ROOT/'build/pallet'
SCRIPT=json.loads((ROOT/'content/opening/prologue.json').read_text('utf8'))
REPORT=json.loads((OUT/'presentation-report.json').read_text('utf8'))
GRIDS=json.loads((OUT/'opening-collision.json').read_text())
GLYPHS={g['char']:g for g in json.loads((ROOT/'assets/source/rocket-dialogue.json').read_text('utf8'))['glyphs']}
BLOB=(OUT/'rocket_text.bin').read_bytes()

def rgb(v):return tuple(((v>>s)&31)*8+(((v>>s)&31)>>2) for s in (0,5,10))
def shot(path):return Image.frombytes('RGBA',(240,160),path.read_bytes()).convert('RGB')
def draw_line(im,x,y,text):
    for ch in text:
        index=sorted(GLYPHS).index(ch);data=BLOB[index*64:index*64+64]
        for yy in range(16):
            for xx in range(16):
                bits=struct.unpack_from('<H',data,(yy//8*2+xx//8)*16+(yy%8)*2)[0]
                v=(bits>>(14-2*(xx%8)))&3
                if v in (1,2):im.putpixel((x+xx,y+yy),[(0,0,0),(99,99,99),(214,214,206)][v])
        x+=width(ch)

class OpeningLayout(unittest.TestCase):
    def test_source_running_font_and_window(self):
        source=shot(OUT/'reference-rocket-dialogue.rgba')
        expected=Image.new('RGB',(240,160))
        offset=len(GLYPHS)*64
        for y in range(48):
            for x in range(240):
                v=struct.unpack_from('<H',BLOB,offset+(y*240+x)*2)[0]
                if v!=0x8000:expected.putpixel((x,y+112),rgb(v))
        draw_line(expected,16,121,'本版本只在西班牙火箭队吧')
        draw_line(expected,16,135,'进行更新发布。')
        # Independent source engine verifies actual glyphs, punctuation,
        # shadow, baseline and fourteen-pixel line spacing.
        for region in [(0,112,240,121),(0,152,240,160),(0,120,16,152),(224,120,240,152),(16,121,172,135),(16,135,100,150)]:
            self.assertEqual(source.crop(region).tobytes(),expected.crop(region).tobytes(),region)
        proof=Image.new('RGB',(480,160));proof.paste(source);proof.paste(expected,(240,0))
        proof.resize((960,320),Image.Resampling.NEAREST).save(OUT/'rocket-dialogue-source-comparison.png')

    def test_all_actual_rom_dialogue_lines(self):
        for cue in REPORT['cues']:
            if not cue['dialogue']:continue
            beat=SCRIPT['scenes'][cue['chapter']]['beats'][cue['beat']]
            actual=shot(OUT/f'cue-{cue["cue"]}.rgba')
            expected=Image.new('RGB',(240,160),'white')
            for y,line in zip((121,135),beat['lines']):
                self.assertLessEqual(sum(width(c) for c in line),204)
                draw_line(expected,16,y,line)
                end=16+sum(width(c) for c in line)
                # Exclude the source continuation arrow after the text.
                self.assertEqual(actual.crop((16,y,end,y+14)).tobytes(),expected.crop((16,y,end,y+14)).tobytes(),(cue['cue'],line))

    def test_blocked_destination_and_furniture_shortcut_rejected(self):
        grid=GRIDS['league']
        with self.assertRaisesRegex(AssertionError,'Blocked actor destination'):
            route(grid,[128,48],[128,80]) # conference tabletop
        around=route(grid,[128,48],[128,112])
        self.assertGreater(len(around),5) # direct line crosses the table
        for a,b in zip(around,around[1:]):
            self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),16)
            self.assertTrue(clear(grid,tile(b)))
        with self.assertRaisesRegex(AssertionError,'Blocked actor destination'):
            route(grid,[128,48],[128,112],occupied=[[128,112]])

    def test_old_flowerpot_bug_is_an_obstacle(self):
        # Actual source block at world (17,4), old stage (128,80).
        from build_opening_stages import get
        blocks=get('data/layouts/RocketHideout_B4F/map.bin')
        block=struct.unpack_from('<H',blocks,(4*24+17)*2)[0]
        self.assertTrue(block&0xc00,'Source flowerpot must not be treated as walkable')

    def test_every_cue_reserves_other_actor_tiles(self):
        for cue in REPORT['cues']:
            paths=cue['paths'];moving=[a for a,p in paths.items() if len(p)>1]
            self.assertLessEqual(len(moving),1)
            for actor,path in paths.items():
                expected=route(GRIDS[cue['stage']],path[0],path[-1],[p[0] for a,p in paths.items() if a!=actor])
                self.assertEqual(path,expected)

    def test_meeting_and_music_continuity(self):
        spoken=[c for c in REPORT['cues'] if c['dialogue']]
        # The expanded war/aftermath now includes four commanders and cries;
        # political meetings still carry a majority of spoken beats.
        self.assertGreater(sum(c['scene'] in ('lance','silph','rocket') for c in spoken),len(spoken)*.5)
        self.assertEqual({c['music'] for c in REPORT['cues'] if c['scene'] in ('lance','silph','rocket')},{4})
        self.assertFalse(any(c['fade_in'] or c['fade_out'] for c in REPORT['cues'] if c['scene'] in ('silph','rocket')))
        lab=next(s for s in SCRIPT['scenes'] if s['stage']=='lab')['beats'];leave=next(i for i,b in enumerate(lab) if b.get('move',{}).get('gary')==[96,208])
        monitor=next(i for i,b in enumerate(lab) if b.get('effect')=='monitor')
        self.assertGreater(monitor,leave,'Private research must begin after Gary leaves')

    def test_war_precedes_meetings_and_preserves_full_viewport(self):
        scene=SCRIPT['scenes'][0]
        self.assertEqual(scene['id'],'war-front')
        self.assertEqual(scene['cast'],[])
        self.assertGreaterEqual(scene['beats'][0]['ticks'],384)
        self.assertNotIn('speaker',scene['beats'][0])
        self.assertEqual(SCRIPT['scenes'][1]['id'],'lance')
        self.assertEqual(GRIDS['war']['kind'],'battlefield')
        self.assertIn(0,GRIDS['war']['cells'],'Native battlefield requires traversable terrain')
        data=json.loads((ROOT/'content/opening/battlefield.json').read_text('utf8'))
        self.assertEqual(len(data['actors']),40)
        self.assertTrue({a['id'] for a in data['actors']}<=set(scene['actors']))
        for cue in REPORT['cues']:
            if cue['stage']!='war':continue
            for x,y in cue['camera']:
                self.assertTrue(0<=x<=272 and 0<=y<=160,'Camera exposes empty space')
        # Evidence comes from actual ROM frames, not the high-resolution source.
        selected=[REPORT['cues'][0],next(c for c in REPORT['cues'] if c['scene']=='war-front' and c['dialogue']),next(c for c in REPORT['cues'] if c['scene']=='lance' and c['dialogue'])]
        proof=Image.new('RGB',(720,160))
        for i,cue in enumerate(selected):
            actual=shot(OUT/f'cue-{cue["cue"]}.rgba')
            if i==0:
                self.assertGreater(len(set(actual.get_flattened_data())),30)
                actual.resize((720,480),Image.Resampling.NEAREST).save(OUT/'war-opening.png')
            proof.paste(actual,(i*240,0))
        proof.resize((1440,320),Image.Resampling.NEAREST).save(OUT/'war-to-meeting-proof.png')

if __name__=='__main__':unittest.main()
