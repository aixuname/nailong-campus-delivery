"""Integration checks of actual incident choices, resume flow and scoring."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
if (ROOT/'vendor').exists():
    sys.path.insert(0,str(ROOT/'vendor'))
os.environ['SDL_AUDIODRIVER']='dummy';os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['TEMP']=str(ROOT/'data'/'temp');os.environ['TMP']=os.environ['TEMP']
import itertools
import math
import pygame
from main import Game
from engine import edge_key
from world import PLACES, START, NODES
from visuals import rounded,text,incident_icon,PAPER,INK,MUTED,GREEN

QA=ROOT/'qa';QA.mkdir(exist_ok=True)

def press(game,key):
    game.draw()
    button=next(rect for name,rect,callback in game.buttons if name==key)
    game.click(button.center)

def advance(game,wanted):
    for _ in range(3000):
        if game.state in wanted:
            return
        game.update(.2)
    raise AssertionError(f'Never reached {wanted}: {game.state}')

def fixture(game,kind):
    game.event_enabled=True;game.new_round(4)
    game.orders=['dorm9','south','library','admin'];game.selected=list(game.orders)
    game.incident_kinds=[kind]+[k for k in ['construction','urgent','hungry','chase'] if k!=kind]
    game.start();game.incident_schedule=[1]
    advance(game,{'incident'})
    assert game.incident['kind']==kind
    before=game.rider;completed=set(game.delivered)
    game.update(20)
    assert game.rider==before and game.delivered==completed, 'Incident cards must pause delivery'
    game.close_modal();assert game.modal=='incident', 'An incident cannot be dismissed without a choice'
    game.draw();pygame.image.save(game.canvas,str(QA/f'incident-{kind}.png'))

def check_end(game):
    advance(game,{'complete'})
    assert set(game.selected)==game.delivered
    assert math.isclose(game.cost,game.finished_cost,rel_tol=1e-9), 'Actual travelled legs must match the recorded cost'
    assert math.isclose(game.cost,sum(s['cost'] for s in game.stages),rel_tol=1e-9)
    assert game.best_cost<=game.cost+1e-7 and 0<game.score<=100
    game.draw()

def run():
    game=Game(headless=True,seed=113);game.score_file=QA/'incident-records.json';game.records={}
    for kind in ['construction','urgent','hungry','chase']:
        fixture(game,kind)
        if kind=='construction':
            assert game.event.blocked
            for p in PLACES:game.network.shortest(game.current_node,p.id)
            prefix=set(game.delivered);press(game,'incident-replan')
            assert game.state=='replanning'
            press(game,'clear');game.resume_replan();assert game.state=='replanning'
            assert set(game.selected)==prefix, 'Clearing remaining orders must preserve already delivered stops'
            for id in reversed(game.orders):
                if id not in prefix:game.toggle_place(id)
            press(game,'start');assert game.state=='delivering'
            current=game.current_node;remaining=game.selected[game.leg_index:]
            expected=min(game.network.route(p,current)[0] for p in itertools.permutations(remaining))
            check_end(game)
            assert math.isclose(game.stages[-1]['best_cost'],expected)
            for a,b in zip(game.stages[-1]['path'],game.stages[-1]['path'][1:]):
                assert edge_key(a,b) not in game.event.blocked
        elif kind=='urgent':
            count=len(game.selected);target=game.incident['target']
            press(game,'slot-plus');assert game.incident['slot']==1
            chosen=game.urgent_tail();press(game,'incident-urgent')
            assert game.selected[game.leg_index:]==chosen
            assert len(game.selected)==count+1 and target in game.orders
            assert game.selected[game.leg_index+1]==target
            check_end(game);assert game.event_badges==1
        elif kind=='hungry':
            current=game.current_node;remaining=game.selected[game.leg_index:]
            reference=min(game.network.shortest(current,site)[0]+min(game.network.route(p,site)[0] for p in itertools.permutations(remaining)) for site in ['food','shop'])
            press(game,'supply-food');assert game.supply_pending=='food'
            check_end(game)
            assert game.stages[-1]['visits'][0]=='food'
            assert math.isclose(game.stages[-1]['best_cost'],reference)
            assert len(game.delivered)==4, 'A supply visit must not falsely complete an order'
        else:
            press(game,'incident-chase');before=game.rider
            game.update(2);assert game.rider==before and game.chase_remaining==10
            game.draw();pygame.image.save(game.canvas,str(QA/'incident-chase-map.png'))
            for _ in range(3):
                game.draw();game.click(game.chase_rect.center)
            assert game.state=='delivering' and game.event_badges==1
            check_end(game)
    # A missed chase must always return the bag and remain playable.
    fixture(game,'chase');press(game,'incident-chase');game.update(13)
    assert game.state=='delivering' and game.event_badges==0
    check_end(game)
    # Both supply choices, an already selected urgent destination, and replanning
    # must also work with all 29 map places in the original order.
    for case in ('shop','existing-urgent'):
        game.new_round(0);game.selected=[p.id for p in PLACES]
        game.incident_kinds=['hungry' if case=='shop' else 'urgent','chase','construction','hungry']
        game.start();game.incident_schedule=[1];advance(game,{'incident'})
        if case=='shop':press(game,'supply-shop')
        else:
            assert game.incident['existing'];press(game,'incident-urgent');assert len(game.selected)==29
        check_end(game)
    # Random rounds can contain at most two incidents and must all terminate.
    for i in range(16):
        game.new_round(4);game.selected=list(game.orders);game.start()
        for _ in range(1000):
            game.update(2)
            if game.state=='incident':
                kind=game.incident['kind']
                if kind=='construction':game.replan_incident();game.resume_replan()
                elif kind=='urgent':game.accept_urgent()
                elif kind=='hungry':game.choose_supply('shop')
                else:game.start_chase();game.finish_chase(False)
            if game.state=='complete':break
        assert game.state=='complete' and 1<=len(game.incident_history)<=2
        assert math.isclose(game.cost,game.finished_cost,rel_tol=1e-9)
    # A compact gallery uses the same pictograms as the actual event cards.
    gallery=pygame.Surface((1060,648));gallery.fill(PAPER)
    text(gallery,'配送途中，会发生什么？',(28,21),29,INK,True)
    items=[('construction','前方施工','看路障，重新安排剩余订单'),('urgent','突然加急','把新订单插进合适的位置'),('hungry','奶龙饿了','选择食堂或小卖部补充能量'),('chase','奶龙捣蛋','跟着脚印找回餐袋，拿徽章')]
    for i,(kind,title,caption) in enumerate(items):
        x=22+(i%2)*519;y=83+(i//2)*276
        rounded(gallery,(x,y,497,258),'#e9efdf',15,'#d7dfca')
        incident_icon(gallery,kind,(x+99,y+119),160,.4)
        text(gallery,title,(x+201,y+72),26,GREEN,True)
        text(gallery,caption,(x+201,y+124),17,INK)
        text(gallery,'有图案 · 有选择 · 配送暂停',(x+201,y+166),14,MUTED)
    pygame.image.save(gallery,str(QA/'incidents-gallery.png'))
    pygame.quit()
    print('PASS: all four interactive event cards, pause/resume, remaining-order replan, insertion, both supplies, chase success/timeout, existing urgent stops, fair segment scores, and 16 random rounds.')

if __name__=='__main__':
    run()
