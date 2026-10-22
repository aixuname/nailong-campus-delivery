"""Run a bundled executable's smoke check without requiring source or Python."""
import json
from pathlib import Path
import sys
import pygame
from app_paths import APP_DIR, RESOURCE_DIR, ASSET_DIR
from world import PLACES

def run(game):
    report={'frozen':bool(getattr(sys,'frozen',False)),'executable':sys.executable,
            'app_dir':str(APP_DIR),'resources':str(RESOURCE_DIR),'places':len(PLACES)}
    output=APP_DIR/'data'/'desktop-check.json'
    try:
        assert len(PLACES)==29
        assert game.mascots.images.keys()>={'normal','wink'}
        assert game.audio.available and len(game.audio.sounds)==7
        assert pygame.mixer.music.get_busy()
        game.score_file=APP_DIR/'data'/'desktop-check-scores.json';game.records={}
        game.event_enabled=False;game.new_round(4);game.selected=list(game.orders)
        original=list(game.selected);game.reorder_order(original[0],3);game.undo_order()
        assert game.selected==original
        game.start();game.update(1000)
        assert game.state=='complete' and 0<game.score<=100
        original_cost=game.cost;game.open_replay();game.update(.5);game.draw()
        assert game.replay and game.cost==original_cost
        game.close_replay()
        game.draw()
        checks=[]
        for kind in ['construction','urgent','hungry','chase']:
            game.event_enabled=True;game.new_round(4)
            game.orders=['dorm9','south','library','admin'];game.selected=list(game.orders)
            game.incident_kinds=[kind]+[name for name in ['construction','urgent','hungry','chase'] if name!=kind]
            game.start();game.incident_schedule=[1]
            for _ in range(1000):
                game.update(.2)
                if game.state=='incident':break
            assert game.state=='incident' and game.incident['kind']==kind
            game.draw()
            if kind=='construction':game.replan_incident();game.resume_replan()
            elif kind=='urgent':game.accept_urgent()
            elif kind=='hungry':game.choose_supply('shop')
            else:
                game.start_chase()
                for _ in range(3):
                    game.draw();game.click(game.chase_rect.center)
            for _ in range(1000):
                game.update(.3)
                if game.state=='complete':break
            assert game.state=='complete'
            assert abs(game.cost-game.finished_cost)<1e-6
            checks.append(kind)
        game.draw();pygame.image.save(game.canvas,str(APP_DIR/'data'/'desktop-check.png'))
        report.update(status='passed',audio=True,events=checks,score=game.score,
                      features=['drag_undo','route_replay','spaced_incidents','event_emotions'],
                      asset_dir=str(ASSET_DIR),data_dir=str(APP_DIR/'data'))
    except Exception as error:
        report.update(status='failed',error=repr(error))
    finally:
        pygame.quit()
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if report['status']=='passed' else 1
