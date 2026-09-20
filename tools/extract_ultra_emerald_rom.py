"""Hash-locked extraction of the user's Ultra Emerald 5.8 permanent-Mega ROM.

ROM/PNG payloads remain local. Source-scoped tables are references, not approved
Omni battle rules. The original 28-byte record's ability bytes are NOT used:
the hooked ability getter reads three uint16 values from a separate table.
"""
import argparse
import json
import re
import struct
import urllib.request
from pathlib import Path
from extract_rocket_rom import pointer, lz10, sprite_png, digest

ROOT = Path(__file__).resolve().parents[1]
ROM_PATH = 'assets/imported/ultra-emerald-5.8-user/ultra-emerald-5.8-final-permanent-mega.gba'
SHA = 'cb93af4a51809e4ef4fb5e7356e029e009a026bf20148fa7618e0731bb91edac'
CHARMAP_URL = 'https://raw.githubusercontent.com/GoldenCaterpie/pokeemerald-ch/c8b4aed68d8ff0af6b2992f54253a0e3cc379bdb/charmap.txt'
CHARMAP_SHA = '3b6797670938e2a94df78b8bfeaecff5ff7f5848c8eafce83771cbf742245fcb'
TABLES = dict(stats=0x101D700, names=0x10442CC, front=0x102E1FC, back=0x1032E44,
              normal_palette=0x1037A8C, shiny_palette=0x103C6D4, abilities=0x17A0000,
              ability_names=0x1D03068, evolution=0x105785C, items=0xFC2C7C)
TYPES = {i:t for i,t in enumerate(['Normal','Fighting','Flying','Poison','Ground','Rock','Bug','Ghost','Steel',None,'Fire','Water','Grass','Electric','Psychic','Ice','Dragon','Dark']) if t}
TYPES[23] = 'Fairy'
# Explicit source identities, reviewed against names, sprites and incoming edges.
# Forms with no canonical species identity retain national number 0.
FORMS = {
 413:(150,'黯影超梦 X',432),414:(571,'索罗亚克 Z',624),415:(350,'美纳斯 Z',329),
 416:(392,'烈焰猴 X',445),418:(908,'超级假面喵',1201),419:(911,'骨纹巨声鳄 · 永久进化',1204),
 420:(914,'超级浪舞鸭',1207),421:(466,'电击魔兽 X',519),422:(612,'超级战斧龙',665),
 423:(395,'帝王拿波 X',448),424:(142,'化石骨龙',142),425:(34,'尼多王 X',34),
 426:(467,'鸭嘴炎兽 Y',520),427:(34,'尼多王 Y',34),428:(658,'小智忍蛙 · 神战版',711),
 429:(715,'超级音波龙',768),430:(497,'超级君主蛇',550),431:(25,'飞行皮卡丘',25),
 432:(150,'黯影超梦',None),433:(621,'灭世魔龙',674),434:(38,'超级九尾',38),
 990:(0,'化石雷鸟',None),991:(0,'化石巨龙',None),992:(0,'化石鳃鱼',None),993:(0,'化石海兽',None),
 1076:(25,'小智皮卡丘 · 神战版',None),1079:(249,'暗黑洛奇亚',None),1097:(150,'铠甲超梦',None),
 1106:(330,'沙漠蜻蜓 · 神战超进化',334),1118:(150,'全装甲超梦',None),1119:(646,'合众酋雷姆',None),
 1336:(493,'阿尔宙斯 · 光之石形态',546),1337:(493,'阿尔宙斯 · 暗之石形态',546),
 1383:(249,'洛奇亚 · 光之石形态',249),1384:(250,'凤王 · 火之石形态',250),
}

def charmap():
    path=ROOT/'.cache/ultra-emerald/charmap.txt'
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(urllib.request.urlopen(CHARMAP_URL,timeout=30).read())
    raw=path.read_bytes()
    if digest(raw)!=CHARMAP_SHA: raise ValueError('Character map hash changed')
    table={}
    for line in raw.decode('utf8').splitlines():
        m=re.match(r"'(.+)'\s*=\s*([0-9A-Fa-f ]+)",line)
        if m:
            try: table[bytes.fromhex(m[2].strip())]=m[1]
            except ValueError: pass
    return table

def decode(data, table):
    output=[];i=0
    while i<len(data) and data[i]!=255:
        width=2 if data[i:i+2] in table else 1
        output.append(table.get(data[i:i+width],f'<{data[i]:02X}>'));i+=width
    return ''.join(output).rstrip()

def inspect(rom, sid, chars):
    if not 0 <= sid <= 1385: raise ValueError('Outside reviewed table region')
    at=TABLES['stats']+sid*28;raw=rom[at:at+28]
    name=rom[TABLES['names']+sid*11:TABLES['names']+(sid+1)*11]
    abilities=list(struct.unpack_from('<HHH',rom,TABLES['abilities']+sid*6))
    evo=[]
    for slot in range(5):
        offset=TABLES['evolution']+sid*40+slot*8
        method,param,target,padding=struct.unpack_from('<HHHH',rom,offset)
        if method:
            evo.append(dict(offset=offset,method_raw=method,parameter=param,target_sid=target,padding=padding))
    return dict(source_sid=sid,source_name=decode(name,chars),name_bytes_hex=name.hex(),
                stats_offset=at,record_sha256=digest(raw),record_hex=raw.hex(),
                stats=dict(zip(['hp','atk','def','spe','spa','spd'],raw[:6])),
                type_ids=list(raw[6:8]),types=list(dict.fromkeys(TYPES.get(t,f'Unknown:{t}') for t in raw[6:8])),
                ability_ids=abilities,ability_table_offset=TABLES['abilities']+sid*6,evolutions=evo)

def validate(rom, chars):
    if len(rom)!=33554432 or digest(rom)!=SHA: raise ValueError('Unrecognized ROM; refusing guessed offsets')
    for field,key in [(0x128,'front'),(0x12C,'back'),(0x130,'normal_palette'),(0x134,'shiny_palette'),(0x144,'names'),(0x1BC,'stats'),(0x1C0,'ability_names')]:
        if pointer(rom,field)!=TABLES[key]: raise ValueError('Header table mismatch')
    if pointer(rom,0x6B698)!=0x1D739E5 or pointer(rom,0x1D739F8)!=TABLES['abilities']:
        raise ValueError('Active ability hook mismatch')
    # Getter computes (species*3 + slot)*2 and loads uint16; do not read legacy bytes.
    if rom[0x1D739E4:0x1D739F0].hex()!='03225043034b41184900c85a':
        raise ValueError('Ability getter instructions changed')
    for sid,name in [(1,'妙蛙种子'),(6,'喷火龙'),(150,'超梦'),(249,'洛奇亚'),(250,'凤王')]:
        if inspect(rom,sid,chars)['source_name']!=name: raise ValueError('Chinese decoding anchors disagree')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rom',type=Path,default=ROOT/ROM_PATH);args=parser.parse_args()
    rom=args.rom.read_bytes();chars=charmap();validate(rom,chars)
    rows=[inspect(rom,sid,chars) for sid in range(1,1386)]
    by_sid={r['source_sid']:r for r in rows};payloads={};records=[]
    for sid,(national,label,parent) in FORMS.items():
        row=dict(by_sid[sid]);row.update(entry_id=f'dex:omni:ultra58:{sid}',national_number=national,display_name=label,parent_source_sid=parent)
        if any(t not in TYPES.values() for t in row['types']) or not all(0<v<=255 for v in row['stats'].values()): raise ValueError('Invalid selected stats/types')
        assets={};decoded={}
        for kind in ['front','back','normal_palette','shiny_palette']:
            at=TABLES[kind]+sid*8;address=pointer(rom,at);data,used=lz10(rom,address)
            decoded[kind]=data
            assets[kind]=dict(table_offset=at,data_offset=address,compressed_bytes=used,decoded_bytes=len(data),decoded_sha256=digest(data),table_record_hex=rom[at:at+8].hex())
        variants={}
        for variant,art,pal in [('front_default','front','normal_palette'),('back_default','back','normal_palette'),('front_shiny','front','shiny_palette'),('back_shiny','back','shiny_palette')]:
            data=sprite_png(decoded[art],decoded[pal]);path=f'assets/imported/ultra-emerald-5.8-user/form-sprites/{sid}-{variant}.png'
            payloads[path]=data;variants[variant]=dict(path=path,url=f'/ultra-art/{sid}-{variant}.png',sha256=digest(data))
        incoming=[]
        for origin in rows:
            for edge in origin['evolutions']:
                if edge['target_sid']!=sid: continue
                item=None
                if edge['method_raw'] in [6,7,251]:
                    at=TABLES['items']+edge['parameter']*44
                    if struct.unpack_from('<H',rom,at+14)[0]!=edge['parameter']: raise ValueError('Item table ID mismatch')
                    item=decode(rom[at:at+14],chars)
                incoming.append(dict(**edge,source_sid=origin['source_sid'],source_name=origin['source_name'],item_name=item))
        if parent is not None and not any(e['source_sid']==parent for e in incoming): raise ValueError('Expected incoming evolution missing')
        row.update(assets=assets,variants=variants,incoming_evolutions=incoming,normal_shiny_identical=decoded['normal_palette']==decoded['shiny_palette'])
        row['abilities']=[]
        for slot,aid in zip(['0','1','H'],row['ability_ids']):
            name=decode(rom[TABLES['ability_names']+aid*13:TABLES['ability_names']+(aid+1)*13],chars) if aid<255 else None
            row['abilities'].append(dict(slot=slot,source_id=aid,name=name,name_verified=name is not None))
        records.append(row)
    report=dict(schema_version=1,source_rom_sha256=SHA,source_rom_path=ROM_PATH,source_edition='User-supplied 5.8 神战最终版 + 永久超进化 + PC cheat variant',
                charmap_source=dict(url=CHARMAP_URL,sha256=CHARMAP_SHA),tables=TABLES,reviewed_species_range=[1,1385],records=records,
                classification='Source-scoped custom/variant references. Not a list of newly official species.',
                exclusions=dict(placeholder_sids=[201,412,417],unown_source_overrides=[435,436,437,438,439],reserved_table_space='Header pointer spacing reserves 2441 slots; after 1385 records are overwritten/unused, not 2441 verified species.'),
                limitations=['Only first sprite animation frame exported; decoded full stream hashes retained.','Source names may be shortened; display suffixes distinguish duplicate source names.','Evolution table decoded; script encounters, runtime persistence, held-item privileges and reversion hooks not fully verified.','Extended ability names >=255 not decoded; source IDs preserved without assigning official ability identities.','Source learnsets and Omni battle/quest implementation remain pending.','Existing official forms and their values are not overwritten by this reference pack.'])
    for path,data in payloads.items():
        target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    out=ROOT/'content/source-variants';out.mkdir(parents=True,exist_ok=True)
    (out/'ultra-emerald-5.8.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'ultra-emerald-5.8-inventory.json').write_text(json.dumps(dict(source_rom_sha256=SHA,scope='Contiguous reviewed tables; placeholders and duplicates intentionally preserved as raw references.',records=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Extracted {len(records)} source variants, {len(payloads)} PNG variants and {len(rows)} source table records; battle approval remains false.')

if __name__=='__main__': main()
