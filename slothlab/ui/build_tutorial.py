"""Rebuild the bundled silent lesson (development: Pillow and an ffmpeg binary).

Run: python -m slothlab.ui.build_tutorial /path/to/ffmpeg
No encoder is required to view the application or bundled lesson.
"""
from pathlib import Path
import subprocess
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont
from slothlab.ui.learning import ASSETS, CHAPTERS

FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')

def build(encoder: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    title_font = ImageFont.truetype(str(FONT), 34)
    text_font = ImageFont.truetype(str(FONT), 23)
    small_font = ImageFont.truetype(str(FONT), 17)
    command = [encoder,'-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','960x540','-r','8','-i','-','-an','-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(ASSETS/'research-guide.mp4')]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin
    captions = ['WEBVTT\n']
    def timestamp(seconds: int) -> str:
        return f'00:{seconds//60:02}:{seconds%60:02}.000'
    for index, chapter in enumerate(CHAPTERS):
        sentences = textwrap.wrap(chapter.transcript, 84)
        captions.append(f'{timestamp(chapter.start)} --> {timestamp(chapter.start+chapter.duration)}\n{chapter.action}\n')
        for frame in range(chapter.duration*8):
            im = Image.new('RGB',(960,540),'#101f28')
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((32,30,928,510),radius=24,fill='#19323b',outline='#36545b',width=2)
            d.text((65,58),'SLOTHLAB  /  RESEARCH SCHOOL',font=small_font,fill='#9eddbb')
            d.text((65,101),f'{index+1:02}  {chapter.title}',font=title_font,fill='#f1f7f4')
            d.text((65,160),' → '.join(['QUESTION','DESIGN','RUN','CONFIRM','REPORT']),font=small_font,fill='#acc8d0')
            lines = textwrap.wrap(chapter.action, 63)
            for line_no,line in enumerate(lines):
                d.text((65,211+line_no*35),line,font=text_font,fill='#f1f7f4')
            # Deliberate progressive reveal makes this a paced visual lesson.
            reveal = min(len(sentences),1+frame//16)
            for line_no,line in enumerate(sentences[:reveal]):
                d.text((65,315+line_no*23),line,font=small_font,fill='#bfd3d8')
            d.text((65,470),'SILENT ANIMATED LESSON · illustrations, not measured research results',font=small_font,fill='#9eddbb')
            progress = (chapter.start+frame/8)/84
            d.rounded_rectangle((65,495,895,499),radius=2,fill='#36545b')
            d.rounded_rectangle((65,495,65+max(2,int(830*progress)),499),radius=2,fill='#9eddbb')
            process.stdin.write(im.tobytes())
    process.stdin.close()
    error = process.stderr.read().decode() if process.stderr else ''
    if process.wait():
        raise RuntimeError(error)
    (ASSETS/'research-guide.vtt').write_text('\n'.join(captions),encoding='utf-8')

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv)>1 else 'ffmpeg')
