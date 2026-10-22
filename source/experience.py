"""Drag/undo route editing and an explanatory, read-only route replay."""
from collections import Counter
import math
import pygame
from world import BY_ID, NODES
from visuals import text, wrap, rounded, speech, INK, MUTED, GREEN, ORANGE

ORDER_VIEW=pygame.Rect(1105,407,329,280)

class ExperienceMixin:
    def init_experience(self):
        self.order_history=[];self.order_rows=[];self.order_drag=None
        self.replay=None

    def remember_order(self):
        snapshot=tuple(self.selected)
        if not self.order_history or self.order_history[-1]!=snapshot:
            self.order_history.append(snapshot)
            self.order_history=self.order_history[-40:]

    def reset_order_history(self):
        self.order_history=[];self.order_drag=None

    def undo_order(self):
        if self.modal or self.state not in ('planning','replanning') or not self.order_history:
            return
        self.selected=list(self.order_history.pop());self.order_drag=None
        if self.state=='replanning':self.refresh_estimate()
        self.message('已撤销上一步安排。');self.audio.play('tap')

    def reorder_order(self,id,index):
        if self.state not in ('planning','replanning') or id not in self.selected:
            return
        first=self.leg_index if self.state=='replanning' else 0
        old=self.selected.index(id)
        if old<first:return
        index=max(first,min(len(self.selected)-1,index))
        if old==index:return
        self.remember_order();self.selected.pop(old);self.selected.insert(index,id)
        if self.state=='replanning':self.refresh_estimate()
        self.audio.play('tap');self.message('配送顺序已调整，点「撤销」可退回上一步。')

    def order_down(self,pos):
        if self.modal or self.replay or self.state not in ('planning','replanning'):
            return False
        for id,rect in self.order_rows:
            if rect.collidepoint(pos):
                self.order_drag={'id':id,'start':pos,'pos':pos,'rect':rect.copy(),'moving':False}
                return True
        return False

    def order_motion(self,pos):
        drag=self.order_drag
        if not drag:return
        drag['pos']=pos
        if math.dist(pos,drag['start'])>6 and drag['id'] in self.selected:
            drag['moving']=True

    def order_up(self,pos):
        drag=self.order_drag;self.order_drag=None
        if not drag:return False
        if self.modal or self.state not in ('planning','replanning'):return True
        if drag['moving']:
            if ORDER_VIEW.inflate(16,16).collidepoint(pos):
                index=int((pos[1]-411+self.order_scroll)//46)
                self.reorder_order(drag['id'],index)
        elif drag['rect'].collidepoint(pos):
            self.toggle_place(drag['id'])
        return True

    def update_drag(self,dt):
        drag=self.order_drag
        if not drag or not drag['moving']:return
        x,y=drag['pos']
        if ORDER_VIEW.left-15<x<ORDER_VIEW.right+15:
            if y<ORDER_VIEW.top+30:self.order_scroll=max(0,self.order_scroll-dt*220)
            elif y>ORDER_VIEW.bottom-30:self.order_scroll+=dt*220

    def draw_drag(self):
        drag=self.order_drag
        if not drag or not drag['moving'] or self.modal:return
        first=self.leg_index if self.state=='replanning' else 0
        index=max(first,min(len(self.selected)-1,int((drag['pos'][1]-411+self.order_scroll)//46)))
        y=max(ORDER_VIEW.top+2,min(ORDER_VIEW.bottom-2,411+index*46-self.order_scroll))
        pygame.draw.line(self.canvas,ORANGE,(1112,y),(1424,y),4)
        ghost=pygame.Rect(0,0,282,44);ghost.center=drag['pos'];ghost.clamp_ip(self.canvas.get_rect())
        rounded(self.canvas,ghost,'#fff2cf',9,'#e4ad63',2)
        text(self.canvas,BY_ID[drag['id']].name,(ghost.x+13,ghost.y+11),16,INK,True)
        text(self.canvas,'松手放这里',(ghost.right-93,ghost.y+14),12,'#ad7136')

    def replay_stage(self,offset=0):
        if not self.stages:return
        old=self.replay['stage'] if self.replay else 0
        index=max(0,min(len(self.stages)-1,old+offset))
        stage=self.stages[index]
        counts=Counter(tuple(sorted(edge)) for edge in zip(stage['path'],stage['path'][1:]))
        reference=Counter(tuple(sorted(edge)) for edge in zip(stage['best_path'],stage['best_path'][1:]))
        extra=counts-reference
        highlights=sorted(extra,key=lambda e:extra[e]*stage['edge_costs'].get(e,math.dist(NODES[e[0]],NODES[e[1]])),reverse=True)[:3]
        self.replay={'stage':index,'progress':0.0,'playing':True,'speed':1,
                     'duration':max(5,min(14,max(stage['cost'],stage['best_cost'])/320)),
                     'highlights':highlights}
        self.modal=None;self.order_drag=None

    def open_replay(self):
        if self.state=='complete' and self.stages:
            self.replay=None;self.replay_stage()

    def close_replay(self):
        self.replay=None;self.modal='result'

    def toggle_replay(self):
        if self.replay:
            if self.replay['progress']>=1:self.replay['progress']=0
            self.replay['playing']=not self.replay['playing']

    def speed_replay(self):
        if self.replay:self.replay['speed']=3-self.replay['speed']

    def update_replay(self,dt):
        if self.replay and self.replay['playing'] and not self.modal:
            self.replay['progress']=min(1,self.replay['progress']+dt*self.replay['speed']/self.replay['duration'])
            if self.replay['progress']>=1:self.replay['playing']=False

    @staticmethod
    def replay_point(stage,path,cost):
        if not path:return (0,0)
        for a,b in zip(path,path[1:]):
            length=stage['edge_costs'][tuple(sorted((a,b)))]
            if cost<=length:
                t=cost/length if length else 1
                return tuple(NODES[a][i]+(NODES[b][i]-NODES[a][i])*t for i in (0,1))
            cost-=length
        return NODES[path[-1]]

    def draw_replay_map(self):
        replay=self.replay;stage=self.stages[replay['stage']]
        self.line(stage['best_path'],'#398461',6,True)
        self.line(stage['path'],ORANGE,4)
        for edge in replay['highlights']:
            self.line(edge,'#d45f36',10)
        distance=replay['progress']*max(stage['cost'],stage['best_cost'])
        for path,key,label,color,dx in [(stage['path'],'normal','你的路线',ORANGE,-12),(stage['best_path'],'wink','参考路线',GREEN,12)]:
            point=self.map_point(self.replay_point(stage,path,distance))
            center=(point[0]+dx,point[1]-8)
            moving=replay['playing'] and distance<(stage['cost'] if key=='normal' else stage['best_cost'])
            pygame.draw.ellipse(self.canvas,color,(center[0]-22,center[1]-4,44,10),2)
            self.mascots.draw(self.canvas,key,center,68,delivery=True,phase=self.anim_time,pose='move' if moving else 'idle')
            rect=pygame.Rect(0,0,76,23);rect.midtop=(center[0],center[1]+9);rect.clamp_ip(self.map_bounds)
            rounded(self.canvas,rect,color,5);text(self.canvas,label,rect.center,11,'#fffdf1',True,True)
        title=pygame.Rect(self.map_bounds.x+16,self.map_bounds.y+11,360,33)
        rounded(self.canvas,title,'#fff9df',9,'#d8dcb8')
        text(self.canvas,f"路线回放 · 第 {replay['stage']+1} / {len(self.stages)} 段",title.center,15,INK,True,True)

    def draw_replay_panel(self):
        c=self.canvas;replay=self.replay;stage=self.stages[replay['stage']]
        rounded(c,(1084,109,372,810),'#fffdf6',14,'#dce2d2')
        text(c,'ROUTE REPLAY',(1105,132),11,MUTED,True)
        text(c,'看看哪里绕了路',(1105,159),26,GREEN,True)
        text(c,f"第 {replay['stage']+1} 段 · 从{BY_ID[stage['start']].name}出发",(1105,207),15,MUTED)
        for x,label,value,color in [(1105,'你的成本',stage['cost'],ORANGE),(1276,'参考成本',stage['best_cost'],GREEN)]:
            rounded(c,(x,246,157,96),'#f0f3e7',10)
            text(c,label,(x+13,259),13,MUTED);text(c,f'{value:.0f}',(x+13,286),29,color,True)
        extra=max(0,stage['cost']-stage['best_cost'])
        if extra<.01:
            insight='这一段已经达到参考路线，安排得很顺！'
        elif stage.get('supply_options') and stage['visits'][0]!=stage['best_order'][0]:
            insight=f"参考方案先去{BY_ID[stage['best_order'][0]].name}补给，再安排后面的订单，合计少走 {extra:.0f} 单位。"
        else:
            differing=next(((a,b,i) for i,(a,b) in enumerate(zip(stage['visits'],stage['best_order'])) if a!=b),None)
            insight=f'这一段比参考方案多走 {extra:.0f} 单位。'
            if differing:
                a,b,i=differing
                insight+=f"你第 {i+1} 站先去{BY_ID[a].name}，参考方案先去{BY_ID[b].name}。"
        wrap(c,insight,(1105,365),327,18,INK,9)
        wrap(c,'橙色实线：你的路线\n绿色虚线：参考路线\n橙色加粗：你的路线额外经过的路段',(1105,490),327,13,MUTED,8)
        self.button('replay-prev','← 上一段',(1105,585,157,40),lambda:self.replay_stage(-1),enabled=replay['stage']>0,size=14)
        self.button('replay-next','下一段 →',(1277,585,157,40),lambda:self.replay_stage(1),enabled=replay['stage']<len(self.stages)-1,size=14)
        self.button('replay-play','暂停' if replay['playing'] else '播放',(1105,641,208,43),self.toggle_replay,primary=True)
        self.button('replay-speed',f"{replay['speed']} 倍速",(1325,641,109,43),self.speed_replay,size=14)
        rounded(c,(1105,708,329,9),'#e4e8d8',4)
        if replay['progress']>0:rounded(c,(1105,708,max(8,329*replay['progress']),9),ORANGE,4)
        text(c,f"本段回放 {round(replay['progress']*100)}%",(1105,731),13,MUTED)
        if not stage['exact']:text(c,'参考方案使用启发式，不保证全局最优。',(1105,760),12,MUTED)
        self.button('replay-exit','返回结算',(1105,794,329,45),self.close_replay,primary=True)
        self.button('replay-restart','再看这一段',(1105,854,329,37),lambda:self.replay_stage(),size=13)
