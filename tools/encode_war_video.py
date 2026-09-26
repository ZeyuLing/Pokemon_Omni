"""Encode tests/war-rom.cjs's real-emulator recording; no synthetic frames."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.cache/war-video-runtime'))
import imageio_ffmpeg
out=ROOT/'build/pallet';meta=json.loads((out/'war-playback.json').read_text())
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-f','rawvideo','-pixel_format','rgba','-video_size','240x160','-framerate',str(meta['fps']),'-i',str(out/'war-playback.rgba'),'-f','s16le','-ar','32768','-ac','2','-i',str(out/'war-playback.pcm'),'-vf','scale=720:480:flags=neighbor','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',str(out/'war-playback.mp4')],check=True)
print(out/'war-playback.mp4')
