"""Locally composed background loop and lightweight game sound effects.

No network service or extra dependency is required. All WAVs live in assets/audio.
"""
from array import array
import json
import math
from pathlib import Path
import random
import sys
import time
import wave

from app_paths import APP_DIR, ASSET_DIR
ROOT=APP_DIR
AUDIO_DIR=ASSET_DIR/'audio'
RATE=22050

def frequency(midi):
    return 440*2**((midi-69)/12)

def add_note(left,right,beat,midi,length,volume=.2,kind='bell',pan=0):
    start=round(beat*RATE);count=round(length*RATE);hz=frequency(midi)
    for i in range(min(count,len(left)-start)):
        t=i/RATE;progress=t/max(.001,length)
        attack=min(1,t/.008);release=min(1,(length-t)/.045)
        if kind=='bell':
            envelope=attack*release*math.exp(-5*progress)
            value=math.sin(math.tau*hz*t)+.22*math.sin(math.tau*hz*2*t)*math.exp(-10*progress)
        elif kind=='bass':
            envelope=attack*release*math.exp(-2.5*progress)
            value=math.sin(math.tau*hz*t)+.17*math.sin(math.tau*hz*2*t)
        elif kind=='pad':
            envelope=min(1,t/.06)*release*.65
            value=math.sin(math.tau*hz*t)+.12*math.sin(math.tau*hz*3*t)
        else:
            envelope=attack*release*math.exp(-4*progress)
            value=.75*math.sin(math.tau*hz*t)+.15*math.sin(math.tau*hz*3*t)
        value*=envelope*volume
        left[start+i]+=value*(1-max(0,pan)*.5)
        right[start+i]+=value*(1+min(0,pan)*.5)

def write_wave(path,left,right):
    samples=array('h')
    for a,b in zip(left,right):
        samples.append(round(max(-1,min(1,a)) * 29000))
        samples.append(round(max(-1,min(1,b)) * 29000))
    if sys.byteorder!='little':
        samples.byteswap()
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(RATE);wav.writeframes(samples.tobytes())

def make_music():
    beat=60/112;duration=64*beat
    left=array('f',[0])*round(duration*RATE);right=array('f',[0])*len(left)
    # Four short pentatonic phrases over C / Am / F / G. The last phrase
    # leaves a breath before the loop restarts; note tails stay inside the loop.
    phrases=[
        [72,76,79,None,76,74,72,74,76,None,79,81,79,76,74,None],
        [76,79,81,None,79,76,74,72,74,None,76,79,76,74,72,None],
        [77,81,84,None,81,79,77,76,77,None,79,81,79,77,76,None],
        [74,79,83,None,81,79,76,74,76,74,72,None,74,79,71,None]
    ]
    chords=[(48,60,64,67),(45,57,60,64),(41,53,57,60),(43,55,59,62)]
    noise=random.Random(112)
    for bar in range(16):
        chord=chords[bar%4]
        for step in range(8):
            midi=phrases[(bar//4)%4][(bar%2)*8+step]
            if midi is not None:
                add_note(left,right,(bar*4+step*.5)*beat,midi,(.42 if step%2 else .64)*beat,.19,pan=.15 if step%2 else -.15)
        for tick in range(4):
            at=(bar*4+tick)*beat
            add_note(left,right,at,chord[0]+(12 if tick%2 else 0),.62*beat,.18,'bass')
            add_note(left,right,at+.25*beat,chord[1+tick%3],.24*beat,.075,'pluck',pan=-.35)
            # Soft kick and shaker rather than a loud continuous drum loop.
            offset=round(at*RATE)
            for i in range(min(round(.09*RATE),len(left)-offset)):
                t=i/RATE
                kick=.10*math.sin(math.tau*(72*t-140*t*t))*math.exp(-t*45) if tick%2==0 else 0
                shake=noise.uniform(-1,1)*.019*math.exp(-t*65)
                left[offset+i]+=kick+shake;right[offset+i]+=kick-shake
    # Avoid discontinuities at the seam without a long quiet section.
    fade=round(.025*RATE)
    for i in range(fade):
        left[i]*=i/fade;right[i]*=i/fade
        left[-1-i]*=i/fade;right[-1-i]*=i/fade
    write_wave(AUDIO_DIR/'campus-loop.wav',left,right)

def make_effect(name,notes,duration,volume=.32):
    left=array('f',[0])*round(duration*RATE);right=array('f',[0])*len(left)
    for when,midi,length in notes:
        add_note(left,right,when,midi,length,volume,'bell')
    write_wave(AUDIO_DIR/(name+'.wav'),left,right)

def ensure_assets():
    AUDIO_DIR.mkdir(parents=True,exist_ok=True)
    if not (AUDIO_DIR/'campus-loop.wav').exists():
        make_music()
    effects={
        'tap':([(.0,76,.08)],.11,.18),
        'select':([(0,72,.12),(.07,79,.16)],.26,.28),
        'start':([(0,67,.15),(.1,72,.15),(.2,79,.22)],.48,.3),
        'deliver':([(0,76,.18),(.11,79,.22),(.22,84,.24)],.52,.3),
        'badge':([(0,79,.13),(.075,84,.15),(.15,88,.25)],.45,.26),
        'event':([(0,67,.18),(.17,64,.24)],.46,.23),
        'success':([(0,72,.24),(.12,76,.24),(.24,79,.24),(.38,84,.48),(.38,76,.48)],.93,.25)
    }
    for name,(notes,duration,volume) in effects.items():
        if not (AUDIO_DIR/(name+'.wav')).exists():
            make_effect(name,notes,duration,volume)

class SoundManager:
    def __init__(self,headless=False):
        self.settings_path=ROOT/'data'/'audio-settings.json'
        self.settings={'music':True,'effects':True,'music_volume':.30,'effects_volume':.55}
        if not headless:
            try:
                saved=json.loads(self.settings_path.read_text(encoding='utf-8'))
                for key in self.settings:
                    value=saved.get(key)
                    if key in ('music','effects') and isinstance(value,bool):
                        self.settings[key]=value
                    elif key.endswith('_volume') and isinstance(value,(float,int)):
                        self.settings[key]=max(0,min(1,float(value)))
            except (OSError,ValueError,AttributeError):
                pass
        self.headless=headless;self.available=False;self.error='';self.sounds={};self.last_play={}
        import pygame
        self.pygame=pygame
        try:
            ensure_assets()
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=RATE,size=-16,channels=2,buffer=512)
            pygame.mixer.set_num_channels(12)
            for path in AUDIO_DIR.glob('*.wav'):
                if path.name!='campus-loop.wav':
                    self.sounds[path.stem]=pygame.mixer.Sound(str(path))
            pygame.mixer.music.load(str(AUDIO_DIR/'campus-loop.wav'))
            self.available=True;self.apply()
            pygame.mixer.music.play(loops=-1,fade_ms=800)
        except (pygame.error,OSError) as error:
            self.error=str(error)

    def apply(self):
        if self.available:
            self.pygame.mixer.music.set_volume(self.settings['music_volume'] if self.settings['music'] else 0)
            for sound in self.sounds.values():
                sound.set_volume(self.settings['effects_volume'] if self.settings['effects'] else 0)

    def save(self):
        if not self.headless:
            try:
                self.settings_path.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8')
            except OSError:
                pass

    def toggle(self,kind):
        self.settings[kind]=not self.settings[kind];self.apply();self.save()
        if kind=='effects' and not self.settings[kind] and self.available:
            self.pygame.mixer.stop()

    def volume(self,kind,change):
        key=kind+'_volume';self.settings[key]=round(max(0,min(1,self.settings[key]+change)),2)
        self.apply();self.save()

    def play(self,name):
        now=time.monotonic()
        if self.available and self.settings['effects'] and now-self.last_play.get(name,-1e9)>.06:
            self.last_play[name]=now
            sound=self.sounds.get(name)
            if sound:sound.play()

if __name__=='__main__':
    ensure_assets()
    print('Generated original background music and 7 sound effects in '+str(AUDIO_DIR))
