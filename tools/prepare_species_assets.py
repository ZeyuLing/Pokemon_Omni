"""Prepare source-scoped battle frames and party icons from archived baselines.

Payloads stay under assets/imported; the reviewable manifest records exact ROM
offsets and hashes. Source IDs are NOT National Dex IDs. Successful decoding is
not visual acceptance, species identity verification, or animation verification.
"""
import hashlib
import json
from pathlib import Path
from extract_rocket_rom import pointer, lz10, USER_SHA
from extract_ultra_emerald_rom import ROM_PATH, SHA, charmap, decode
from build_game_ui_assets import colors, tile_image

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('rocket', 'assets/imported/rocket-user/rocket-user-modifier.gba', USER_SHA, 1392),
    ('ultra58', ROM_PATH, SHA, 1385),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    charmap_cached=charmap()
    result = {'schema_version': 1, 'acceptance': 'decoded_pending_identity_and_visual_review',
              'limitations': ['No field animation inferred from battle art or party icons.',
                  'All decoded battle frames retained; timing and animation scripts unverified.',
                  'Source slots include alternate forms and placeholders; counts are not unique species.',
                  'Only the first 251 unchanged-generation slots have a provisional numeric mapping; other identities remain unassigned.'],
              'sources': []}
    for label, path, expected, count in SOURCES:
        rom = (ROOT/path).read_bytes()
        assert sha(rom) == expected, 'Baseline hash changed'
        out = ROOT/'assets/imported/species-preparation'/label
        out.mkdir(parents=True, exist_ok=True)
        tables = {k: pointer(rom, a) for k,a in [('front',0x128),('back',0x12c),('normal',0x130),('shiny',0x134),('icons',0x138),('icon_ids',0x13c),('icon_palettes',0x140)]}
        source = {'id':label, 'rom':path, 'sha256':expected, 'tables':tables, 'records':[]}
        for sid in range(1,count+1):
            row = {'sid':sid, 'national_candidate':sid if sid<=251 else None, 'assets':{}, 'errors':[]}
            if label == 'ultra58':
                at=pointer(rom,0x144)+sid*11
                row['source_name'] = decode(rom[at:at+11], charmap_cached)
            decoded={}
            for kind in ('front','back','normal','shiny'):
                try:
                    at=pointer(rom,tables[kind]+sid*8)
                    data,used=lz10(rom,at)
                    if kind in ('normal','shiny'):
                        assert len(data)==32
                    else:
                        assert len(data)>=2048 and len(data)%2048==0 and len(data)<=32768
                    decoded[kind]=data
                    row['assets'][kind]={'offset':at,'encoded_bytes':used,'decoded_bytes':len(data),'sha256':sha(data)}
                except (ValueError,IndexError,AssertionError) as e:
                    row['errors'].append(kind+': '+(str(e) or 'invalid dimensions'))
            for side in ('front','back'):
                for pal in ('normal','shiny'):
                    if side in decoded and pal in decoded:
                        data=decoded[side]
                        im=tile_image(data,64,len(data)//32,colors(decoded[pal]),64,64)
                        im.save(out/f'{sid}-{side}-{pal}.png')
            try:
                at=pointer(rom,tables['icons']+sid*4)
                index=rom[tables['icon_ids']+sid]
                assert index<16
                palat=pointer(rom,tables['icon_palettes']+index*8)
                data,pal=rom[at:at+1024],rom[palat:palat+32]
                assert len(data)==1024 and len(pal)==32
                tile_image(data,32,64,colors(pal),32,32).save(out/f'{sid}-icon.png')
                row['assets']['icon']={'offset':at,'bytes':1024,'palette_offset':palat,'sha256':sha(data+pal)}
            except (ValueError,IndexError,AssertionError) as e:
                row['errors'].append('icon: '+(str(e) or 'invalid layout'))
            source['records'].append(row)
        source['counts']={k:sum(k in r['assets'] for r in source['records']) for k in ('front','back','normal','shiny','icon')}
        result['sources'].append(source)
        print(label,source['counts'])
    dest=ROOT/'assets/source/species-preparation.json'
    dest.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n','utf8')


if __name__ == '__main__':
    main()
