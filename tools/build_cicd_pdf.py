"""Render the Vietnamese deployment guide with embedded fonts and native flow diagram."""
import re, html
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Preformatted,KeepTogether,Flowable
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT

ROOT=Path(__file__).resolve().parents[1]
pdfmetrics.registerFont(TTFont('ArialVN','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialVN-Bold','C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('ConsolasVN','C:/Windows/Fonts/consola.ttf'))
pdfmetrics.registerFontFamily('ArialVN',normal='ArialVN',bold='ArialVN-Bold',italic='ArialVN',boldItalic='ArialVN-Bold')
W,H=595.28,841.89; margin=48; usable=W-2*margin
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='VNBody',fontName='ArialVN',fontSize=10,leading=15,textColor=colors.HexColor('#243443'),spaceAfter=9,splitLongWords=True))
styles.add(ParagraphStyle(name='VNTitle',fontName='ArialVN-Bold',fontSize=29,leading=36,textColor=colors.HexColor('#0D5B54'),spaceAfter=24))
styles.add(ParagraphStyle(name='VNHeading',fontName='ArialVN-Bold',fontSize=20,leading=27,textColor=colors.HexColor('#0D5B54'),spaceAfter=17))
styles.add(ParagraphStyle(name='VNBullet',parent=styles['VNBody'],leftIndent=14,firstLineIndent=-9,spaceAfter=6))

def safe(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<font name="ConsolasVN">\1</font>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',s)
    return s

class Diagram(Flowable):
    def __init__(self): super().__init__();self.width=usable;self.height=225
    def draw(self):
        c=self.canv
        boxes=[(5,160,'CODE / PR'),(174,160,'TEST + BUILD'),(343,160,'MODEL + AUDIT'),(343,60,'DOCKER HUB'),(174,60,'DEPLOY RIÊNG'),(5,60,'HEALTH / ROLLBACK')]
        for x,y,label in boxes:
            c.setFillColor(colors.HexColor('#E8F3EF'));c.setStrokeColor(colors.HexColor('#93BEB2'));c.roundRect(x,y,150,42,8,fill=1)
            c.setFillColor(colors.HexColor('#0D5B54'));c.setFont('ArialVN-Bold',9);c.drawCentredString(x+75,y+17,label)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(colors.HexColor('#47786B'));c.setLineWidth(1.5);c.line(x1,y1,x2,y2)
            import math
            a=math.atan2(y2-y1,x2-x1)
            for d in [-.5,.5]:c.line(x2,y2,x2-7*math.cos(a+d),y2-7*math.sin(a+d))
        arrow(155,181,174,181);arrow(324,181,343,181);arrow(418,160,418,102);arrow(343,81,324,81);arrow(174,81,155,81)
        c.setFillColor(colors.HexColor('#61726C'));c.setFont('ArialVN',8)
        c.drawCentredString(418,130,'chỉ push tin cậy')
        c.drawString(5,26,'PR dừng sau audit. Publish và deploy là hai bước riêng.')

class NumberedCanvas(canvas.Canvas):
    def __init__(self,*a,**kw):canvas.Canvas.__init__(self,*a,**kw);self.states=[]
    def showPage(self): self.states.append(dict(self.__dict__));self._startPage()
    def save(self):
        total=len(self.states)
        for state in self.states:
            self.__dict__.update(state);self.footer(total);canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    def footer(self,total):
        self.setStrokeColor(colors.HexColor('#D7E4DF'));self.line(margin,42,W-margin,42)
        self.setFont('ArialVN',8);self.setFillColor(colors.HexColor('#5B7169'))
        self.drawString(margin,28,'VoiceScope | CI/CD & Docker | 31/10/2026')
        self.drawRightString(W-margin,28,f'{self._pageNumber} / {total}')

text=(ROOT/'docs/huong-dan-cicd-docker-ai.md').read_text(encoding='utf-8')
assert '@@VERIFICATION@@' not in text
story=[];lines=text.splitlines();i=0;first_section=True
while i<len(lines):
    line=lines[i]
    if line.startswith('# '):
        story.extend([Spacer(1,56),Paragraph('HƯỚNG DẪN THỰC HÀNH',ParagraphStyle(name='eyebrow',fontName='ArialVN-Bold',fontSize=10,leading=16,textColor=colors.HexColor('#61786E'))),Spacer(1,14),Paragraph(safe(line[2:]),styles['VNTitle'])]);i+=1
    elif line.startswith('## '):
        story.append(PageBreak());story.append(Paragraph(safe(line[3:]),styles['VNHeading']));i+=1
        if line.startswith('## 2.'):story.append(Diagram());story.append(Spacer(1,10))
    elif line.startswith('```'):
        lang=line[3:];code=[];i+=1
        while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
        i+=1
        if lang=='text' and any('Code / Pull request' in x for x in code):continue
        size=8.5
        longest=max((pdfmetrics.stringWidth(x,'ConsolasVN',size) for x in code),default=0)
        if longest>usable-24:size=max(7.2,size*(usable-24)/longest)
        assert max((pdfmetrics.stringWidth(x,'ConsolasVN',size) for x in code),default=0)<usable-10, 'Code exceeds available width'
        ps=ParagraphStyle(name='code',fontName='ConsolasVN',fontSize=size,leading=size*1.4,backColor=colors.HexColor('#F0F4F5'),borderColor=colors.HexColor('#D5DFE0'),borderWidth=.4,borderPadding=10,leftIndent=0,spaceBefore=5,spaceAfter=15)
        story.append(Preformatted('\n'.join(code),ps))
    elif line.startswith('- '):story.append(Paragraph('- '+safe(line[2:]),styles['VNBullet']));i+=1
    elif not line.strip():i+=1
    else:
        para=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','```','- ')):para.append(lines[i]);i+=1
        story.append(Paragraph(safe(' '.join(para)),styles['VNBody']))
output=ROOT/'docs/huong-dan-cicd-docker-ai.pdf'
doc=SimpleDocTemplate(str(output),pagesize=(W,H),rightMargin=margin,leftMargin=margin,topMargin=48,bottomMargin=60,title='VoiceScope - Huong dan CI/CD va Docker AI',author='VoiceScope',pageCompression=1)
doc.build(story,canvasmaker=NumberedCanvas)
print(output)
