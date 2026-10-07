"""Encode continuous emulator frames/audio; keep native pixels and real timing."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'.cache/war-video-runtime'))
import imageio_ffmpeg

out = ROOT/'build/pallet/story-playthrough'
meta = json.loads((out/'story.json').read_text('utf8'))
subprocess.run([
    imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-v', 'error',
    '-f', 'rawvideo', '-pixel_format', 'rgba', '-video_size', '240x160',
    '-framerate', str(meta['fps']), '-i', str(out/'story.rgba'),
    '-f', 's16le', '-ar', str(meta['audioRate']), '-ac', '2', '-i', str(out/'story.pcm'),
    '-vf', 'scale=720:480:flags=neighbor', '-c:v', 'libx264', '-crf', '16',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', '-movflags', '+faststart',
    str(out/'story.mp4')], check=True)
from PIL import Image, ImageDraw
sheet = Image.new('RGB', (720, 4*186), '#20252b')
draw = ImageDraw.Draw(sheet)
with (out/'story.rgba').open('rb') as stream:
    for i, chapter in enumerate(meta['chapters'][1:13]):
        frame = min(meta['videoFrames']-1, int((chapter['seconds']+2)*meta['fps']))
        stream.seek(frame*153600)
        image = Image.frombytes('RGBA', (240, 160), stream.read(153600))
        x,y = i%3*240,i//3*186
        sheet.paste(image, (x,y+22))
        draw.text((x+5,y+4), f"{i+1:02} | {int(chapter['seconds'])//60:02}:{int(chapter['seconds'])%60:02}", fill='white')
sheet.save(out/'review.png')
print(json.dumps({'video': str(out/'story.mp4'), 'seconds': meta['seconds'], 'chapters': len(meta['chapters'])}))
