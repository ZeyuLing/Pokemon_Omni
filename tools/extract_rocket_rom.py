"""Extract the 23 documented bond forms from the user's pinned local ROM.

ROMs and decoded PNGs stay in assets/imported (git ignored). The committed
manifest records offsets, hashes and discrepancies, never a ROM payload.
This parser is deliberately hash-locked; it is not a generic Emerald importer.
"""
import argparse
import hashlib
import json
import struct
import zlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_SHA = "033235cdd389c4c8cb1aa6d68a93954a55fd681c92a1a554ebc63431117b4eaf"
AUTHOR_SHA = "008c256ca16c46d81f7417edfc2ec40ab9e3d2932e67bf5317e48d15b206ff9e"
TYPES = ['Normal', 'Fighting', 'Flying', 'Poison', 'Ground', 'Rock', 'Bug',
         'Ghost', 'Steel', 'Unknown', 'Fire', 'Water', 'Grass', 'Electric',
         'Psychic', 'Ice', 'Dragon', 'Dark', 'Fairy']
# IDs are validated against the author ROM's independently decoded name table.
IDENTITIES = {
    'Rhyperior': (936, 'Rhyper&'), 'Hypno': (933, 'Hypno&'),
    'Rapidash': (929, 'Rapidash&'), 'Butterfree': (927, 'Butterfr&'),
    'Kingdra': (930, 'Kingdra&'), 'Skarmory': (931, 'Skarmory&'),
    'Poliwrath': (926, 'Poliwrath&'), 'Eevee': (932, 'Eevee&'),
    'Mamoswine': (1309, 'Mamosw-&'), 'Delphox': (935, 'Delphox-&'),
    'Feraligatr': (928, 'Feralig&'), 'Flareon EN': (972, 'En'),
    'Jolteon RAI': (971, 'Rai'), 'Vaporeon SUI': (970, 'Sui'),
    'Ninetales': (1380, 'Ninetales&'), 'Crobat Protagonist': (1305, 'Crobat♂-&'),
    'Crobat Andra': (1306, 'Crobat♀-&'), 'Volcarona': (945, 'Volcarona&'),
    'Milotic': (1392, 'Milotic&'), 'Goodra': (946, 'Goodra&'),
    'Dragonite': (948, 'Dragonite&'), 'Jirachi': (1040, 'Jirachi-&'),
    'Sacred Dragon Dun': (973, 'Dun-O'),
}
TABLE_FIELDS = {'front': 0x128, 'back': 0x12C, 'normal_palette': 0x130,
                'shiny_palette': 0x134, 'names': 0x144, 'species': 0x1B8,
                'ability_names': 0x1BC}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pointer(rom, offset):
    if offset < 0 or offset + 4 > len(rom):
        raise ValueError('Pointer field outside ROM')
    value = struct.unpack_from('<I', rom, offset)[0] - 0x08000000
    if not 0 <= value < len(rom):
        raise ValueError(f'Invalid ROM pointer at {offset:#x}')
    return value


def lz10(rom, offset):
    """Bounded GBA BIOS LZ77 stream, including overlapping back references."""
    if offset < 0 or offset + 4 > len(rom) or rom[offset] != 0x10:
        raise ValueError('Not a GBA LZ10 stream')
    size = int.from_bytes(rom[offset + 1:offset + 4], 'little')
    if not 0 < size <= 65536:
        raise ValueError('Unsupported decompressed size')
    cursor, output = offset + 4, bytearray()
    def byte():
        nonlocal cursor
        if cursor >= len(rom):
            raise ValueError('Truncated LZ10 stream')
        value = rom[cursor]
        cursor += 1
        return value
    while len(output) < size:
        flags = byte()
        for bit in range(7, -1, -1):
            if len(output) == size:
                break
            if flags & (1 << bit):
                high, low = byte(), byte()
                count = (high >> 4) + 3
                distance = ((high & 15) << 8 | low) + 1
                if distance > len(output):
                    raise ValueError('LZ10 reference precedes output')
                for _ in range(min(count, size - len(output))):
                    output.append(output[-distance])
            else:
                output.append(byte())
    return bytes(output), cursor - offset


def decode_name(data):
    """Latin subset of Gen III charmap, only for the author's Spanish ROM."""
    extra = {0: ' ', 0x2D: '&', 0xAE: '-', 0xAD: '.', 0xB5: '♂', 0xB6: '♀',
             0x01: 'À', 0x02: 'Á', 0x06: 'É', 0x0B: 'Î', 0x0E: 'Ó',
             0x12: 'Ú', 0x13: 'Û', 0x16: 'à', 0x17: 'á', 0x1B: 'é', 0x20: 'î',
             0x23: 'ó', 0x27: 'ú', 0x28: 'û', 0x29: 'ñ', 0x5A: 'Í', 0x6F: 'í'}
    result = ''
    for value in data:
        if value == 255:
            break
        if 0xBB <= value <= 0xD4:
            result += chr(value - 0xBB + 65)
        elif 0xD5 <= value <= 0xEE:
            result += chr(value - 0xD5 + 97)
        elif 0xA1 <= value <= 0xAA:
            result += str(value - 0xA1)
        else:
            result += extra.get(value, f'<{value:02x}>')
    return result


def sprite_png(tiles, palette):
    """First 64x64 frame, 4bpp 8x8 tiles, BGR555; palette index 0 transparent."""
    if len(tiles) < 2048 or len(tiles) % 2048 or len(palette) != 32:
        raise ValueError('Unsupported sprite/palette layout')
    colors = []
    for index, (value,) in enumerate(struct.iter_unpack('<H', palette)):
        channels = [(value >> shift) & 31 for shift in (0, 5, 10)]
        colors.append(bytes([(v << 3) | (v >> 2) for v in channels] + [255 if index else 0]))
    scanlines = bytearray()
    for y in range(64):
        scanlines.append(0)
        for x in range(64):
            index = (y // 8 * 8 + x // 8) * 32 + y % 8 * 4 + x % 8 // 2
            color = (tiles[index] >> ((x % 2) * 4)) & 15
            scanlines.extend(colors[color])
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 64, 64, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(scanlines), 9)) + chunk(b'IEND', b''))


def inspect(rom, sid):
    tables = {key: pointer(rom, field) for key, field in TABLE_FIELDS.items()}
    offset = tables['species'] + sid * 36
    record = rom[offset:offset + 36]
    if len(record) != 36:
        raise ValueError('Truncated species record')
    stats = dict(zip(['hp', 'atk', 'def', 'spe', 'spa', 'spd'], record[:6]))
    types = list(dict.fromkeys(TYPES[t] for t in record[6:8]))
    abilities = list(struct.unpack_from('<HHH', record, 24))
    assets, payloads = {}, {}
    for key in ('front', 'back', 'normal_palette', 'shiny_palette'):
        table_offset = tables[key] + sid * 8
        address = pointer(rom, table_offset)
        payload, consumed = lz10(rom, address)
        tag_offset = 6 if key in ('front', 'back') else 4
        tag = struct.unpack_from('<H', rom, table_offset + tag_offset)[0]
        if tag != sid + (5000 if key == 'shiny_palette' else 0):
            raise ValueError('Species sprite/palette tag mismatch')
        payloads[key] = payload
        assets[key] = {'table_entry_offset': table_offset, 'data_offset': address,
                       'compressed_bytes': consumed, 'decoded_bytes': len(payload),
                       'decoded_sha256': digest(payload)}
    return {'species_offset': offset, 'stats': stats, 'types': types,
            'ability_ids': abilities, 'species_record_sha256': digest(record),
            'name_bytes_hex': rom[tables['names'] + sid * 11:tables['names'] + (sid + 1) * 11].hex(),
            'assets': assets}, payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT / 'assets/imported/rocket-user/rocket-user-modifier.gba')
    parser.add_argument('--author-archive', type=Path, default=ROOT / '.cache/rocket-author.zip')
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if digest(rom) != USER_SHA:
        raise ValueError('Unrecognized user ROM hash; update and verify a new profile explicitly')
    with zipfile.ZipFile(args.author_archive) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith('.gba') and not n.startswith('__MACOSX/')]
        if len(members) != 1:
            raise ValueError('Expected exactly one author ROM')
        author = archive.read(members[0])
    if digest(author) != AUTHOR_SHA:
        raise ValueError('Unrecognized author ROM hash')
    documentation = json.loads((ROOT / 'content/bond/author-reference.json').read_text(encoding='utf-8'))
    entries = json.loads((ROOT / 'content/pokedex/entries.json').read_text(encoding='utf-8'))['entries']
    records = []
    # Validate everything before publishing any output.
    pngs = {}
    for doc in documentation['records']:
        name = doc['name']
        sid, expected_name = IDENTITIES[name]
        user, payloads = inspect(rom, sid)
        original, original_payloads = inspect(author, sid)
        decoded_name = decode_name(bytes.fromhex(original['name_bytes_hex']))
        if decoded_name != expected_name:
            raise ValueError(f'Author species identity mismatch: {name}: {decoded_name}')
        if user['species_record_sha256'] != original['species_record_sha256'] or payloads != original_payloads:
            raise ValueError(f'User and author species/assets differ: {name}; manual review required')
        entry = next(e for e in entries if e['name_reference'] == name + ' [Rocket bond candidate]')
        slug = entry['entry_id'].split(':')[-1]
        variants = {}
        for variant, side, palette in [('front_default', 'front', 'normal_palette'),
                                       ('front_shiny', 'front', 'shiny_palette'),
                                       ('back_default', 'back', 'normal_palette'),
                                       ('back_shiny', 'back', 'shiny_palette')]:
            relative = f'assets/imported/rocket-user/bond-sprites/{slug}-{variant}.png'
            png = sprite_png(payloads[side], payloads[palette])
            pngs[relative] = png
            variants[variant] = {'path': relative, 'url': f'/rocket-art/{slug}-{variant}.png',
                                 'sha256': digest(png), 'width': 64, 'height': 64,
                                 'frame_index': 0, 'frame_count': len(payloads[side]) // 2048}
        differences = {}
        if user['stats'] != doc['stats']:
            differences['stats'] = {'document': doc['stats'], 'rom': user['stats']}
        if set(user['types']) != set(doc['types']):
            differences['types'] = {'document': doc['types'], 'rom': user['types']}
        ability_base = pointer(author, 0x1BC)
        records.append({'entry_id': entry['entry_id'], 'name': name, 'species_id': sid,
                        'author_rom_name': decoded_name, 'user_rom': user,
                        'author_rom': original, 'author_matches_user': True,
                        'author_ability_names': [decode_name(author[ability_base + n * 17:ability_base + (n + 1) * 17]) for n in user['ability_ids']],
                        'document_differences': differences, 'variants': variants})
    manifest = {'schema_version': 1, 'user_rom_sha256': USER_SHA, 'author_rom_sha256': AUTHOR_SHA,
                'identity_basis': 'Author Spanish species names + exact 36-byte species records and four decoded graphic/palette payloads shared by both ROMs.',
                'version_status': 'User-played modifier ROM; upstream release number still unverified.',
                'graphics_scope': 'First front/back frame, normal/shiny palettes. No battle animation or transition code verification.',
                'battle_data_approved': False, 'records': records}
    for relative, png in pngs.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)
    (ROOT / 'content/bond/rom-reference.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'forms': len(records), 'pngs': len(pngs), 'both_roms_agree': True,
                      'document_discrepancies': {r['name']: r['document_differences'] for r in records if r['document_differences']}}, indent=2))


if __name__ == '__main__':
    main()
