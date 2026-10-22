"""Resolution-independent campus artwork rendered locally with Pygame."""
import os
import math
from pathlib import Path
import pygame
from app_paths import RESOURCE_DIR
from world import PLACES, NODES, EDGES

INK='#294535'; MUTED='#74836e'; PAPER='#faf8ef'; GREEN='#426e4c'; ORANGE='#ee8744'
ROOT=RESOURCE_DIR
FONT_PATH=next((p for p in [ROOT/'assets'/'font.ttf',Path('C:/Windows/Fonts/msyh.ttc'),Path('C:/Windows/Fonts/simhei.ttf')] if p.exists()),None)
_fonts={};_text={}

def font(size,bold=False):
    key=(size,bold)
    if key not in _fonts:
        f=pygame.font.Font(str(FONT_PATH) if FONT_PATH else None,size);f.set_bold(bold);_fonts[key]=f
    return _fonts[key]

def text(surface,content,pos,size=16,color=INK,bold=False,center=False):
    content=str(content);key=(content,size,color,bold)
    if key not in _text:
        if len(_text)>2500:
            _text.clear()
        _text[key]=font(size,bold).render(content,True,color)
    img=_text[key];rect=img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surface.blit(img,rect)
    return rect

def rounded(surface,rect,color,radius=12,border=None,width=1):
    pygame.draw.rect(surface,color,rect,border_radius=radius)
    if border:
        pygame.draw.rect(surface,border,rect,width,border_radius=radius)

def wrap(surface,content,pos,width,size=15,color=MUTED,gap=6):
    line='';y=pos[1]
    for char in content:
        if char=='\n' or (font(size).size(line+char)[0]>width and char not in '。，、；：！？）》」'):
            text(surface,line,(pos[0],y),size,color);y+=size+gap;line='' if char=='\n' else char
        else:
            line+=char
    if line:
        text(surface,line,(pos[0],y),size,color);y+=size+gap
    return y

def tree(s,x,y,r=13):
    pygame.draw.circle(s,'#85ab73',(x+1,y+4),r+2)
    pygame.draw.circle(s,'#accb8d',(x-3,y-2),r)
    pygame.draw.circle(s,'#bcd59b',(x+3,y-5),max(4,r-5))

def building(s,rect,label,fill='#e8e5cc',size=19,vertical=False):
    r=pygame.Rect(rect);rounded(s,r.move(3,5),'#6c8a5740',5)
    rounded(s,r,fill,5,'#78906c',2)
    pygame.draw.line(s,'#fffdf0',(r.left+5,r.top+4),(r.right-6,r.top+4),3)
    pygame.draw.line(s,'#b7bea3',(r.right-5,r.top+7),(r.right-5,r.bottom-7),2)
    if vertical:
        for i,ch in enumerate(label):
            text(s,ch,(r.centerx,r.centery+(i-(len(label)-1)/2)*(size+2)),size,center=True,bold=True)
    else:
        text(s,label,r.center,size,bold=True,center=True)

def court(s,rect,kind='basket'):
    r=pygame.Rect(rect);rounded(s,r,'#d9ab78' if kind=='basket' else '#9ebc81',4,'#fff5dc',3)
    inner=r.inflate(-13,-13);pygame.draw.rect(s,'#f6e9cc',inner,2)
    if kind=='basket':
        pygame.draw.line(s,'#f6e9cc',(r.centerx,inner.top),(r.centerx,inner.bottom),2)
        pygame.draw.circle(s,'#f6e9cc',r.center,min(13,r.height//5),2)
    else:
        pygame.draw.line(s,'#f6e9cc',(inner.left,r.centery),(inner.right,r.centery),2)
        for x in [inner.left+10,inner.right-10]:
            pygame.draw.line(s,'#f6e9cc',(x,inner.top),(x,inner.bottom),1)

def campus():
    s=pygame.Surface((1080,810));s.fill('#eef0db')
    # Lawns and distinct campus blocks.
    for rect in [(105,25,330,125),(140,170,130,160),(305,170,125,160),(470,35,150,295),(675,35,380,295),(115,385,215,335),(385,380,260,150),(380,560,265,160),(690,390,280,320)]:
        rounded(s,rect,'#d4e1ba',13)
    # The original map's road structure stays readable as a separate layer.
    for a,b in EDGES:
        if a.startswith('j') and b.startswith('j'):
            pygame.draw.line(s,'#fffdf4',NODES[a],NODES[b],27)
            pygame.draw.circle(s,'#fffdf4',NODES[a],13)
            pygame.draw.circle(s,'#fffdf4',NODES[b],13)
    for p in PLACES:
        pygame.draw.line(s,'#fffdf4',p.position,p.anchor,15)
    # Dormitories, kept individually identifiable.
    digits={1:'一',2:'二',3:'三',4:'四',5:'五',6:'六',7:'七',8:'八',9:'九'}
    for n,x in [(9,140),(8,200),(7,260),(6,320),(5,380)]:
        building(s,(x-22,43,44,87),digits[n]+'栋','#f3eee0',17,True)
    for n,x,y in [(1,333,205),(3,397,205),(2,333,295),(4,397,295)]:
        building(s,(x-20,y-35,40,66),digits[n]+'栋','#f3eee0',15,True)
    # Landmark architecture.
    building(s,(479,55,119,82),'图书馆','#f5eddb',22)
    building(s,(479,173,125,75),'教学楼','#e6e9d8',23)
    building(s,(479,272,125,49),'实验楼','#e6e9d8',21)
    building(s,(153,174,68,28),'小卖部','#e8c6af',14)
    rounded(s,(153,215,112,43),'#b4cbb0',8,'#78906c')
    text(s,'学生活动',(209,225),16,center=True,bold=True);text(s,'中心',(209,244),16,center=True,bold=True)
    building(s,(167,275,103,55),'食堂','#f1d7b3',24)
    building(s,(48,203,29,67),'加油站','#e6cdbb',13,True)
    # Sun and moon lake: curved outline and an island pavilion.
    lake=pygame.Rect(685,55,210,260)
    rounded(s,lake,'#abd8db',55,'#86bdc3',3)
    for y in [105,160,215,267]:
        for x in [715,775,835]:
            pygame.draw.arc(s,'#92c9ce',(x,y,34,13),0.15,2.9,2)
    rounded(s,(799,60,37,50),'#e7e5cd',10,'#74958a',2)
    text(s,'日月湖',(790,207),27,'#426f72',True,True)
    # Sports area.
    pygame.draw.circle(s,'#fffdf0',(210,465),77);pygame.draw.circle(s,'#8da58e',(210,465),77,3)
    pygame.draw.circle(s,'#dbe6da',(210,465),55);pygame.draw.circle(s,'#a4b9a2',(210,465),55,2)
    text(s,'体育馆',(210,462),24,bold=True,center=True)
    court(s,(305,395,43,106),'tennis');court(s,(305,535,43,57),'tennis')
    rounded(s,(389,390,66,67),'#abd8df',4,'#8cb9bf',2)
    for x in range(401,451,12):
        pygame.draw.line(s,'#e5f2e8',(x,400),(x,446),2)
    text(s,'游泳池',(422,410),15,center=True,bold=True)
    court(s,(390,468,67,54),'tennis');text(s,'网球场',(425,497),14,center=True,bold=True)
    for x in [484,558]:
        for y in [393,455]:
            court(s,(x,y,67,52))
    text(s,'篮球场·东区',(554,435),18,center=True,bold=True)
    for x in [164,240]:
        court(s,(x,620,65,72))
    text(s,'篮球场·西区',(232,652),18,center=True,bold=True)
    pygame.draw.ellipse(s,'#d49a75',(379,561,258,155))
    for inset in [7,14,21]:
        pygame.draw.ellipse(s,'#f7dfbd',(379+inset,561+inset,258-inset*2,155-inset*2),1)
    pygame.draw.rect(s,'#a8be80',(438,586,139,103));pygame.draw.rect(s,'#f5edcc',(438,586,139,103),2)
    pygame.draw.line(s,'#f5edcc',(508,587),(508,688),2);pygame.draw.circle(s,'#f5edcc',(508,637),20,2)
    text(s,'田径场',(508,637),22,center=True,bold=True)
    # East campus.
    admin=[(754,424),(785,456),(823,458),(823,544),(786,544),(749,606),(720,582),(747,524),(719,495)]
    pygame.draw.polygon(s,'#b8c0b7',[(x+3,y+5) for x,y in admin]);pygame.draw.polygon(s,'#ecebdf',admin);pygame.draw.lines(s,'#81917e',True,admin,3)
    text(s,'行政楼',(776,501),22,bold=True,center=True)
    building(s,(904,446,56,112),'红楼','#d5a09a',20,True)
    building(s,(1015,420,51,145),'科创园','#e6e3df',19,True)
    # Little landscape details, avoiding road corridors.
    for x,y in [(954,74),(997,102),(970,142),(1023,173),(952,225),(1012,272),(729,360),(780,360),(827,361),(700,687),(759,693),(890,652),(929,690),(165,565),(212,565),(250,564),(55,110),(45,440)]:
        tree(s,x,y)
    for p in PLACES:
        if p.category=='校门':
            x,y=p.position;pygame.draw.line(s,'#8c9e81',(x-16,y),(x+16,y),5)
            pygame.draw.line(s,'#8c9e81',(x-16,y),(x-16,y+13),5);pygame.draw.line(s,'#8c9e81',(x+16,y),(x+16,y+13),5)
            text(s,p.name,(x,y+25),17,bold=True,center=True)
    text(s,'暨南大学 · 珠海校区',(420,791),23,bold=True,center=True)
    text(s,'北',(32,660),19,bold=True);pygame.draw.polygon(s,GREEN,[(31,640),(17,648),(31,655)])
    text(s,'依照参考图重绘 / 游戏道路示意',(815,788),11,MUTED)
    return s

class Mascots:
    def __init__(self):
        self.images={};self.scaled={}
        for key,name in [('normal','屏幕截图 2026-10-19 195437.png'),('wink','屏幕截图 2026-10-19 195441.png'),('hat','屏幕截图 2026-10-19 123121.png')]:
            path=ROOT/'assets'/'references'/name
            if path.exists():
                # Runtime colour-key blend, including near-white screenshot pixels.
                # This is only a display mask; reference files stay untouched.
                image=pygame.image.load(str(path)).convert_alpha()
                background=pygame.mask.from_threshold(image,(255,255,255,255),(20,20,20,255))
                blend=background.to_surface(setcolor=(0,0,0,0),unsetcolor=(255,255,255,255))
                image.blit(blend,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
                self.images[key]=image

    def draw(self,surface,key,center,height=65,delivery=False,*,phase=0.0,
             pose='idle',facing=1,turn=0.0,age=0.0,opacity=255):
        """Animate the sprite at render time around its grounded foot position.

        Returns the visible bounds so encounter clicks follow its actual pose.
        """
        if key=='normal' and pose in ('idle','accept') and phase%4.9>4.62:
            key='wink'
        if pose in ('celebrate','caught','proud'):
            key='wink' if key!='hat' else 'hat'
        image=self.images.get(key,self.images.get('normal'))
        if image is None:
            rect=pygame.Rect(center[0]-20,center[1]-60,40,60)
            pygame.draw.ellipse(surface,'#f3cc38',rect);return rect
        cache_key=(key,height)
        if cache_key not in self.scaled:
            width=round(image.get_width()*height/image.get_height());self.scaled[cache_key]=pygame.transform.smoothscale(image,(width,height))
        base=self.scaled[cache_key]
        wave=math.sin(phase*2.5);sx=1+.018*wave;sy=1-.02*wave
        angle=2.6*math.sin(phase*1.7);hop=0;x_offset=0
        if pose=='move':
            gait=phase*12
            hop=abs(math.sin(gait))*height*.10
            sx=1+.045*math.cos(gait*2);sy=1-.04*math.cos(gait*2)
            angle=5.5*math.sin(gait)+turn*5
        elif pose=='accept':
            progress=min(1,max(0,age/.64))
            hop=math.sin(progress*math.pi)*height*.19
            sx=1+.07*math.cos(progress*math.tau);sy=1-.07*math.cos(progress*math.tau)
            angle=math.sin(progress*math.tau)*8
        elif pose in ('celebrate','caught'):
            hop=abs(math.sin(phase*8))*height*.18
            angle=math.sin(phase*8)*10
            sx=1+.05*math.cos(phase*16);sy=1-.05*math.cos(phase*16)
            if pose=='caught':
                x_offset=math.sin(age*45)*max(0,1-age/.25)*9
                hop+=max(0,age-.22)*height*.55
        elif pose=='peek':
            reveal=min(1,max(0,age/.55))
            hop=-(1-reveal)*height*.72
            angle=math.sin(phase*4)*9
            x_offset=math.sin(phase*2.8)*4
        elif pose=='scratch':
            angle=-7+3*math.sin(phase*3)
            sy=.98+.018*math.sin(phase*2)
        elif pose=='panic':
            angle=5*math.sin(phase*18)
            hop=abs(math.sin(phase*12))*height*.045
            sx=1+.025*math.sin(phase*18)
        elif pose=='hungry':
            angle=-3+2*math.sin(phase*2)
            sy=.94+.012*math.sin(phase*5);sx=1.025
        elif pose=='proud':
            hop=abs(math.sin(phase*7))*height*.12
            angle=7+4*math.sin(phase*5)
        image=pygame.transform.smoothscale(base,(max(1,round(base.get_width()*sx)),max(1,round(height*sy))))
        if facing<0:
            image=pygame.transform.flip(image,True,False)
        image=pygame.transform.rotate(image,angle)
        opacity=max(0,min(255,int(opacity)))
        image.set_alpha(opacity)
        rect=image.get_rect(midbottom=(round(center[0]+x_offset),round(center[1]-hop)))
        shadow=pygame.Surface((height,height//3+4),pygame.SRCALPHA)
        shadow_width=max(12,round(height*.64-hop*.3))
        pygame.draw.ellipse(shadow,(54,79,45,round(opacity*.18)),((height-shadow_width)//2,4,shadow_width,max(5,height//9)))
        surface.blit(shadow,(round(center[0]-height/2),round(center[1]-5)))
        if pose=='peek':
            # Rising behind a little bush makes the entrance read as a peek.
            old_clip=surface.get_clip()
            surface.set_clip(old_clip.clip(pygame.Rect(0,0,surface.get_width(),max(0,round(center[1])))))
            surface.blit(image,rect);surface.set_clip(old_clip)
            tree(surface,round(center[0]+height*.27),round(center[1]+1),max(7,height//9))
            rect=rect.clip(pygame.Rect(0,0,surface.get_width(),max(0,round(center[1]))))
        else:
            surface.blit(image,rect)
        if pose in ('scratch','hungry','proud'):
            outline='#bb9637';yellow='#efcc48';stroke=max(3,height//22)
            if pose=='scratch':
                hand=(rect.centerx+height*.19+math.sin(phase*12)*height*.018,rect.top+height*.15)
                points=[(rect.right-height*.13,rect.top+height*.50),(rect.right+height*.07,rect.top+height*.35),hand]
                pygame.draw.lines(surface,outline,False,points,stroke+2)
                pygame.draw.lines(surface,yellow,False,points,stroke)
                pygame.draw.circle(surface,yellow,(round(hand[0]),round(hand[1])),max(4,height//23))
                text(surface,'?',(rect.right+height*.09,rect.top-height*.02),max(14,height//5),'#a47a3c',True,True)
            elif pose=='hungry':
                belly=pygame.Rect(rect.centerx-height*.24,rect.top+height*.55,height*.50,height*.21)
                pygame.draw.arc(surface,outline,belly,.1,math.pi-.1,stroke+2)
                pygame.draw.arc(surface,yellow,belly,.1,math.pi-.1,stroke)
                for i in range(2):
                    r=pygame.Rect(rect.centerx-height*.09+i*height*.12,rect.top+height*.68,height*.10,height*.05)
                    pygame.draw.arc(surface,'#bb8f42',r,.1,2.9,max(1,height//80))
                text(surface,'咕噜',(rect.right+height*.04,rect.top+height*.52),max(10,height//10),'#b08548',True)
            else:
                for side in [-1,1]:
                    points=[(rect.centerx+side*height*.22,rect.top+height*.56),
                            (rect.centerx+side*height*.40,rect.top+height*.39),
                            (rect.centerx+side*height*.36,rect.top+height*.25)]
                    pygame.draw.lines(surface,outline,False,points,stroke+2)
                    pygame.draw.lines(surface,yellow,False,points,stroke)
                for i in range(3):
                    angle=-math.pi*.8+i*.28
                    p=(rect.centerx+math.cos(angle)*height*.55,rect.top+height*.1+math.sin(angle)*height*.12)
                    q=(p[0]-height*.03,p[1]-height*.07)
                    pygame.draw.line(surface,'#dda638',p,q,max(2,height//45))
        elif pose=='panic':
            for i in range(2):
                x=rect.right+height*(.04+i*.1)
                y=rect.top+height*(.2+i*.13)+math.sin(phase*10+i)*height*.025
                r=max(3,height//24)
                pygame.draw.polygon(surface,'#74b4cd',[(x,y-r*2),(x-r,y),(x+r,y)])
                pygame.draw.circle(surface,'#74b4cd',(round(x),round(y)),r)
        if delivery:
            sway=math.sin(phase*12)*4 if pose=='move' else math.sin(phase*3)*2
            bx=rect.right-9 if facing>0 else rect.left-15
            bag=pygame.Rect(bx+sway,rect.bottom-height*.34+abs(sway),24,20)
            pygame.draw.arc(surface,'#a56435',(bag.x+6,bag.y-7,12,13),0,math.pi,2)
            rounded(surface,bag,ORANGE,4,'#a56435')
            text(surface,'餐',bag.center,11,'#fffef0',True,True)
        return rect

def speech(surface,content,center,bounds,size=13):
    width=font(size).size(content)[0]+22
    rect=pygame.Rect(0,0,width,size+18);rect.midbottom=(round(center[0]),round(center[1]))
    rect.clamp_ip(bounds)
    rounded(surface,rect,'#fff9df',9,'#d9c88d')
    pygame.draw.polygon(surface,'#fff9df',[(rect.centerx-5,rect.bottom-1),(rect.centerx+4,rect.bottom-1),(rect.centerx+1,rect.bottom+6)])
    text(surface,content,rect.center,size,'#80592e',True,True)

def celebration(surface,center,age,duration=1.0):
    if not 0<=age<duration:
        return
    progress=age/duration
    colors=['#efa454','#e6c254','#8db478','#d58e91']
    for i in range(10):
        angle=i*math.tau/10
        radius=15+progress*40
        x=center[0]+math.cos(angle)*radius
        y=center[1]-30+math.sin(angle)*radius-progress*20
        r=max(1,round((1-progress)*4))
        if i%2:
            pygame.draw.circle(surface,colors[i%4],(round(x),round(y)),r)
        else:
            pygame.draw.polygon(surface,colors[i%4],[(x-r,y),(x,y-r*2),(x+r,y),(x,y+r*2)])

def incident_icon(surface,kind,center,size=80,phase=0):
    """Game-native pictograms: no text glyphs or external image service needed."""
    art=pygame.Surface((180,180),pygame.SRCALPHA)
    pygame.draw.circle(art,'#f7e7be',(90,90),84)
    if kind=='construction':
        for x in (35,129):
            pygame.draw.line(art,'#7a795a',(x,106),(x-9,150),7)
            pygame.draw.line(art,'#7a795a',(x,106),(x+9,150),7)
        rounded(art,(23,75,128,40),'#f3bb45',5,'#9d7846',3)
        for x in range(31,142,28):
            pygame.draw.polygon(art,'#574e37',[(x,78),(x+13,78),(x+29,112),(x+15,112)])
        pygame.draw.circle(art,'#ed9a4c' if math.sin(phase*7)>0 else '#f9df76',(87,57),13)
        pygame.draw.circle(art,'#fff1af',(87,57),6)
        pygame.draw.polygon(art,'#ed8c4e',[(137,116),(121,153),(154,153)])
        pygame.draw.line(art,'#fff4dc',(130,139),(146,139),6)
        pygame.draw.line(art,'#ae6f48',(118,156),(158,156),6)
    elif kind=='urgent':
        hop=round(math.sin(phase*6)*5)
        rounded(art,(34,31+hop,60,113),'#476452',10)
        rounded(art,(40,43+hop,48,82),'#f8f4dc',5)
        pygame.draw.line(art,'#9fae90',(51,55+hop),(76,55+hop),4)
        pygame.draw.circle(art,'#eeb347',(64,86+hop),16)
        pygame.draw.line(art,'#80623d',(64,76+hop),(64,87+hop),4)
        pygame.draw.circle(art,'#80623d',(64,95+hop),2)
        rounded(art,(93,87-hop,61,57),ORANGE,9,'#aa693c',3)
        pygame.draw.arc(art,'#aa693c',(108,72-hop,30,31),0,math.pi,4)
        pygame.draw.line(art,'#fff1ca',(102,108-hop),(145,108-hop),4)
        text(art,'急',(123,125-hop),19,'#fff6db',True,True)
        for x in [106,123,140]:
            pygame.draw.line(art,'#dba454',(x,37),(x-4,55),3)
    elif kind=='hungry':
        pygame.draw.ellipse(art,'#e6d8af',(30,129,121,26))
        pygame.draw.ellipse(art,'#fffcdf',(36,120,108,26))
        pygame.draw.arc(art,'#9d8251',(42,67,97,76),math.pi,math.tau,5)
        pygame.draw.polygon(art,'#d9a76b',[(41,102),(55,132),(126,132),(139,102)])
        pygame.draw.ellipse(art,'#fff3c8',(41,87,98,32))
        pygame.draw.ellipse(art,'#e8b957',(57,90,32,20))
        pygame.draw.circle(art,'#90aa66',(110,103),11)
        pygame.draw.line(art,'#7e6346',(120,79),(154,50),5)
        pygame.draw.line(art,'#7e6346',(112,78),(145,46),5)
        for x in [58,79,101]:
            sway=round(math.sin(phase*4+x)*4)
            pygame.draw.arc(art,'#c1b48f',(x+sway,48,15,30),1.6,4.6,3)
    else:
        # A mischievous yellow dragon peeking over its stolen lunch bag.
        pygame.draw.ellipse(art,'#f1c642',(37,47,105,111))
        pygame.draw.circle(art,'#f5d35e',(88,60),36)
        pygame.draw.circle(art,'#456945',(73,56),8)
        pygame.draw.circle(art,'#263f30',(73,56),4)
        pygame.draw.arc(art,'#46583d',(99,48,15,14),.1,2.9,4)
        pygame.draw.arc(art,'#9d6d3b',(72,65,35,22),3.4,5.9,3)
        rounded(art,(88,109,65,49),ORANGE,10,'#b27942',3)
        pygame.draw.arc(art,'#9c7545',(107,96,27,27),0,math.pi,4)
        text(art,'餐',(120,134),23,'#fff4cf',True,True)
        for x,y in [(32,140),(21,158),(155,60)]:
            pygame.draw.ellipse(art,'#bdaf79',(x,y,12,7))
    image=pygame.transform.smoothscale(art,(size,size))
    surface.blit(image,image.get_rect(center=(round(center[0]),round(center[1]))))
