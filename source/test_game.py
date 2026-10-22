import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
if (ROOT/'vendor').exists():
    sys.path.insert(0,str(ROOT/'vendor'))
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['TEMP']=str(ROOT/'data'/'temp')
os.environ['TMP']=os.environ['TEMP']
import itertools
import random
import unittest
from world import PLACES, NODES, EDGES, START
from engine import Network, Event, random_event, edge_key

class AlgorithmChecks(unittest.TestCase):
    def test_all_29_places_are_unique_and_reachable(self):
        self.assertEqual(len(PLACES),29)
        self.assertEqual(len(set(p.id for p in PLACES)),29)
        network=Network()
        for p in PLACES:
            cost,path=network.shortest(START,p.id)
            self.assertGreaterEqual(cost,0)
            self.assertEqual(path[0],START)
            self.assertEqual(path[-1],p.id)

    def test_all_events_preserve_connectivity_and_closed_roads_are_never_used(self):
        kinds=set()
        for seed in range(100):
            event=random_event(random.Random(seed));network=Network(event);kinds.add(event.title)
            for place in PLACES:
                cost,path=network.shortest(START,place.id)
                self.assertTrue(all(edge_key(a,b) not in event.blocked for a,b in zip(path,path[1:])))
        self.assertEqual(len(kinds),4)

    def test_exact_solution_matches_exhaustive_permutations_with_event(self):
        ids=['dorm9','dorm2','library','south','gym','admin']
        network=Network(random_event(random.Random(13)))
        expected=min(network.route(order)[0] for order in itertools.permutations(ids))
        cost,order,exact=network.optimize(ids)
        self.assertTrue(exact)
        self.assertAlmostEqual(cost,expected)
        self.assertCountEqual(order,ids)

    def test_large_route_is_labeled_approximate_and_never_worse_than_input(self):
        ids=[p.id for p in PLACES];network=Network(random_event(random.Random(21)))
        cost,order,exact=network.optimize(ids)
        self.assertFalse(exact)
        self.assertCountEqual(order,ids)
        self.assertLessEqual(cost,network.route(ids)[0]+1e-7)

    def test_slow_edges_have_real_cost_and_closed_edges_force_detours(self):
        a,b='j225_355','j285_355';key=edge_key(a,b)
        normal=Network().shortest(a,b)[0]
        slow=Network(Event(slow={key:2.2})).shortest(a,b)[0]
        detour=Network(Event(blocked={key})).shortest(a,b)[0]
        self.assertAlmostEqual(slow,normal*2.2)
        self.assertGreater(detour,normal)

def smoke_test():
    import pygame
    from main import Game, MAP
    from visuals import campus
    qa=ROOT/'qa';qa.mkdir(exist_ok=True)
    game=Game(headless=True,seed=31)
    game.event_enabled=False;game.new_round()
    game.score_file=qa/'test-records.json';game.records={}
    assert game.audio.available, 'WAV assets must load through the dummy audio device'
    assert pygame.mixer.music.get_busy(), 'The background track should loop during gameplay'
    assert all(name in game.audio.sounds for name in ['tap','select','start','deliver','badge','event','success'])
    game.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m))
    assert pygame.mixer.music.get_volume()==0
    game.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m))
    assert pygame.mixer.music.get_volume()>0
    game.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_s))
    assert not game.audio.settings['effects']
    game.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_s))
    game.audio.volume('music',2);assert game.audio.settings['music_volume']==1
    game.audio.volume('music',-2);assert game.audio.settings['music_volume']==0
    game.audio.volume('music',.3)
    game.modal='audio';game.draw();pygame.image.save(game.canvas,str(qa/'audio-settings.png'))
    game.close_modal()
    game.draw();pygame.image.save(game.canvas,str(qa/'desktop.png'))
    pygame.image.save(campus(),str(ROOT/'assets'/'campus-map.png'))
    # Exercise the same mouse and key routes as a player.
    game.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_4))
    game.draw()
    for p in PLACES:
        game.click(game.map_point(p.position))
    assert len(game.selected)==29, f'Not all map points can be selected: {len(game.selected)}'
    game.draw();pygame.image.save(game.canvas,str(qa/'all-29-places.png'))
    game.clear();assert not game.selected
    game.new_round(8)
    for id in game.orders:
        game.toggle_place(id)
    game.draw();game.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
    assert game.state=='delivering'
    for _ in range(2000):
        game.update(.2)
        if game.state=='complete':break
    assert game.state=='complete' and game.delivered==set(game.orders)
    assert 0<game.score<=100 and game.exact
    game.draw();pygame.image.save(game.canvas,str(qa/'result.png'))
    game.close_modal();game.draw();pygame.image.save(game.canvas,str(qa/'route-comparison.png'))
    game.new_round(0);game.selected=[p.id for p in PLACES];game.start()
    assert not game.exact
    game.update(1000);assert game.state=='complete'
    game.draw();pygame.image.save(game.canvas,str(qa/'free-result.png'))
    game.new_round();game.egg='lake';game.egg_until=999999999
    game.update(.6);game.draw();game.click(game.egg_rect.center)
    assert game.encounters==1 and game.egg is None
    game.draw();game.click(game.map_point(NODES['lake']))
    assert game.encounters==1, 'A departure animation must not grant a second badge'
    game.update(1.1);assert game.egg_departure is None
    # Arrival celebration must be visible before the final score dialog.
    game.new_round(0);game.selected=['activity'];expected_cost=game.network.route(game.selected)[0]
    game.start();game.update(.3)
    assert game.rider==NODES[START], 'Pickup hop must finish before movement'
    for _ in range(200):
        game.update(.1)
        if game.pending_finish:break
    assert game.pending_finish and game.modal is None and game.state=='delivering'
    assert game.pose=='celebrate'
    game.update(2)
    assert game.state=='complete' and game.modal=='result'
    assert abs(game.cost-expected_cost)<1e-8, 'Animation timing must not change route cost'
    game.new_round()
    game.modal='help';game.draw();pygame.image.save(game.canvas,str(qa/'help.png'))
    game.modal=None;game.screen=pygame.display.set_mode((1000,650),flags=pygame.HIDDEN);game.draw()
    mode_button=next(rect for key,rect,callback in game.buttons if key=='mode6')
    logical=mode_button.center
    physical=tuple(round(logical[i]*game.screen_scale+game.screen_offset[i]) for i in (0,1))
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=physical));assert game.mode==6
    pygame.quit()
    print('PASS: full desktop flows, all 29 locations, fair scores, animated encounters, arrival reactions, background loop, sound effects, mute/volume controls, replay and window scaling.')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AlgorithmChecks))
    if not result.wasSuccessful():
        raise SystemExit(1)
    smoke_test()
