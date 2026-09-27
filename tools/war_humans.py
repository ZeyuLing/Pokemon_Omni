"""Native overworld frames, without resizing or per-direction recentering."""
import io
from PIL import Image
import war_sources

def native_frames(spec,fire_red_get):
    get={'emerald':war_sources.get,'platinum':war_sources.platinum_get}.get(spec['source'],fire_red_get)
    sheet=Image.open(io.BytesIO(get(spec['path'])));palette=sheet.getpalette()
    w,h=spec['frame'];result=[]
    for direction,index in enumerate(spec['directions']):
        box=(0,index*h,w,(index+1)*h) if spec['layout']=='vertical' else (index*w,0,(index+1)*w,h)
        raw=sheet.crop(box);frame=Image.new('RGBA',(w,h))
        for y in range(h):
            for x in range(w):
                value=raw.getpixel((x,y));dy=y+spec.get('offset_y',0)
                if value:
                    assert 0<=dy<h, 'Native frame would lose opaque pixels'
                    frame.putpixel((x,dy),(*palette[value*3:value*3+3],255))
        if direction==3 and spec.get('mirror_right'):frame=frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        assert frame.getbbox()[3]==31, 'Native feet must share the original FireRed baseline'
        result.append(frame)
    return result
