"""Verify native framebuffer pixels, after both startup ROM tests."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/pallet'

def frame(name):
    return Image.frombytes('RGBA', (240,160), (OUT/(name+'.rgba')).read_bytes())

source = frame('reference-start-menu')
empty = frame('start-empty')
assert source.crop((0,0,240,32)).tobytes() == empty.crop((0,0,240,32)).tobytes(), 'Source menu geometry, palette or glyph placement differs'
cover = frame('start-cover')
assert len(set(cover.get_flattened_data())) > 30, 'Missing native title artwork'
assert any(cover.getpixel((x,y))[0] > 220 for y in range(128,136) for x in range(40,136)), 'Source PRESS START not visible'
proof = Image.new('RGBA', (480,160))
proof.paste(cover,(0,0));proof.paste(frame('start-continue'),(240,0))
proof.resize((1440,480),Image.Resampling.NEAREST).save(OUT/'startup-proof.png')
for name in ['cover','empty','continue','overwrite','debug-dex']:
    frame('start-'+name).resize((720,480),Image.Resampling.NEAREST).save(OUT/('start-'+name+'.png'))
report = {'selected_new_game_panel': {'pixels_compared': 7680, 'differences': 0,
          'scope': 'Actual archived Rocket fresh-save menu vs actual Omni ROM. Other rows/actions differ intentionally.'},
          'cover': 'FireRed source artwork with authored Omni wordmark; not a claim of identical FireRed or Rocket cover.',
          'continue_layout': 'Emerald main_menu.c window coordinates and labels; live Omni saved values. Inactive dimming is quantized to RGB555.'}
(OUT/'startup-layout-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: all 7680 pixels of the selected New Game panel match the actual Rocket ROM; title/prompt proof exported')
