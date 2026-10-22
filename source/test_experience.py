"""Exercise drag gestures, undo boundaries, pacing and read-only replay."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
if (ROOT/'vendor').exists():sys.path.insert(0,str(ROOT/'vendor'))
os.environ['SDL_AUDIODRIVER']='dummy';os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['TEMP']=str(ROOT/'data'/'temp');os.environ['TMP']=os.environ['TEMP']
import copy
import pygame
from main import Game
from world import PLACES,NODES,START
from visuals import rounded,text,PAPER,GREEN
from test_incidents import fixture,advance

def physical(game,pos):
    return tuple(round(pos[i]*game.screen_scale+game.screen_offset[i]) for i in (0,1))

def gesture(game,start,end):
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=physical(game,start)))
    game.handle(pygame.event.Event(pygame.MOUSEMOTION,pos=physical(game,end),rel=(0,0),buttons=(1,0,0)))
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=physical(game,end)))

def run():
    qa=ROOT/'qa';qa.mkdir(exist_ok=True)
    g=Game(headless=True,seed=701);g.score_file=qa/'experience-records.json';g.records={}
    g.event_enabled=False;g.new_round(4)
    for id in g.orders:g.toggle_place(id)
    before=list(g.selected)
    g.screen=pygame.display.set_mode((1000,650),pygame.HIDDEN);g.draw()
    start=g.order_rows[0][1].center;end=g.order_rows[3][1].center
    gesture(g,start,end)
    assert g.selected==before[1:]+before[:1], 'Scaled-window drag must reorder without removing a stop'
    g.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_z,mod=pygame.KMOD_CTRL))
    assert g.selected==before
    g.draw();gesture(g,g.order_rows[0][1].center,(500,500));assert g.selected==before
    g.clear();assert g.selected==[];g.undo_order();assert g.selected==before
    # A click still toggles an unselected item; moving less than threshold does not drag.
    g.clear();g.draw();p=g.order_rows[0][1].center
    gesture(g,p,(p[0]+2,p[1]+2));assert len(g.selected)==1
    # Drag from the top to the bottom of a long list using edge auto-scroll.
    g.new_round(0);g.selected=[p.id for p in PLACES];g.reset_order_history();g.draw()
    first=g.selected[0];p=g.order_rows[0][1].center
    g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=physical(g,p)))
    end=(1260,682)
    g.handle(pygame.event.Event(pygame.MOUSEMOTION,pos=physical(g,end),rel=(0,0),buttons=(1,0,0)))
    g.update(7);g.draw()
    pygame.image.save(g.canvas,str(qa/'drag-orders.png'))
    g.handle(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=physical(g,end)))
    assert g.selected[-1]==first and len(set(g.selected))==29
    g.undo_order();assert g.selected[0]==first
    # Completed stops are locked and undo history cannot cross the event boundary.
    fixture(g,'construction');prefix=list(g.selected[:g.leg_index]);g.replan_incident()
    assert not g.order_history
    original=list(g.selected);g.reorder_order(prefix[0],3);assert g.selected==original
    g.reorder_order(g.selected[-1],g.leg_index);assert g.selected[:g.leg_index]==prefix
    g.undo_order();assert g.selected==original
    g.resume_replan();assert not g.order_history
    advance(g,{'complete'})
    assert not g.stages[0]['blocked'] and g.stages[-1]['blocked'], 'Replay must preserve the road state of each stage'
    # Pacing is deterministic by task count, with at least two stops before an event.
    for count,expected in [(1,[]),(2,[]),(3,[2]),(4,[2]),(5,[2]),(6,[2,4]),(8,[2,5]),(29,[2,19])]:
        g.event_enabled=True;g.new_round(0);g.selected=[p.id for p in PLACES][:count]
        g.schedule_incidents();assert g.incident_schedule==expected
    # Replay must show two routes and have no effect on cost, badges or records.
    g.event_enabled=False;g.new_round(0);g.selected=['south','dorm9','admin','library']
    g.start();g.update(1000);assert g.state=='complete'
    snapshot=(g.cost,g.best_cost,g.score,copy.deepcopy(g.records),list(g.selected),g.finished_cost)
    score_bytes=g.score_file.read_bytes()
    g.open_replay();assert g.replay and g.modal is None and g.replay['highlights']
    g.update(1);g.draw();pygame.image.save(g.canvas,str(qa/'route-replay.png'))
    progress=g.replay['progress'];g.toggle_replay();g.update(2);assert g.replay['progress']==progress
    g.toggle_replay();g.speed_replay();g.update(100);assert g.replay['progress']==1 and not g.replay['playing']
    for stage in g.stages:
        assert g.replay_point(stage,stage['path'],stage['cost']+1)==NODES[stage['path'][-1]]
        assert g.replay_point(stage,stage['best_path'],stage['best_cost']+1)==NODES[stage['best_path'][-1]]
    g.close_replay();assert g.modal=='result'
    assert snapshot==(g.cost,g.best_cost,g.score,g.records,g.selected,g.finished_cost)
    assert g.score_file.read_bytes()==score_bytes
    # Both a zero-cost round and multi-stage replay remain playable.
    g.new_round(0);g.selected=[START];g.start();g.update(1000);g.open_replay();g.update(6);g.draw()
    assert g.replay['progress']==1
    fixture(g,'hungry');g.choose_supply('shop');advance(g,{'complete'})
    g.open_replay();g.replay_stage(1);assert g.replay['stage']==1;g.replay_stage(-1);assert g.replay['stage']==0
    # Event cards render the corresponding character pose, not only their pictogram.
    for kind,pose in [('construction','scratch'),('urgent','panic'),('hungry','hungry'),('chase','panic')]:
        fixture(g,kind);assert g.pose==pose;g.draw()
        pygame.image.save(g.canvas,str(qa/f'emotion-{kind}.png'))
    g.start_chase();g.finish_chase(True);assert g.pose=='proud' and g.pause>=1
    gallery=pygame.Surface((960,354));gallery.fill(PAPER)
    text(gallery,'奶龙遇到突发事件的反应',(25,18),27,GREEN,True)
    for i,(pose,label) in enumerate([('scratch','施工：挠头想办法'),('panic','加急：紧张冒汗'),('hungry','饿了：捂住肚子'),('proud','追回：得意庆祝')]):
        x=15+i*237;rounded(gallery,(x,74,222,264),'#e8efdc',14)
        g.mascots.draw(gallery,'normal',(x+111,267),135,phase=.65,pose=pose)
        text(gallery,label,(x+111,311),17,GREEN,True,True)
    pygame.image.save(gallery,str(qa/'event-emotions.png'))
    pygame.quit()
    print('PASS: scaled-window mouse drag, undo/clear, long-list scroll, completed-stop locking, incident pacing, replay costs/controls/immutability/zero-cost/multiple stages, and contextual mascot emotions.')

if __name__=='__main__':run()
