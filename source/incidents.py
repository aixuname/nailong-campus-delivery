"""Interactive mid-delivery incidents and scoring at the actual decision points."""
import math
import pygame
from world import NODES, PLACES, BY_ID, TRUNK_EDGES, START, length
from engine import Event, Network, edge_key
from visuals import text, wrap, rounded, speech, incident_icon, INK, MUTED, GREEN, ORANGE

class IncidentMixin:
    def init_incidents(self):
        self.incident=None;self.incident_history=[];self.event_badges=0
        self.urgent_target=None;self.urgent_deadline=0
        self.supply_pending=None;self.is_supply_leg=False
        self.stages=[];self.stage_start=START;self.current_node=START
        self.stage_orders=[];self.stage_visits=[];self.stage_supply_options=()
        self.pending_required=set();self.chase_rect=None;self.chase_step=0
        self.incident_kinds=self.rng.sample(['construction','urgent','hungry','chase'],4)
        self.incident_schedule=[];self.next_incident=0;self.result_scroll=0

    def schedule_incidents(self):
        count=len(self.selected)
        # Trigger at a delivery stop, so the decision starts at a precise node.
        if not self.event_enabled or count<3:
            self.incident_schedule=[]
        elif count<6:
            self.incident_schedule=[2]
        else:
            # The rider gets at least two deliveries between interruptions.
            self.incident_schedule=[2,max(4,min(count-2,round(count*.67)))]
        self.next_incident=0

    def begin_stage(self,supply_options=()):
        self.stage_start=self.current_node;self.stage_orders=[];self.stage_visits=[]
        self.stage_supply_options=tuple(supply_options)

    def seal_stage(self):
        if not self.stage_visits:
            return
        actual,path=self.network.route(self.stage_visits,self.stage_start)
        if self.stage_supply_options:
            choices=[]
            for site in self.stage_supply_options:
                cost,order,exact=self.network.optimize(self.stage_orders,site)
                choices.append((self.network.shortest(self.stage_start,site)[0]+cost,[site]+order,exact))
            best,order,exact=min(choices,key=lambda row:row[0])
        else:
            best,order,exact=self.network.optimize(self.stage_orders,self.stage_start)
        best_path=self.network.route(order,self.stage_start)[1]
        edges={edge_key(a,b) for p in [path,best_path] for a,b in zip(p,p[1:])}
        self.stages.append({'start':self.stage_start,'visits':list(self.stage_visits),
            'cost':actual,'best_cost':best,'best_order':order,'exact':exact,
            'path':path,'best_path':best_path,'supply_options':self.stage_supply_options,
            'blocked':set(self.event.blocked),'slow':dict(self.event.slow),
            'edge_costs':{edge:length(*edge)*self.event.slow.get(edge,1) for edge in edges}})
        self.stage_visits=[];self.stage_orders=[];self.stage_supply_options=()

    def refresh_estimate(self):
        tail=self.selected[self.leg_index:]
        if self.supply_pending:
            tail=[self.supply_pending]+tail
        self.cost=sum(s['cost'] for s in self.stages)+self.network.route(self.stage_visits+tail,self.stage_start)[0]

    def projected_path(self):
        tail=self.selected[self.leg_index:] if self.state!='planning' else self.selected
        if self.supply_pending:
            tail=[self.supply_pending]+tail
        return self.network.route(self.stage_visits+tail,self.stage_start)[1]

    def construction_event(self):
        future=self.network.route(self.selected[self.leg_index:],self.current_node)[1]
        used=[edge_key(a,b) for a,b in zip(future,future[1:])]
        trunks={edge_key(a,b) for a,b in TRUNK_EDGES}
        for key in dict.fromkeys(used):
            if key not in trunks or key in self.event.blocked:
                continue
            candidate=Event('配送途中 · 前方施工','锥桶所在道路封闭，请重新安排剩余订单。',self.event.blocked|{key},dict(self.event.slow))
            network=Network(candidate)
            try:
                for place in PLACES:
                    network.shortest(self.current_node,place.id)
            except ValueError:
                continue
            return candidate,key
        return None,None

    def trigger_incident(self,kind=None):
        if self.state!='delivering' or self.leg_index>=len(self.selected):
            return False
        kind=kind or self.incident_kinds[len(self.incident_history)%4]
        road_event,road_key=(self.construction_event() if kind=='construction' else (None,None))
        if kind=='construction' and road_event is None:
            kind='urgent'
        self.seal_stage()
        self.begin_stage()
        self.pause=0;self.pending_finish=False;self.pose='idle';self.say_until=0
        self.state='incident';self.modal='incident';self.incident_history.append(kind)
        self.reset_order_history()
        self.pose={'construction':'scratch','urgent':'panic','hungry':'hungry','chase':'panic'}[kind]
        self.incident={'kind':kind,'slot':0,'at':self.current_node}
        if kind!='construction':
            labels={'urgent':('突然加急 · 安排新订单','两站内送达可获得独立加急徽章。'),
                    'hungry':('奶龙饿了 · 先去补给','食堂还是小卖部？考虑后面的配送路线。'),
                    'chase':('捣蛋奶龙 · 找回餐袋','跟着小脚印点中奶龙三次，获得追逐徽章。')}
            title,description=labels[kind]
            self.event=Event(title,description,set(self.event.blocked),dict(self.event.slow))
            self.network=Network(self.event)
        if kind=='construction':
            self.event=road_event;self.network=Network(road_event)
            self.incident['road']=road_key
        elif kind=='urgent':
            unused=[p.id for p in PLACES if p.id not in self.selected and p.id!=START]
            target=self.rng.choice(unused or self.selected[self.leg_index:])
            self.incident['target']=target
            self.incident['existing']=target in self.selected
        elif kind=='chase':
            candidates=[p.id for p in PLACES if p.id!=self.current_node]
            self.chase_points=self.rng.sample(candidates,3)
            self.chase_step=0;self.chase_remaining=12.0;self.chase_rect=None
        self.audio.play('event')
        return True

    def maybe_incident(self):
        if self.next_incident>=len(self.incident_schedule):
            return False
        if self.leg_index<self.incident_schedule[self.next_incident] or self.leg_index>=len(self.selected):
            return False
        self.next_incident+=1
        return self.trigger_incident()

    def replan_incident(self):
        self.pending_required=set(self.selected[self.leg_index:])
        self.begin_stage();self.state='replanning';self.modal=None;self.incident=None
        self.pose='scratch';self.reset_order_history()
        self.order_scroll=max(0,self.leg_index*46-46)
        self.message('拖动右侧剩余订单调整顺序，支持撤销；排好后点击「继续配送」。')
        self.refresh_estimate()

    def continue_delivery(self,supply_options=(),begin=True):
        if begin:
            self.begin_stage(supply_options)
        self.state='delivering';self.modal=None;self.incident=None
        self.reset_order_history()
        self.pose='accept';self.reaction_at=self.anim_time;self.pause=.55
        self.say='重新安排好啦，继续送！';self.say_until=self.anim_time+1.7
        self.refresh_estimate();self.prepare_leg();self.audio.play('start')

    def resume_replan(self):
        tail=self.selected[self.leg_index:]
        if set(tail)!=self.pending_required or len(tail)!=len(self.pending_required):
            self.message('还有剩余订单未安排，请全部排好后继续。');return
        self.continue_delivery(begin=False)

    def urgent_tail(self):
        target=self.incident['target']
        tail=[id for id in self.selected[self.leg_index:] if id!=target]
        slot=min(self.incident['slot'],len(tail));tail.insert(slot,target)
        return tail

    def move_urgent_slot(self,delta):
        length=len([id for id in self.selected[self.leg_index:] if id!=self.incident['target']])
        self.incident['slot']=max(0,min(length,self.incident['slot']+delta))

    def accept_urgent(self):
        target=self.incident['target']
        self.selected=self.selected[:self.leg_index]+self.urgent_tail()
        if target not in self.orders:
            self.orders.append(target)
        self.urgent_target=target;self.urgent_deadline=self.leg_index+2
        self.continue_delivery()
        self.pose='panic';self.say='加急单！奶龙会努力的！';self.say_until=self.anim_time+2

    def choose_supply(self,site):
        self.supply_pending=site
        self.continue_delivery(('food','shop'))
        self.pose='hungry'
        self.say='肚子有点饿，先补充能量！';self.say_until=self.anim_time+2

    def start_chase(self):
        self.state='chasing';self.modal=None;self.chase_remaining=12.0
        self.message('跟着小脚印找奶龙，12 秒内点中它 3 次，拿回餐袋！')

    def finish_chase(self,success):
        if self.state!='chasing':
            return
        if success:
            self.event_badges+=1;self.audio.play('badge')
        self.chase_rect=None;self.continue_delivery()
        if success:self.pose='proud';self.pause=1.5
        self.say='拿回餐袋啦！徽章 +1' if success else '奶龙玩累了，自己把餐袋还回来啦！'
        self.say_until=self.anim_time+3
        self.message(self.say+'；路线评分不受追逐结果影响。')

    def click_chase(self,pos):
        if self.state!='chasing' or self.modal or not self.chase_rect or not self.chase_rect.collidepoint(pos):
            return False
        self.chase_step+=1;self.audio.play('select');self.chase_rect=None
        if self.chase_step>=3:
            self.finish_chase(True)
        return True

    def draw_incident_map(self):
        c=self.canvas;bounds=self.map_bounds
        blocked=self.stages[self.replay['stage']]['blocked'] if self.replay else self.event.blocked
        for a,b in blocked:
            point=self.map_point(tuple((NODES[a][i]+NODES[b][i])/2 for i in (0,1)))
            incident_icon(c,'construction',point,44,self.anim_time)
        if self.replay:return
        if self.urgent_target and self.urgent_target not in self.delivered:
            pos=self.map_point(NODES[self.urgent_target])
            incident_icon(c,'urgent',(pos[0]+23,pos[1]-25),42,self.anim_time)
        if self.incident and self.incident['kind']=='urgent':
            pos=self.map_point(NODES[self.incident['target']])
            incident_icon(c,'urgent',(pos[0]+20,pos[1]-24),48,self.anim_time)
        if self.supply_pending:
            pos=self.map_point(NODES[self.supply_pending])
            incident_icon(c,'hungry',(pos[0]+24,pos[1]-25),43,self.anim_time)
        if self.state=='chasing':
            point=self.chase_points[self.chase_step]
            pos=self.map_point(NODES[point]);x=max(bounds.left+65,min(bounds.right-65,pos[0]));y=max(bounds.top+128,min(bounds.bottom-20,pos[1]))
            old=self.map_point(NODES[self.current_node if self.chase_step==0 else self.chase_points[self.chase_step-1]])
            for step in range(1,6):
                t=step/6;px=old[0]+(x-old[0])*t;py=old[1]+(y-old[1])*t
                pygame.draw.ellipse(c,'#9c9f73',(px-4,py-2+(step%2)*7,9,5))
            self.chase_rect=self.mascots.draw(c,'wink',(x,y),91,delivery=True,phase=self.anim_time,pose='peek',age=1).inflate(12,10).clip(bounds)
            speech(c,f'来追我呀！ {self.chase_step}/3',(x,y-116),bounds)
            banner=pygame.Rect(bounds.centerx-230,bounds.top+11,460,40)
            rounded(c,banner,'#fff6da',10,'#e8bf7a')
            text(c,f'找回餐袋：点中奶龙 3 次  ·  剩余 {math.ceil(self.chase_remaining)} 秒',banner.center,16,INK,True,True)
        else:
            self.chase_rect=None

    def draw_incident_modal(self):
        data=self.incident;kind=data['kind'];c=self.canvas
        titles={'construction':'前方施工，奶龙挠头！','urgent':'叮！突然来了一份加急单','hungry':'咕噜……奶龙肚子饿了','chase':'不好！餐袋被捣蛋奶龙抱走了'}
        incident_icon(c,kind,(659,237),115,self.anim_time)
        emotion={'construction':'scratch','urgent':'panic','hungry':'hungry','chase':'panic'}[kind]
        self.mascots.draw(c,'normal',(827,305),131,delivery=True,phase=self.anim_time,pose=emotion)
        text(c,titles[kind],(740,342),27,INK,True,True)
        text(c,'配送已暂停 · 做好选择再出发',(740,384),14,MUTED,center=True)
        if kind=='construction':
            wrap(c,'原路线上的一段道路临时封闭了！地图上会出现锥桶、路障和闪烁警示灯。接下来请重新安排剩余订单，找一条顺畅的绕行路线。',(442,427),592,18,INK,10)
            wrap(c,'已送达的订单保留。剩余路线从奶龙当前位置重新评分，不会把之前走过的道路追溯为违规。',(442,570),592,15,MUTED,9)
            self.button('incident-replan','查看路障，重新规划剩余订单',(441,756,594,59),self.replan_incident,primary=True)
        elif kind=='urgent':
            target=data['target'];tail=self.urgent_tail();position=data['slot']+1
            text(c,BY_ID[target].name+' · '+('已有订单升级加急' if data['existing'] else '新增一份热乎外卖'),(740,437),22,GREEN,True,True)
            text(c,'两站内送达可获加急徽章，徽章与路线评分分开计算。',(442,482),16,MUTED)
            text(c,'把它插到接下来的第几站？',(442,531),18,INK,True)
            self.button('slot-minus','−',(781,518,52,44),lambda:self.move_urgent_slot(-1),size=23)
            text(c,position,(878,540),26,GREEN,True,True)
            self.button('slot-plus','+',(926,518,52,44),lambda:self.move_urgent_slot(1),size=23)
            next_cost=self.network.route(tail,self.current_node)[0]
            text(c,f'这样安排，剩余通行成本约 {next_cost:.0f} 单位',(442,588),17,INK)
            preview=' → '.join(BY_ID[id].name for id in tail[:5])+(' …' if len(tail)>5 else '')
            wrap(c,preview,(442,632),590,15,MUTED)
            self.button('incident-urgent','就这样安排，继续送餐！',(441,756,594,59),self.accept_urgent,primary=True)
        elif kind=='hungry':
            wrap(c,'奶龙需要先吃点东西，才有力气继续送餐。选择一个补给点，补给后再配送剩余外卖。近的店不一定让整趟路线更短哦！',(442,428),591,18,INK,10)
            for site,x in [('food',441),('shop',748)]:
                cost=self.network.shortest(self.current_node,site)[0]
                rounded(c,(x,559,287,160),'#f2f0dc',13,'#e0d9b8')
                incident_icon(c,'hungry',(x+143,599),54,self.anim_time)
                text(c,f'到{BY_ID[site].name}约 {cost:.0f} 单位',(x+143,652),17,INK,True,True)
                self.button('supply-'+site,'去'+BY_ID[site].name+'补给',(x+15,756,257,59),lambda site=site:self.choose_supply(site),primary=True)
            text(c,'参考方案会比较食堂、小卖部两种选择的后续总成本。',(442,730),14,MUTED)
        else:
            wrap(c,'捣蛋奶龙抱着餐袋跑到校园里了！进入地图后，跟着小脚印找到它，12 秒内点中 3 次就能拿回外卖，并获得一枚追逐徽章。',(442,432),592,18,INK,10)
            wrap(c,'配送和路线计费都会暂停。没追上也能继续游戏，奶龙会自己归还餐袋；追逐结果只影响独立徽章。',(442,581),592,15,MUTED,9)
            self.button('incident-chase','去地图找奶龙！',(441,756,594,59),self.start_chase,primary=True)
