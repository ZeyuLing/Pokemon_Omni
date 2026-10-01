"""Native gait imports; two rejected generated adaptations remain pending repair."""
import hashlib,json,io
from PIL import Image
from war_uniforms import cells, quantize, ROOT

NAMES=['karen','alder','diantha','hala','leon','geeta','matori']

def frames(name, get):
    from overworld_source_art import records, source_frames
    if name in {r['actor'] for r in records()}:
        return source_frames(name)
    if name in ('steven','cynthia'):
        platinum=name=='cynthia'
        from war_sources import platinum_get, get as emerald_get
        data=(platinum_get('res/graphics/field_sprites/npc/cynthia.png') if platinum else
              emerald_get('graphics/object_events/pics/people/steven.png'))
        spec=next(s for s in json.loads((ROOT/'assets/source/overworld-repair.json').read_text('utf-8'))['native_game_sources'] if s['actor']==name)
        assert hashlib.sha256(data).hexdigest()==spec['sha256'], 'Native gait source changed'
        source=Image.open(io.BytesIO(data));palette=source.getpalette()
        indices=[[4,5,7],[0,1,3],[8,9,11],[12,13,15]] if platinum else [[0,3,4],[1,5,6],[2,7,8],[2,7,8]]
        result=[];w=32 if platinum else 16
        for face,poses in enumerate(indices):
            for index in poses:
                cell=source.crop((0,index*32,32,(index+1)*32) if platinum else (index*16,0,(index+1)*16,32))
                frame=Image.new('RGBA',(w,32))
                for y in range(32):
                    for x in range(w):
                        color=cell.getpixel((x,y))
                        if color:
                            assert y+int(platinum)<32
                            frame.putpixel((x,y+int(platinum)),(*palette[color*3:color*3+3],255))
                if face==3 and not platinum:frame=frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                result.append(frame)
        return result
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
