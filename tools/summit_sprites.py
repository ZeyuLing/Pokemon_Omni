"""Four-direction summit adaptations; never rescale individual characters."""
import hashlib,json
from PIL import Image
from war_uniforms import cells, quantize, ROOT
from war_humans import native_frames

NAMES=['karen','alder','diantha','hala','leon','geeta','matori']

def frames(name, get):
    if name in ('steven','cynthia'):
        platinum=name=='cynthia'
        return native_frames(dict(source='platinum' if platinum else 'emerald',
            path='res/graphics/field_sprites/npc/cynthia.png' if platinum else 'graphics/object_events/pics/people/steven.png',
            frame=[32 if platinum else 16,32],layout='vertical' if platinum else 'horizontal',
            directions=[4,0,8,12] if platinum else [0,1,2,2],
            mirror_right=not platinum,offset_y=int(platinum)),get)
    source=ROOT/'assets/characters/summit/delegates-source.png'
    manifest=json.loads((source.parent/'manifest.json').read_text('utf8'))
    assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['sha256'], 'Summit source changed'
    raw=cells(source,7)
    scale=min(22/max(c.height for c in raw),22/max(c.width for c in raw))
    result=[]
    for cell in raw[NAMES.index(name)*4:NAMES.index(name)*4+4]:
        small=cell.resize((round(cell.width*scale),round(cell.height*scale)),Image.Resampling.NEAREST)
        canvas=Image.new('RGBA',(24,32));canvas.paste(small,((24-small.width)//2,31-small.height))
        assert canvas.getbbox()[3]==31
        result.append(canvas)
    return quantize(result)
