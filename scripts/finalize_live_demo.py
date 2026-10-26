"""Trim automated-browser setup, encode public MP4, and write its captions.

Usage: python scripts/finalize_live_demo.py /path/to/ffmpeg
Run only after record_live_demo.cjs completes successfully. Review all scenes
before publishing. Raw browser recordings and exported research remain ignored.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'artifacts/public-demo/recording'
OUT=ROOT/'docs/media'

def build(encoder):
 data=json.loads((RAW/'chapters.json').read_text())
 video=Path((RAW/'video-path.txt').read_text())
 probe=subprocess.run([encoder,'-hide_banner','-i',str(video)],capture_output=True,text=True)
 match=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',probe.stderr)
 if not match:raise ValueError('Cannot determine recording duration')
 hours,minutes,seconds=map(float,match.groups());duration=hours*3600+minutes*60+seconds
 # Playwright records from page creation; remove navigation and fixture setup.
 offset=max(0,duration-data['end'])
 OUT.mkdir(parents=True,exist_ok=True)
 dest=OUT/'slothlab-live-demo.mp4'
 subprocess.run([encoder,'-y','-v','error','-ss',str(offset),'-i',str(video),'-t',str(data['end']),'-an','-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
 subprocess.run([encoder,'-v','error','-i',str(dest),'-f','null','-'],check=True)
 # Use the actual first reviewed scene as the public poster.
 Image.open(RAW/'01.png').save(OUT/'slothlab-live-demo-poster.png')
 def stamp(value):
  millis=round(value*1000);return f'{millis//3600000:02d}:{millis//60000%60:02d}:{millis//1000%60:02d}.{millis%1000:03d}'
 captions=['WEBVTT\n'];transcript=['# Live app demo transcript\n','Actual automated browser recording of the local application. The displayed investigation was completed before recording; no new research run is launched. Silent video with English captions.\n']
 chapters=data['chapters']
 for i,c in enumerate(chapters):
  end=chapters[i+1]['start'] if i+1<len(chapters) else data['end']
  captions.append(f"{stamp(c['start'])} --> {stamp(end)}\n{c['text']}\n")
  transcript.append(f"## {stamp(c['start'])[:-4]} — {c['name']}\n\n{c['text']}\n")
 (OUT/'slothlab-live-demo.vtt').write_text('\n'.join(captions))
 (OUT/'slothlab-live-demo-transcript.md').write_text('\n'.join(transcript))
 sheet=Image.new('RGB',(1440,250*((len(chapters)+3)//4)), '#16212b')
 for i,c in enumerate(chapters):
  with Image.open(RAW/f'{i+1:02d}.png') as image:sheet.paste(image.resize((360,250)),((i%4)*360,(i//4)*250))
 sheet.save('/tmp/slothlab-live-demo-contact.png')
 print(dest)
if __name__=='__main__':build(sys.argv[1] if len(sys.argv)>1 else 'ffmpeg')
