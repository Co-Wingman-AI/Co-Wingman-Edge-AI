"""Rebuild the 48 x 36 inch research poster; original evidence stays unmodified."""
from pathlib import Path
import math
from reportlab.pdfgen import canvas
from reportlab.lib.colors import toColor as HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'artifacts/poster-assets'
OUT = ROOT / 'output/pdf/Co-Wingman_Research_Poster_48x36.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialBold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
W, H = 1600, 1200
c = canvas.Canvas(str(OUT), pagesize=(3456, 2592))
c.setTitle('Co-Wingman - Hybrid Edge-Cloud AI Research Poster')
c.setAuthor('Mrunal Vibhute; Shrimayee Deshpande; Honey Reddy Daram; Dr. Andrea Ramirez-Salgado')
c.scale(3456 / W, 2592 / H)
NAVY='#07346A'; BLUE='#0875B9'; ORANGE='#F36C21'; INK='#152C42'; MUTED='#4B6174'
LIGHT='#F5F8FC'; LINE='#CCDBE8'; GREEN='#167C62'

def rect(x,y,w,h,fill='white',stroke=None,r=0):
    c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke or fill)); c.setLineWidth(.9)
    c.roundRect(x,H-y-h,w,h,r,stroke=bool(stroke),fill=1)

def text(x,y,s,size=18,bold=False,color=INK,align='left'):
    c.setFillColor(HexColor(color)); c.setFont('ArialBold' if bold else 'Arial',size)
    fn={'left':c.drawString,'center':c.drawCentredString,'right':c.drawRightString}[align]
    fn(x,H-y-size*.82,s)

def para(x,y,s,width,size=17,leading=None,color=INK,bold=False):
    leading=leading or size*1.28
    font='ArialBold' if bold else 'Arial'
    for source in s.split('\n'):
        line=''
        for word in source.split():
            trial=(line+' '+word).strip()
            if line and pdfmetrics.stringWidth(trial,font,size)>width:
                text(x,y,line,size,bold,color); y+=leading; line=word
            else: line=trial
        text(x,y,line,size,bold,color); y+=leading
    return y

def panel(x,y,w,h,title,number):
    rect(x,y,w,h,LIGHT,LINE,9)
    text(x+18,y+17,number,15,True,ORANGE)
    text(x+50,y+13,title,23,True,NAVY)
    rect(x+18,y+49,w-36,2,LINE)

def arrow(points,color=BLUE,width=2,dash=False):
    c.setStrokeColor(HexColor(color)); c.setFillColor(HexColor(color)); c.setLineWidth(width)
    c.setDash(5,3) if dash else c.setDash()
    p=c.beginPath(); p.moveTo(points[0][0],H-points[0][1])
    for x,y in points[1:]: p.lineTo(x,H-y)
    c.drawPath(p,stroke=1); c.setDash()
    (a,b),(x,y)=points[-2:]; theta=math.atan2(y-b,x-a); length=8
    p=c.beginPath(); p.moveTo(x,H-y)
    for ang in [theta+2.65,theta-2.65]: p.lineTo(x+length*math.cos(ang),H-(y+length*math.sin(ang)))
    p.close(); c.drawPath(p,fill=1,stroke=0)

def box(x,y,w,h,title,sub='',color=BLUE,size=17):
    rect(x,y,w,h,'white',color,6)
    lines=title.split('\n'); block=len(lines)*size*1.15+(17 if sub else 0)
    top=y+(h-block)/2
    for s in lines: text(x+w/2,top,s,size,True,INK,'center'); top+=size*1.15
    if sub: text(x+w/2,top+3,sub,13,False,MUTED,'center')

def image_crop(path,x,y,w,h,crop=None):
    im=ImageReader(str(path)); iw,ih=im.getSize()
    cx,cy,cw,ch=crop or (0,0,iw,ih)
    scale=min(w/cw,h/ch)
    dx=x+(w-cw*scale)/2; dy=y+(h-ch*scale)/2
    c.saveState(); p=c.beginPath(); p.rect(dx,H-dy-ch*scale,cw*scale,ch*scale); c.clipPath(p,stroke=0)
    c.drawImage(im,dx-cx*scale,H-dy-(ih-cy)*scale,iw*scale,ih*scale,mask='auto')
    c.restoreState()

rect(0,0,W,H)
rect(0,0,W,8,ORANGE)
text(30,29,'Co-Wingman',48,True,NAVY)
text(30,83,'A Hybrid Edge-Cloud AI Assistant for',31,True,NAVY)
text(30,120,'Real-Time Conversational Recovery Cues',31,True,NAVY)
text(30,165,'Mrunal Vibhute, Shrimayee Deshpande, Honey Reddy Daram, Dr. Andrea Ramirez-Salgado',19)
text(30,191,"University of Florida | Master's in AI Systems | AI Days 2026",17,False,MUTED)
image_crop(ASSETS/'hwcoe-logo.png',1285,28,280,176)
rect(30,222,1540,3,ORANGE)

# Three-column editorial grid.
L,LW=30,290
M,MW=338,740
R,RW=1096,474
panel(L,242,LW,195,'Motivation','01')
para(L+18,310,'Help speakers recover their train of thought with a short, context-aware cue during a conversational pause.',LW-36,20,27)
panel(L,455,LW,334,'Capabilities','02')
items=[('01','Local speech recognition'),('02','60-second rolling context'),('03','Manual or pause triggers'),('04','Portfolio-grounded cues'),('05','Minute summaries'),('06','Optional S3 continuity')]
for i,(n,label) in enumerate(items):
    yy=521+i*40
    rect(L+18,yy,27,27,'#E3EFFA',r=6)
    text(L+31.5,yy+6,n,12,True,BLUE,'center')
    text(L+56,yy+4,label,17,False,INK)
panel(L,807,LW,317,'Privacy & control','03')
y=873
for title,body in [('Audio stays local','No application-created recordings.'),('Bounded cloud input','Recent text goes to UF NaviGator.'),('Storage is opt-in','Saved S3 objects persist until deleted.'),('User-controlled assistance','Pause cues use an energy/silence heuristic, not anxiety detection.')]:
    text(L+18,y,title,17,True,NAVY)
    y=para(L+18,y+24,body,LW-36,15,19)+12

panel(M,242,MW,273,'Speak. Pause. Recover.','04')
# Generated illustration is composed into the PDF; original evidence below is unaltered.
image_crop(ASSETS/'poster-visual-reference.png',M+16,300,MW-32,176,(310,260,699,268))
rect(M+18,480,MW-36,22,'#E3EFFA',r=5)
text(M+MW/2,484,'A brief cue helps the speaker continue the conversation.',14,False,NAVY,'center')

panel(M,533,MW,591,'Hybrid architecture','05')
# A chain across the local zone enters cloud inference and returns to local validation.
zx=M+16; zy=598
rect(zx,zy,468,348,'#EAF5FD','#83B9DE',8)
rect(zx+480,zy,212,348,'#EBF7F0','#87BDA7',8)
text(zx+16,zy+13,'NVIDIA Jetson',22,True,NAVY)
text(zx+16,zy+41,'LOCAL AUDIO, CONTEXT & OUTPUT',12,True,BLUE)
text(zx+496,zy+13,'UF hosted inference',18,True,GREEN)
text(zx+496,zy+41,'BOUNDED TEXT ONLY',12,True,GREEN)

# Input pipeline (local).
box(zx+15,zy+74,132,68,'Microphone\n4 s audio buffer',size=16)
box(zx+166,zy+74,132,68,'NVIDIA\nNeMo ASR',size=16)
box(zx+317,zy+74,136,68,'60 s rolling\ntext context',size=16)
arrow([(zx+147,zy+108),(zx+166,zy+108)])
arrow([(zx+298,zy+108),(zx+317,zy+108)])
box(zx+15,zy+173,132,68,'Manual / pause\ntrigger',size=16)
box(zx+166,zy+173,132,68,'Local portfolio\nselection','optional',size=15)
box(zx+317,zy+173,136,68,'Bounded\nrequest',size=17)
arrow([(zx+385,zy+142),(zx+385,zy+173)])
arrow([(zx+147,zy+199),(zx+156,zy+199),(zx+156,zy+157),(zx+344,zy+157),(zx+344,zy+173)])
arrow([(zx+298,zy+207),(zx+317,zy+207)])

# Cloud call and return; local validation is fully inside the blue zone.
box(zx+497,zy+159,178,56,'UF NaviGator API',color=GREEN,size=16)
box(zx+497,zy+243,178,58,'NVIDIA Nemotron','cue / minute summary',color=GREEN,size=17)
arrow([(zx+453,zy+187),(zx+497,zy+187)],GREEN)
text(zx+474,zy+164,'HTTPS',10,True,GREEN,'center')
arrow([(zx+586,zy+215),(zx+586,zy+243)],GREEN)
box(zx+210,zy+274,243,49,'Validate response',size=17)
arrow([(zx+497,zy+282),(zx+453,zy+298)],GREEN)
box(zx+15,zy+274,168,49,'Terminal cue',size=17)
arrow([(zx+210,zy+298),(zx+183,zy+298)])
text(zx+16,zy+331,'Raw audio stays local. Rolling listening continues during cue calls.',12,True,NAVY)

# Explicit application-mediated storage; links below cloud are excluded.
rect(zx,966,692,140,'#FFF3E8','#E9AE78',8)
text(zx+16,979,'AWS S3',22,True,'#9F430C')
text(zx+118,985,'OPTIONAL PERSISTENCE',12,True,'#9F430C')
text(zx+16,1018,'Summary history',17,True,INK)
text(zx+16,1041,'windows/ + latest.json',14,False,MUTED)
text(zx+269,1018,'Portfolio archive',17,True,INK)
text(zx+269,1041,'portfolios/ + portfolio.json',14,False,MUTED)
text(zx+16,1081,'boto3  |  IAM prefix access  |  SSE-S3  |  No audio or full transcript archive',12,False,'#8B461D')
arrow([(zx+220,946),(zx+220,966)],ORANGE)
arrow([(zx+420,966),(zx+420,946)],ORANGE)
rect(zx+12,950,176,12,'white')
text(zx+12,950,'Jetson app uploads summary + metadata',9,False,'#9F430C')
rect(zx+238,950,165,12,'white')
text(zx+238,950,'Explicit portfolio load / summary reuse',9,False,'#9F430C')
para(zx+514,1018,'Live AWS upload/reload validation pending.',160,13,18,color='#8B461D')

panel(R,242,RW,882,'Results & next steps','06')
# Place the unmodified supplied photograph, clipped only at the page viewport.
image_crop(ASSETS/'jetson-live-output.png',R+18,307,RW-36,267,(340,1310,4660,2050))
text(R+RW/2,585,'Live visual cue demonstrated on Jetson',16,True,NAVY,'center')
rect(R+18,612,RW-36,34,'#E3EFFA',r=5)
text(R+RW/2,621,'CUE: I built them with React and Node',16,True,NAVY,'center')
for i,(value,label,color) in enumerate([('94','audio windows',BLUE),('13','cue requests',ORANGE),('0','dropped windows',GREEN)]):
    xx=R+18+i*149
    rect(xx,660,140,83,'white',LINE,7)
    text(xx+70,670,value,36,True,color,'center')
    text(xx+70,715,label,14,False,INK,'center')

tx=R+18; ty=758; tw=RW-36
rect(tx,ty,tw,30,'#E1EBF5',r=3)
text(tx+12,ty+8,'Measured stage',14,True,NAVY)
text(tx+283,ty+8,'Median',14,True,NAVY,'center')
text(tx+389,ty+8,'p95',14,True,NAVY,'center')
for i,(name,median,p95) in enumerate([('ASR inference','110 ms','127 ms'),('Cue handling','1.04 s','2.54 s'),('Summary update','1.42 s','1.99 s')]):
    yy=ty+30+i*29
    rect(tx,yy,tw,29,'white' if i%2==0 else '#EDF3F8')
    text(tx+12,yy+7,name,14)
    text(tx+283,yy+7,median,14,True,INK,'center')
    text(tx+389,yy+7,p95,14,True,INK,'center')
para(tx,887,'Timing sample: pause-assist-05; photo from a separate demo. 69 voiced windows, 7 summaries, zero recorded stage failures. Cue timing excludes capture wait; a completed request may offer no cue.',tw,12.6,17)
text(tx,968,'NEXT STEPS',15,True,ORANGE)
for i,s in enumerate(['Reduce four-second buffering delay','Evaluate cue usefulness with users','Validate AWS upload and recovery','Evaluate experimental disfluency scoring']):
    text(tx,997+i*25,str(i+1).zfill(2),13,True,ORANGE)
    text(tx+29,997+i*25,s,15)

rect(0,1144,W,56,NAVY)
text(30,1163,'Local speech processing  /  Bounded cloud reasoning  /  Optional persistent memory',18,True,'white')
text(1570,1165,'github.com/Co-Wingman-AI/Co-Wingman-Edge-AI',14,False,'white','right')
c.showPage(); c.save()
print(OUT)
