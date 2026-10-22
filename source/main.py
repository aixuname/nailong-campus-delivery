"""Local Python desktop game. Run with: python -B main.py"""
import os
import sys
from pathlib import Path

sys.dont_write_bytecode=True
from app_paths import APP_DIR, ASSET_DIR
ROOT=APP_DIR
(ROOT/'data').mkdir(exist_ok=True)
(ROOT/'data'/'temp').mkdir(exist_ok=True)
for key in ('TEMP','TMP','TMPDIR'):
    os.environ[key]=str(ROOT/'data'/'temp')
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
if (ROOT/'vendor').exists():
    sys.path.insert(0,str(ROOT/'vendor'))

import json
import math
import random
import time
import pygame
from world import PLACES, BY_ID, NODES, START
from engine import Event, Network, edge_key
from audio import SoundManager
from incidents import IncidentMixin
from experience import ExperienceMixin
from visuals import campus, Mascots, text, wrap, rounded, font, speech, celebration, INK, MUTED, PAPER, GREEN, ORANGE

SIZE=(1480,960)
MAP=pygame.Rect(24,139,1040,780)
SIDE=pygame.Rect(1084,109,372,810)
SCALE=MAP.width/1080
LABELS={
    **{f'dorm{n}':(x,83) for n,x in [(9,140),(8,200),(7,260),(6,320),(5,380)]},
    'dorm1':(333,205),'dorm3':(397,205),'dorm2':(333,295),'dorm4':(397,295),
    'library':(538,96),'teaching':(540,210),'lab':(540,296),'activity':(209,235),
    'shop':(187,187),'food':(219,300),'gas':(63,235),'lake':(790,207),
    'gym':(210,462),'pool':(422,421),'tennis':(425,496),'basket1':(554,435),
    'basket2':(232,652),'track':(508,637),'admin':(776,501),'red':(932,502),
    'science':(1040,490),'north':(90,402),'south':(995,669),'west':(650,786)
}

class Game(ExperienceMixin,IncidentMixin):
    def __init__(self,headless=False,seed=None):
        if headless:
            os.environ.setdefault('SDL_AUDIODRIVER','dummy')
        pygame.mixer.pre_init(22050,-16,2,512)
        pygame.init()
        self.headless=headless
        if headless:
            self.screen=pygame.display.set_mode(SIZE,flags=pygame.HIDDEN)
        else:
            info=pygame.display.Info();factor=min((info.current_w-80)/SIZE[0],(info.current_h-100)/SIZE[1],1)
            factor=max(.5,factor)
            self.screen=pygame.display.set_mode((int(SIZE[0]*factor),int(SIZE[1]*factor)),pygame.RESIZABLE)
        pygame.display.set_caption('奶龙外卖 · 暨珠急送 | 本地 Python 桌面版')
        icon_path=ASSET_DIR/'app-icon.png'
        if icon_path.exists():
            pygame.display.set_icon(pygame.image.load(str(icon_path)))
        self.canvas=pygame.Surface(SIZE);self.base=pygame.transform.smoothscale(campus(),MAP.size)
        self.map_bounds=MAP
        self.mascots=Mascots();self.rng=random.Random(seed)
        self.audio=SoundManager(headless=headless)
        self.mode=4;self.round=0;self.event_enabled=True;self.fast=False;self.running=True
        self.modal=None;self.order_scroll=0;self.buttons=[];self.screen_scale=1;self.screen_offset=(0,0)
        self.hover=None;self.toast='';self.toast_until=0
        self.score_file=ROOT/'data'/'records-v2.json'
        try:
            self.records=json.loads(self.score_file.read_text(encoding='utf-8'))
            if not isinstance(self.records,dict):
                self.records={}
        except (OSError,ValueError):
            self.records={}
        self.new_round()

    def message(self,content):
        self.toast=content;self.toast_until=time.monotonic()+4

    def new_round(self,mode=None):
        if mode is not None:
            self.mode=mode
        self.round+=1;self.state='planning';self.selected=[];self.delivered=set();self.order_scroll=0
        self.toast='';self.toast_until=0
        self.event=Event('配送途中有惊喜','途中会出现互动事件，奶龙会停下来等你做决定。') if self.event_enabled else Event('随机事件已关闭','本局所有道路正常通行。')
        self.network=Network(self.event)
        pool=[p.id for p in PLACES if p.id!=START]
        self.orders=self.rng.sample(pool,self.mode) if self.mode else [p.id for p in PLACES]
        self.started=time.monotonic();self.planning_seconds=0;self.cost=0;self.best_order=[];self.best_cost=0;self.exact=True
        self.rider=NODES[START];self.leg_index=0;self.edge_index=0;self.edge_progress=0;self.finished_cost=0
        self.anim_time=0.0;self.facing=1;self.turn=0.0;self.walk_direction=(0,0)
        self.pose='idle';self.reaction_at=-10.0;self.pause=0.0;self.pending_finish=False
        self.say='先送哪一家呀？';self.say_until=3.2;self.effects=[]
        self.egg_spawned=0.0;self.egg_rect=None;self.egg_departure=None
        self.encounters=0;self.egg=None;self.egg_at=time.monotonic()+self.rng.uniform(5,11);self.egg_until=0
        self.modal=None;self.best_visible=False
        self.init_incidents()
        self.init_experience()

    def toggle_place(self,id):
        if self.state not in ('planning','replanning'):
            return
        if self.state=='replanning' and id not in self.pending_required:
            self.message('请先安排本轮剩余订单；已送达的地点无需再送。');return
        if id not in self.orders:
            self.message('这不是本局订单；选择「自由」即可安排全部 29 个地点。');return
        self.remember_order()
        if id in self.selected:
            self.selected.remove(id)
        else:
            self.selected.append(id)
            self.audio.play('select')
            self.pose='accept';self.reaction_at=self.anim_time
            self.say=self.rng.choice(['接到一单！','好耶，有饭送！','包在奶龙身上！'])
            self.say_until=self.anim_time+1.4
        self.order_scroll=0
        if self.state=='replanning':
            self.refresh_estimate()

    def start(self):
        if self.state=='replanning':
            self.resume_replan();return
        if self.state!='planning' or not self.selected or (self.mode and len(self.selected)!=self.mode):
            return
        self.planning_seconds=int(time.monotonic()-self.started)
        self.reset_order_history()
        self.cost,self.path=self.network.route(self.selected)
        self.best_cost,self.best_order,self.exact=self.network.optimize(self.selected)
        self.state='delivering';self.leg_index=0;self.egg=None
        self.audio.play('start')
        self.egg_rect=None;self.pose='accept';self.reaction_at=self.anim_time;self.pause=.65
        self.say='热乎外卖，出发喽！';self.say_until=self.anim_time+2
        self.schedule_incidents()
        self.prepare_leg()

    def prepare_leg(self):
        self.is_supply_leg=bool(self.supply_pending)
        self.leg_target=self.supply_pending or self.selected[self.leg_index]
        self.leg_cost,self.leg_path=self.network.shortest(self.current_node,self.leg_target)
        self.edge_index=0;self.edge_progress=0
        if len(self.leg_path)==1:
            self.rider=NODES[self.leg_path[0]]

    def finish(self):
        self.seal_stage()
        self.cost=sum(stage['cost'] for stage in self.stages)
        self.best_cost=sum(stage['best_cost'] for stage in self.stages)
        self.best_order=[id for stage in self.stages for id in stage['best_order']]
        self.exact=all(stage['exact'] for stage in self.stages)
        self.state='complete';self.best_visible=True;self.rider=NODES[self.selected[-1]]
        self.pose='celebrate';self.reaction_at=self.anim_time
        self.audio.play('success')
        self.score=100 if self.cost<=1e-9 else min(100,round(self.best_cost/self.cost*100))
        # For >12 deliveries, best_order is explicitly a reference, never called globally optimal.
        key=str(self.mode or 'free')
        old=self.records.get(key,{})
        if not isinstance(old,dict):
            old={}
        if self.score>old.get('score',-1) or (self.score==old.get('score') and self.planning_seconds<old.get('seconds',math.inf)):
            self.records[key]={'score':self.score,'seconds':self.planning_seconds,'count':len(self.selected)}
            try:
                temporary=self.score_file.with_suffix('.tmp');temporary.write_text(json.dumps(self.records,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(self.score_file)
            except OSError:
                self.message('无法保存本机成绩，请检查项目目录的写入权限。')
        self.modal='result'

    def update(self,dt):
        dt=max(0.0,dt);self.anim_time+=dt
        self.update_drag(dt)
        if self.replay:
            self.update_replay(dt);return
        now=time.monotonic()
        self.effects=[effect for effect in self.effects if self.anim_time-effect[1]<1.1]
        if self.egg_departure and self.anim_time-self.egg_departure[1]>1.0:
            self.egg_departure=None
        if self.state=='planning':
            if self.pose=='accept' and self.anim_time-self.reaction_at>=.64:
                self.pose='idle'
            if self.modal:
                return
            if self.egg and now>=self.egg_until:
                self.egg=None;self.egg_rect=None;self.egg_at=now+self.rng.uniform(8,16)
            elif not self.egg and now>=self.egg_at:
                self.egg=self.rng.choice(PLACES).id;self.egg_until=now+8;self.egg_spawned=self.anim_time
                self.audio.play('select')
            return
        if self.state=='chasing':
            if not self.modal:
                self.chase_remaining=max(0,self.chase_remaining-dt)
                if self.chase_remaining<=0:
                    self.finish_chase(False)
            return
        if self.state!='delivering':
            return
        if self.modal:
            return
        remaining_time=dt
        while remaining_time>1e-9 and self.state=='delivering':
            if self.pause>0:
                wait=min(self.pause,remaining_time);self.pause-=wait;remaining_time-=wait
                if self.pause>1e-9:
                    break
                if self.pending_finish:
                    self.finish();break
                self.pose='move'
            if self.edge_index>=len(self.leg_path)-1:
                self.current_node=self.leg_target;self.stage_visits.append(self.leg_target)
                self.finished_cost+=self.leg_cost
                if self.is_supply_leg:
                    self.supply_pending=None
                else:
                    self.delivered.add(self.leg_target);self.stage_orders.append(self.leg_target);self.leg_index+=1
                    if self.leg_target==self.urgent_target:
                        if self.leg_index<=self.urgent_deadline:
                            self.event_badges+=1;self.audio.play('badge')
                            self.message('加急订单两站内送达！加急徽章 +1。')
                        self.urgent_target=None
                self.pose='celebrate';self.reaction_at=self.anim_time
                self.audio.play('deliver')
                self.say='补充能量，继续送餐！' if self.is_supply_leg else self.rng.choice(['开饭啦！','热乎的，趁热吃！','送到啦，嘿嘿！']);self.say_until=self.anim_time+1.5
                self.effects.append((self.rider,self.anim_time))
                if self.leg_index>=len(self.selected):
                    self.pending_finish=True;self.pause=1.25
                else:
                    if not self.is_supply_leg and self.maybe_incident():
                        break
                    self.pause=.7;self.prepare_leg()
                continue
            a,b=self.leg_path[self.edge_index:self.edge_index+2]
            segment=math.dist(NODES[a],NODES[b])*self.event.slow.get(edge_key(a,b),1)
            speed=900 if self.fast else 190
            remaining=segment-self.edge_progress;travel=min(remaining,remaining_time*speed)
            self.edge_progress+=travel;remaining_time-=travel/speed
            dx=NODES[b][0]-NODES[a][0];dy=NODES[b][1]-NODES[a][1]
            direction=(1 if dx>0 else -1 if dx<0 else 0,1 if dy>0 else -1 if dy<0 else 0)
            if direction!=self.walk_direction:
                self.turn=max(-1,min(1,(self.walk_direction[0]*direction[1]-self.walk_direction[1]*direction[0])))
                self.walk_direction=direction
            self.turn*=math.exp(-dt*4)
            if dx:
                self.facing=1 if dx>0 else -1
            self.pose='move'
            t=self.edge_progress/segment if segment else 1
            self.rider=tuple(NODES[a][i]+(NODES[b][i]-NODES[a][i])*t for i in (0,1))
            if self.edge_progress>=segment-1e-8:
                self.edge_index+=1;self.edge_progress=0

    @staticmethod
    def map_point(point):
        return (MAP.x+round(point[0]*SCALE),MAP.y+round(point[1]*SCALE))

    def line(self,path,color,width=4,dashed=False):
        for a,b in zip(path,path[1:]):
            p,q=self.map_point(NODES[a]),self.map_point(NODES[b])
            if not dashed:
                pygame.draw.line(self.canvas,color,p,q,width)
            else:
                distance=math.dist(p,q)
                for offset in range(0,int(distance),15):
                    lo=offset/max(1,distance);hi=min(offset+8,distance)/max(1,distance)
                    u=tuple(p[i]+(q[i]-p[i])*lo for i in (0,1));v=tuple(p[i]+(q[i]-p[i])*hi for i in (0,1))
                    pygame.draw.line(self.canvas,color,u,v,width)

    def button(self,key,label,rect,callback,primary=False,active=False,enabled=True,size=15):
        rect=pygame.Rect(rect)
        fill=ORANGE if primary else '#e3ecd9' if active else '#fffdf6'
        if not enabled:
            fill='#e9ebdf'
        rounded(self.canvas,rect,fill,9,'#d8e0cf')
        text(self.canvas,label,rect.center,size,'#fffdf4' if primary and enabled else INK if enabled else '#a1ab95',active or primary,True)
        if enabled:
            self.buttons.append((key,rect,callback))

    def draw_map(self):
        c=self.canvas;rounded(c,(24,109,1040,810),'#fffdf6',14,'#dce2d2')
        text(c,'暨南大学 · 珠海校区',(43,115),15,GREEN,True)
        text(c,'29 个地点全部开放  /  选择「自由」任意选点',(650,117),13,MUTED)
        c.blit(self.base,MAP)
        replay_stage=self.stages[self.replay['stage']] if self.replay else None
        blocked=replay_stage['blocked'] if replay_stage else self.event.blocked
        slow=replay_stage['slow'] if replay_stage else self.event.slow
        for key in blocked:
            a,b=key;self.line([a,b],'#d86152',13)
            p=self.map_point(tuple((NODES[a][i]+NODES[b][i])/2 for i in (0,1)))
            rounded(c,(p[0]-14,p[1]-14,28,28),'#fff6e8',5,'#ce6855');text(c,'×',p,24,'#bf5144',True,True)
        for key,multiplier in slow.items():
            a,b=key;self.line([a,b],'#78aeca' if multiplier>2 else '#af91c4',12)
            point=self.map_point(tuple((NODES[a][i]+NODES[b][i])/2 for i in (0,1)))
            rounded(c,(point[0]-22,point[1]-12,44,24),'#fffdf4',5,'#c3cfbf');text(c,f'×{multiplier}',point,13,INK,True,True)
        for stage in ([] if self.replay else self.stages):
            if self.best_visible:
                self.line(stage['best_path'],'#398461',6,True)
            self.line(stage['path'],ORANGE,4)
        if self.selected and not self.replay:
            self.line(self.projected_path(),ORANGE,4)
        for p in PLACES:
            pos=self.map_point(p.position);index=self.selected.index(p.id)+1 if p.id in self.selected else 0
            active=p.id in self.orders;done=p.id in self.delivered
            if replay_stage:
                active=p.id in set(replay_stage['visits']+replay_stage['best_order'])
                done=active
            color='#4f8c62' if done else GREEN if index else ORANGE if active else '#a7b397'
            pygame.draw.circle(c,'#fffdf4',pos,14 if active else 9)
            pygame.draw.circle(c,color,pos,11 if active else 6)
            if active:
                text(c,'达' if done else str(index) if index else '+',pos,12,'#ffffff',True,True)
        if self.egg:
            pos=self.map_point(NODES[self.egg]);center=(pos[0],pos[1]-13)
            age=max(0,self.anim_time-self.egg_spawned)
            pygame.draw.circle(c,'#eed466',(center[0],center[1]-27),round(38+3*math.sin(self.anim_time*5)),2)
            remaining=max(0,self.egg_until-time.monotonic())
            self.egg_rect=self.mascots.draw(c,'wink',center,70,phase=self.anim_time,pose='peek',age=age,opacity=min(255,remaining*510))
            # Use the displayed rect, including its current bob/tilt, for clicks.
            self.egg_rect=self.egg_rect.inflate(8,6).clip(MAP)
            if age>.3:
                speech(c,'奶龙出没！点我',(center[0],center[1]-84),MAP)
        else:
            self.egg_rect=None
        if self.egg_departure:
            id,at=self.egg_departure;age=self.anim_time-at;pos=self.map_point(NODES[id])
            center=(pos[0]+max(0,age-.25)*70,pos[1]-13)
            self.mascots.draw(c,'wink',center,70,phase=self.anim_time,pose='caught',age=age,opacity=255*(1-max(0,age-.55)/.45))
            celebration(c,center,age)
            speech(c,'好耶！徽章 +1',(center[0],center[1]-96),MAP)
        rider=self.map_point(self.rider);rider=(rider[0],rider[1]-8)
        if not self.replay:
            self.mascots.draw(c,'normal',rider,80,delivery=self.state!='chasing',phase=self.anim_time,
                              pose=self.pose,facing=self.facing,turn=self.turn,age=self.anim_time-self.reaction_at)
        else:
            self.draw_replay_map()
        for point,at in self.effects:
            celebration(c,self.map_point(point),self.anim_time-at)
        if self.anim_time<self.say_until and not self.replay:
            speech(c,self.say,(rider[0],rider[1]-103),MAP)
        self.draw_incident_map()
        if self.hover and not self.modal:
            p=BY_ID[self.hover];pos=self.map_point(p.position)
            tip=pygame.Rect(pos[0]-58,max(MAP.y,pos[1]-42),116,25)
            tip.clamp_ip(MAP);rounded(c,tip,'#fff9dc',5,'#d7c68e');text(c,p.name,tip.center,12,INK,True,True)

    def draw_panel(self):
        c=self.canvas;rounded(c,SIDE,'#fffdf6',14,'#dce2d2')
        text(c,'YOUR DELIVERY',(1105,128),11,MUTED,True)
        text(c,f'第 {self.round:02} 趟',(1378,128),12,MUTED)
        text(c,'奶龙送餐，你来指路',(1105,153),24,INK,True)
        for i,(mode,label) in enumerate([(4,'4 单'),(6,'6 单'),(8,'8 单'),(0,'自由')]):
            self.button(f'mode{mode}',label,(1105+i*83,200,77,34),lambda mode=mode:self.new_round(mode),active=self.mode==mode,enabled=self.state in ('planning','complete'))
        text(c,'自由模式可选全部 29 地点，包括食堂补给点。',(1105,244),12,MUTED)
        event_rect=(1105,270,329,81);rounded(c,event_rect,'#f0f3e8',9)
        text(c,self.event.title,(1118,280),16,GREEN,True)
        wrap(c,self.event.description,(1118,308),302,12,MUTED,4)
        arranged=f'{len(self.selected)} / {len(self.orders)}' if self.mode else f'{len(self.selected)} / 29'
        text(c,'配送顺序',(1105,368),16,INK,True);text(c,arranged,(1223,370),14,MUTED)
        self.button('undo','撤销',(1292,363,73,30),self.undo_order,enabled=self.state in ('planning','replanning') and bool(self.order_history),size=12)
        self.button('clear','重排' if self.state=='replanning' else '清空',(1374,363,60,30),self.clear,enabled=self.state in ('planning','replanning'),size=12)
        view=pygame.Rect(1105,407,329,280);rounded(c,view,'#f7f7ee',8)
        if self.state=='replanning':
            listing=self.selected+[p for p in self.orders if p in self.pending_required and p not in self.selected]
        elif self.mode:
            listing=self.selected+[p for p in self.orders if p not in self.selected]
        else:
            listing=self.selected
        if not listing:
            wrap(c,'点击地图上的橙色圆点或建筑名称，挑选你想配送的地点。再次点击可移除。',(1122,431),293,15)
        self.order_rows=[]
        old_clip=c.get_clip();c.set_clip(view)
        max_scroll=max(0,len(listing)*46-view.height+4);self.order_scroll=max(0,min(self.order_scroll,max_scroll))
        for i,id in enumerate(listing):
            y=411+i*46-self.order_scroll
            if y+42<view.top or y>view.bottom:
                continue
            idx=self.selected.index(id)+1 if id in self.selected else 0
            rect=pygame.Rect(1111,y,314,40);rounded(c,rect,'#e9efdf' if idx else '#fffdf6',7,'#dce3d0')
            badge=pygame.Rect(1121,y+7,27,26);rounded(c,badge,GREEN if idx else '#e8ebdc',6)
            text(c,'达' if id in self.delivered else idx if idx else '+',badge.center,13,'#fffdf6' if idx else MUTED,True,True)
            text(c,BY_ID[id].name,(1160,y+9),14,INK,True)
            editable=self.state=='planning' or (self.state=='replanning' and id in self.pending_required)
            text(c,'拖动' if idx and editable else BY_ID[id].category,(1363,y+12),11,MUTED)
            clipped=rect.clip(view)
            if clipped.height and (self.state=='planning' or (self.state=='replanning' and id in self.pending_required)):
                self.order_rows.append((id,clipped.copy()))
                self.buttons.append((f'order-{id}',clipped,lambda id=id:self.toggle_place(id)))
        c.set_clip(old_clip)
        if max_scroll:
            bar_height=max(30,view.height*view.height/(len(listing)*46));bar_y=view.y+(view.height-bar_height)*self.order_scroll/max_scroll
            rounded(c,(1428,bar_y,4,bar_height),'#a7b996',2)
        cost=self.network.route(self.selected)[0] if self.state=='planning' else self.cost
        seconds=int(time.monotonic()-self.started) if self.state=='planning' else self.planning_seconds
        text(c,'预计通行成本',(1107,707),12,MUTED);text(c,'规划用时',(1290,707),12,MUTED)
        text(c,f'{cost:.0f}',(1105,730),28,INK,True);text(c,'单位',(1195,744),11,MUTED)
        text(c,f'{seconds//60:02}:{seconds%60:02}',(1285,730),27,INK,True)
        enabled=self.state=='planning' and bool(self.selected) and (not self.mode or len(self.selected)==self.mode)
        label='奶龙，出发！' if enabled else '正在配送…' if self.state=='delivering' else '本趟已送达' if self.state=='complete' else '点击地点，安排配送顺序'
        if self.state=='replanning':
            enabled=set(self.selected[self.leg_index:])==self.pending_required
            label='继续配送！' if enabled else '请排好全部剩余订单'
        elif self.state in ('incident','chasing'):
            label='事件中 · 配送已暂停'
        self.button('start',label,(1105,784,329,45),self.start,primary=enabled,enabled=enabled)
        self.button('new','换一组 / 重新开始',(1105,842,209,37),self.new_round,size=13)
        self.button('speed','加速 ON' if self.fast else '加速 OFF',(1322,842,112,37),self.toggle_speed,active=self.fast,size=12)
        text(c,'橙线：你的路线  |  绿虚线：优选路线',(1108,893),12,MUTED)

    def clear(self):
        if self.state=='planning':
            if not self.selected:return
            self.remember_order()
            self.selected=[];self.order_scroll=0
        elif self.state=='replanning':
            if len(self.selected)==self.leg_index:return
            self.remember_order()
            self.selected=self.selected[:self.leg_index];self.order_scroll=0;self.refresh_estimate()

    def toggle_speed(self):
        self.fast=not self.fast

    def toggle_events(self):
        self.event_enabled=not self.event_enabled;self.new_round()

    def draw_modal(self):
        if not self.modal:
            return
        self.buttons=[]
        shade=pygame.Surface(SIZE,pygame.SRCALPHA);shade.fill((26,45,30,170));self.canvas.blit(shade,(0,0))
        box=pygame.Rect(390,105,700,752);rounded(self.canvas,box,'#fffdf2',20,'#d6dec9')
        if self.modal!='incident':
            self.button('close','×',(1024,120,43,37),self.close_modal,size=23)
        if self.modal=='incident':
            self.draw_incident_modal()
        elif self.modal=='help':
            text(self.canvas,'当奶龙的路线指挥官',(440,154),31,INK,True)
            y=219
            for title,body in [
                ('01  配送途中会有惊喜','4 单途中一次事件，6 / 8 单两次；先送两单再出事件，中间留出配送时间。配送暂停，做完选择后继续。'),
                ('02  点地点，拖订单','自由模式可点全部 29 地点。右侧已选订单可拖动重排，点“撤销”或 Ctrl+Z 退回上一步。'),
                ('03  奶龙沿路送餐','从食堂出发，送完最后一单即可，不必返回。途中经过某地点不自动送达，按你安排的顺序配送。'),
                ('04  分段评分，徽章另算','事件前后分别从各自起点比较路线成本，再合计得分；补给会比较两个店。每段 12 单内精确优化，更多使用参考优选。')]:
                text(self.canvas,title,(442,y),20,GREEN,True);y=wrap(self.canvas,body,(442,y+37),591,16,MUTED,8)+29
            text(self.canvas,'快捷键：空格出发 / N 新一局 / F 加速 / H 帮助',(442,746),14,MUTED)
            self.button('gotit','懂了，接单！',(441,787,594,43),self.close_modal,primary=True)
        elif self.modal=='audio':
            text(self.canvas,'给奶龙一点节奏',(440,154),31,INK,True)
            wrap(self.canvas,'轻快的校园送餐配乐，搭配接单、送达和彩蛋反馈。音乐与音效可分别开关、调节音量。',(442,209),590,16)
            for kind,title,y in [('music','背景音乐',297),('effects','游戏音效',463)]:
                text(self.canvas,title,(442,y),21,GREEN,True)
                is_on=self.audio.settings[kind]
                self.button('toggle-'+kind,'已开启' if is_on else '已关闭',(441,y+44,145,45),lambda kind=kind:self.audio.toggle(kind),active=is_on)
                self.button('minus-'+kind,'−',(610,y+44,55,45),lambda kind=kind:self.audio.volume(kind,-.1),size=23)
                text(self.canvas,f"{round(self.audio.settings[kind+'_volume']*100)}%",(719,y+66),22,INK,True,True)
                self.button('plus-'+kind,'+',(775,y+44,55,45),lambda kind=kind:self.audio.volume(kind,.1),size=23)
                if kind=='effects':
                    self.button('preview-sfx','试听送达音效',(850,y+44,185,45),lambda:self.audio.play('deliver'),size=14)
            text(self.canvas,'M：切换音乐     S：切换音效',(442,631),17,MUTED)
            text(self.canvas,'音量设置会保存在本项目，下次启动自动沿用。',(442,671),14,MUTED)
            if not self.audio.available:
                wrap(self.canvas,'当前音频设备不可用，游戏可继续运行。连接音频设备后重新启动即可。',(442,711),590,14,'#b47344')
            self.button('audio-back','设置好了，继续送餐！',(441,787,594,43),self.close_modal,primary=True)
        elif self.modal=='record':
            text(self.canvas,'本机最佳成绩',(440,158),31,INK,True)
            for i,(key,label) in enumerate([('4','轻松 4 单'),('6','进阶 6 单'),('8','挑战 8 单'),('free','自由选点')]):
                value=self.records.get(key,{});y=240+i*100
                rounded(self.canvas,(441,y,594,76),'#f0f3e7',10)
                text(self.canvas,label,(462,y+23),20,INK,True)
                info=f"{value.get('score',0)} 分 · {value.get('seconds',0)} 秒" if value else '还没有成绩，去试试吧'
                text(self.canvas,info,(697,y+27),18,MUTED)
            wrap(self.canvas,'成绩保存在本项目 data/records-v2.json 中。不同事件和自由订单的成绩只用于轻松记录。',(442,690),580,15)
            self.button('back','继续游戏',(441,787,594,43),self.close_modal,primary=True)
        else:
            self.mascots.draw(self.canvas,'wink',(740,248),105,phase=self.anim_time,pose='celebrate')
            title='每一段都很顺，奶龙为你点赞！' if self.exact and abs(self.cost-self.best_cost)<1e-6 else '外卖全部送达，开饭啦！'
            text(self.canvas,title,(740,277),28,INK,True,True)
            text(self.canvas,'★ ★ ★' if self.score>=95 else '★ ★ ☆' if self.score>=80 else '★ ☆ ☆',(740,324),31,'#d9a739',True,True)
            for x,label,value in [(454,'你的成本合计',f'{self.cost:.0f}'),(650,'分段最优合计' if self.exact else '参考成本合计',f'{self.best_cost:.0f}'),(846,'路线得分',f'{self.score} 分')]:
                rounded(self.canvas,(x,364,180,90),'#edf2e4',10);text(self.canvas,label,(x+90,387),14,MUTED,center=True);text(self.canvas,value,(x+90,425),28,INK,True,True)
            text(self.canvas,'各阶段最优顺序' if self.exact else '各阶段参考优选（不保证全局最优）',(444,483),19,GREEN,True)
            route_text='\n'.join(f"第 {i+1} 段："+BY_ID[stage['start']].name+' → '+' → '.join(BY_ID[id].name for id in stage['best_order']) for i,stage in enumerate(self.stages))
            area=pygame.Rect(444,516,590,151);clip=self.canvas.get_clip();self.canvas.set_clip(area)
            top=516-self.result_scroll;y=wrap(self.canvas,route_text,(444,top),590,14,INK,7)
            self.result_max_scroll=max(0,y-top-area.height);self.result_scroll=max(0,min(self.result_scroll,self.result_max_scroll));self.canvas.set_clip(clip)
            note='滚轮可查看各段路线 · 事件发生后，从当时位置重新比较。' if self.exact else '含 13 单以上的启发式参考段 · 滚轮查看完整路线。'
            text(self.canvas,note,(444,679),13,MUTED)
            text(self.canvas,f'规划 {self.planning_seconds} 秒  ·  独立徽章 {self.encounters+self.event_badges} 枚  ·  途中事件 {len(self.incident_history)} 次',(444,708),14,MUTED)
            text(self.canvas,'你刚刚玩到的，就是最短路径和路线优化。',(444,741),17,GREEN,True)
            text(self.canvas,'校园算法比赛 · 报名详情请咨询摊位工作人员',(444,768),12,MUTED)
            self.button('again','再来一趟',(441,787,185,43),self.new_round,primary=True)
            self.button('replay','路线回放',(645,787,185,43),self.open_replay)
            self.button('compare','回地图对比',(850,787,185,43),self.close_modal)

    def close_modal(self):
        if self.modal!='incident':
            self.modal=None

    def draw(self):
        c=self.canvas;c.fill(PAPER);self.buttons=[]
        rounded(c,(25,22,48,48),'#f6cf58',13);text(c,'奶',(49,46),26,INK,True,True)
        text(c,'奶龙外卖',(89,21),28,INK,True);text(c,'暨珠急送 · 本地 Python 版',(91,61),13,MUTED)
        text(c,'奶龙接单，路线你来定。',(454,28),30,GREEN,True)
        self.button('audio','音乐 / 音效',(950,29,121,40),lambda:setattr(self,'modal','audio'),active=self.audio.settings['music'],size=13)
        self.button('events','事件 ON' if self.event_enabled else '事件 OFF',(1084,29,111,40),self.toggle_events,active=self.event_enabled,size=14)
        self.button('record','本机成绩',(1205,29,111,40),lambda:setattr(self,'modal','record'),size=14)
        self.button('help','玩法说明',(1326,29,130,40),lambda:setattr(self,'modal','help'),size=14)
        self.draw_map()
        if self.replay:self.draw_replay_panel()
        else:self.draw_panel()
        self.draw_drag()
        status='点击地图标记或建筑名称选点，食堂出发，最后一单送完即结束。'
        if self.state=='delivering':
            status=f'奶龙配送中 {len(self.delivered)} / {len(self.selected)}'
            status+=' · 全部送达，开心庆祝中！' if self.pending_finish else f' · 下一站：{BY_ID[self.supply_pending or self.selected[self.leg_index]].name}'
        elif self.state=='replanning':
            status='施工绕行 · 点击剩余订单重排，已送达订单保留；排好后继续配送。'
        elif self.state=='chasing':
            status=f'找回餐袋 · 跟着小脚印找奶龙，已点中 {self.chase_step} / 3 次。'
        elif self.state=='complete':
            status=f'全部送达 · 得分 {self.score} / 100 · 各阶段分别比较，再合计通行成本。'
        if self.replay:status='路线回放 · 橙色看你的走法，绿色看参考走法；空格暂停，左右键切换阶段。'
        if time.monotonic()<self.toast_until:
            status=self.toast
        text(c,status,(28,932),14,MUTED)
        text(c,f'独立徽章 {self.encounters+self.event_badges} 枚 · 途中事件 {len(self.incident_history)} 次',(1138,932),12,MUTED)
        self.draw_modal()
        sw,sh=self.screen.get_size();self.screen_scale=min(sw/SIZE[0],sh/SIZE[1]);size=(round(SIZE[0]*self.screen_scale),round(SIZE[1]*self.screen_scale));self.screen_offset=((sw-size[0])//2,(sh-size[1])//2)
        self.screen.fill('#263c2e');self.screen.blit(pygame.transform.smoothscale(c,size),self.screen_offset);pygame.display.flip()

    def logical(self,pos):
        return tuple((pos[i]-self.screen_offset[i])/self.screen_scale for i in (0,1))

    def pick_map(self,pos):
        if not MAP.collidepoint(pos):
            return None
        world=((pos[0]-MAP.x)/SCALE,(pos[1]-MAP.y)/SCALE)
        close=[(math.dist(world,p.position),p.id) for p in PLACES if math.dist(world,p.position)<21]
        if close:
            return min(close)[1]
        labels=[(math.dist(world,xy),id) for id,xy in LABELS.items() if abs(world[0]-xy[0])<max(22,len(BY_ID[id].name)*9) and abs(world[1]-xy[1])<23]
        return min(labels)[1] if labels else None

    def click(self,pos):
        if self.click_chase(pos):
            return
        if self.egg and self.egg_rect and not self.modal:
            if self.egg_rect.collidepoint(pos):
                self.egg_departure=(self.egg,self.anim_time)
                self.encounters+=1;self.egg=None;self.egg_rect=None
                self.audio.play('badge')
                self.egg_at=time.monotonic()+self.rng.uniform(10,18);self.message('抓到一只奶龙！获得出没徽章 +1，不影响路线评分。');return
        for key,rect,callback in reversed(self.buttons):
            if rect.collidepoint(pos):
                self.audio.play('tap')
                callback();return
        if not self.modal:
            picked=self.pick_map(pos)
            if picked:
                self.toggle_place(picked)

    def handle(self,event):
        if event.type==pygame.QUIT:
            self.running=False
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=self.logical(event.pos)
            if not self.order_down(pos):self.click(pos)
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
            self.order_up(self.logical(event.pos))
        elif event.type==pygame.MOUSEWHEEL:
            if self.modal=='result':
                self.result_scroll=max(0,min(getattr(self,'result_max_scroll',0),self.result_scroll-event.y*36))
            elif not self.modal and pygame.Rect(1105,407,329,280).collidepoint(self.logical(pygame.mouse.get_pos())):
                self.order_scroll-=event.y*42
        elif event.type==pygame.MOUSEMOTION:
            pos=self.logical(event.pos);self.order_motion(pos)
            self.hover=self.pick_map(pos)
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_m:
                self.audio.toggle('music')
            elif event.key==pygame.K_s:
                self.audio.toggle('effects')
            elif event.key==pygame.K_z and getattr(event,'mod',0)&pygame.KMOD_CTRL:
                self.undo_order()
            elif event.key==pygame.K_ESCAPE:
                if self.order_drag:self.order_drag=None
                elif self.modal:self.close_modal()
                elif self.replay:self.close_replay()
                else:self.running=False
            elif self.modal:
                if event.key in (pygame.K_RETURN,pygame.K_SPACE):self.close_modal()
            elif self.replay:
                if event.key==pygame.K_SPACE:self.toggle_replay()
                elif event.key==pygame.K_LEFT:self.replay_stage(-1)
                elif event.key==pygame.K_RIGHT:self.replay_stage(1)
            elif event.key==pygame.K_SPACE:self.start()
            elif event.key==pygame.K_n:self.new_round()
            elif event.key==pygame.K_f:self.toggle_speed()
            elif event.key==pygame.K_h:self.modal='help'
            elif event.key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4) and self.state in ('planning','complete'):
                self.new_round({pygame.K_1:4,pygame.K_2:6,pygame.K_3:8,pygame.K_4:0}[event.key])

    def run(self):
        clock=pygame.time.Clock()
        while self.running:
            dt=min(clock.tick(60)/1000,.12)
            for event in pygame.event.get():self.handle(event)
            self.update(dt);self.draw()
        pygame.quit()

if __name__=='__main__':
    if '--desktop-check' in sys.argv:
        from desktop_check import run
        raise SystemExit(run(Game(headless=True)))
    Game().run()
