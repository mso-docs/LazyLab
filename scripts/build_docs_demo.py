"""Build the documentation walkthrough. Requires Pillow and an ffmpeg executable.

Usage: python scripts/build_docs_demo.py /path/to/ffmpeg
Illustrated UI, deliberately not presented as a live screen recording.
"""
from pathlib import Path
import subprocess
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/media'
SCENES = [
 ('Your research workspace', 'Choose how to keep your work.',
  'Open the local Streamlit app. Choose Guest for temporary JSON storage, or create a Browser profile to remember separate history on this browser. Select System, Light, or Dark appearance.',
  [('History mode', 'Workspace  /  Browser profile  /  Guest'), ('Appearance', 'System  /  Light  /  Dark'), ('Guest storage', 'JSON documents + artifact files; no SQL')]),
 ('Ask a testable question', 'Start in New investigation.',
  'Study the supported prior-probability correction experiment. Name the conditions and a measurable prediction. Include a competing hypothesis, rather than asking an unrestricted research question.',
  [('Question', 'Does prior correction improve Brier score?'), ('Conditions', 'Specify prevalence, sample sizes and seeds'), ('Competing prediction', 'Calibration error may offset the benefit')]),
 ('Set a finite design', 'Decide the limits before running.',
  'Set experiment and token budgets. Reserve independent confirmation seeds before exploration. Review the execution settings and choose an installed model on your Ollama-compatible server.',
  [('Experiment design', 'Controls + exploration conditions'), ('Confirmation', 'Reserve held-out seeds in advance'), ('Budgets', 'Experiments  /  tokens  /  wall time')]),
 ('Watch the investigation', 'Follow evidence in Research.',
  'Inspect measured results, decisions and event logs. LazyLoop may reuse an exact verified result while allowing independent replications. Stop run pauses the worker; Resume investigation continues a nonterminal checkpoint.',
  [('Measurements', 'Read results and uncertainty together'), ('Decisions', 'Inspect execution, reuse and stopping reasons'), ('Run controls', 'Stop run  /  Resume investigation')]),
 ('Keep the evidence', 'Review the outcome, then export.',
  'A budget stop does not confirm a hypothesis. In Provenance and export, prepare a portable ZIP bundle. In Guest mode, Open research bundle restores saved history. Review imported settings before resuming.',
  [('Outcome', 'Separate run status from scientific evidence'), ('Provenance & export', 'Prepare and download a portable ZIP'), ('Open research bundle', 'Restore history; review before resume')]),
 ('Choose your AI server', 'Local or remote, with the same workflow.',
  'Configure a reachable Ollama-compatible HTTP or HTTPS base URL and discover installed models. Inference may be remote; experiments and files stay on the app host. Learn and help includes the research lesson and practice questions.',
  [('AI connection', 'Local or remote Ollama-compatible server'), ('App host', 'Runs experiments and stores research files'), ('Learn & help', 'Captioned lesson  /  chapters  /  quizzes')]),
]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def build(encoder):
 OUT.mkdir(parents=True, exist_ok=True)
 fonts = {k: ImageFont.truetype(BOLD if k in ('title','card') else FONT, v) for k,v in [('title',42),('body',25),('small',18),('card',23),('detail',21)]}
 def frame(index, tick):
  title, subtitle, transcript, cards = SCENES[index]
  im = Image.new('RGB', (1280,720), '#0b1520'); d = ImageDraw.Draw(im)
  d.text((55,32),'SLOTHLAB + LAZYLOOP',font=fonts['small'],fill='#91e1bd')
  d.text((970,32),f'PRODUCT WALKTHROUGH   {index+1}/6',font=fonts['small'],fill='#afc6db')
  d.text((55,95),title,font=fonts['title'],fill='#f3f7fb')
  d.text((55,157),subtitle,font=fonts['body'],fill='#a9c6e1')
  d.rounded_rectangle((55,220,570,608),radius=20,fill='#152437',outline='#30445b',width=2)
  d.text((80,247),f'{index+1:02}  WHAT TO DO',font=fonts['small'],fill='#91e1bd')
  lines=textwrap.wrap(transcript,34)
  for n,line in enumerate(lines):d.text((80,292+n*28),line,font=fonts['detail'],fill='#e1eaf4')
  for j,(heading,detail) in enumerate(cards):
   y=220+j*132
   active=min(2,tick//30)==j
   d.rounded_rectangle((610,y,1225,y+116),radius=16,fill='#20354a' if active else '#152437',outline='#91e1bd' if active else '#30445b',width=2)
   d.text((635,y+17),heading,font=fonts['card'],fill='#f3f7fb')
   for n,line in enumerate(textwrap.wrap(detail,45)):d.text((635,y+55+n*25),line,font=fonts['detail'],fill='#b8cede')
  d.text((55,648),'ILLUSTRATED WORKFLOW • NOT A LIVE SCREEN RECORDING • SILENT / CAPTIONS AVAILABLE',font=fonts['small'],fill='#9eb4c7')
  d.rectangle((55,691,1225,696),fill='#30445b')
  d.rectangle((55,691,55+int(1170*(index*90+tick+1)/540),696),fill='#91e1bd')
  return im
 cmd=[encoder,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','6','-i','-','-an','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'slothlab-demo.mp4')]
 with subprocess.Popen(cmd,stdin=subprocess.PIPE) as p:
  for i in range(6):
   for tick in range(90):p.stdin.write(frame(i,tick).tobytes())
  p.stdin.close()
  if p.wait():raise RuntimeError('Video encoding failed')
 frame(0,0).save(OUT/'slothlab-demo-poster.png')
 # A contact sheet makes every scene reviewable without a video player.
 sheet=Image.new('RGB',(1280,1080))
 for i in range(6):sheet.paste(frame(i,30).resize((640,360)),((i%2)*640,(i//2)*360))
 sheet.save('/tmp/slothlab-docs-demo-contact.png')
 captions=['WEBVTT\n']; transcript=['# Demo transcript\n','90-second silent illustrated walkthrough; not a live screen recording.\n']
 def stamp(s):return f'00:{s//60:02d}:{s%60:02d}.000'
 for i,(title,subtitle,text,cards) in enumerate(SCENES):
  # Short readable caption segments; complete narration is in the transcript.
  sentences=text.split('. ')
  for j,sentence in enumerate(sentences):
   start=i*15+j*15/len(sentences);end=i*15+(j+1)*15/len(sentences)
   def ts(t):return f'00:{int(t)//60:02d}:{int(t)%60:02d}.{int(round(t%1*1000)):03d}'
   captions.append(f'{ts(start)} --> {ts(end)}\n{sentence.strip()}\n')
  transcript.append(f'## {stamp(i*15)[0:8]} — {title}\n\n{text}\n')
 (OUT/'slothlab-demo.vtt').write_text('\n'.join(captions))
 (OUT/'slothlab-demo-transcript.md').write_text('\n'.join(transcript))
 print(OUT/'slothlab-demo.mp4')
if __name__=='__main__':build(sys.argv[1] if len(sys.argv)>1 else 'ffmpeg')
