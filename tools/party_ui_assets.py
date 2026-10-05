"""Rocket-native party tiles, slot palettes and two-frame party icons.

Coordinates and palette substitutions follow the pinned party_menu.c reference.
Never resize a battle picture to manufacture a party icon.
"""
import struct
from PIL import Image
from extract_rocket_rom import pointer


def add_party_assets(rom, read, pictures):
    from build_game_ui_assets import colors, tilemap_image, tile_image
    tiles = read('party_tiles', 0x1c764cc, reference='graphics/party_menu/bg.png')
    pal = colors(read('party_palette', 0x1c76794))
    pictures['party_background'] = tilemap_image(
        tiles, read('party_map', 0x1c76890), pal).crop((0, 0, 240, 160))
    for name, offset, w, h in [('main', 0xcf85a0, 10, 7), ('wide', 0xcf862c, 18, 3), ('empty', 0xcf8698, 18, 3)]:
        cells = read('party_slot_'+name, offset, w*h)
        for selected in range(2):
            p = list(pal[48:64])
            for dest, src in zip([4, 5, 6, 1, 7, 8], [116,117,118,97,103,104] if selected else [52,53,54,49,55,56]):
                p[dest] = pal[src]
            if name == 'empty':
                for dest, src in zip([1,11,12], [17,27,28]):
                    p[dest] = pal[src]
            im = Image.new('RGBA', (w*8, h*8))
            for i, tile in enumerate(cells):
                im.paste(tile_image(tiles[tile*32:(tile+1)*32], 8,8,p,transparent=False), ((i%w)*8,(i//w)*8))
            pictures['party_'+name+str(selected)] = im
    table, indices, palettes = [pointer(rom, at) for at in (0x138,0x13c,0x140)]
    for species in [1,4,7,25,16,19,109,13,111,59,128,131]:
        index = read(f'icon_{species}_palette_index', indices+species, 1)[0]
        assert index < 16
        palette = colors(read(f'icon_{species}_palette', pointer(rom,palettes+index*8),32))
        data = read(f'icon_{species}_tiles',pointer(rom,table+species*4),1024)
        pictures['party_icon_'+str(species)] = tile_image(data,32,64,palette,32,32)
